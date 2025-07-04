"""Amadeus flight offer fetcher."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any, List, Optional

try:  # pragma: no cover - optional dependency for tests
    import amadeus as amadeus_client
    from amadeus import ResponseError
except Exception:  # pragma: no cover - allow tests without package
    class _DummyClient:
        def __init__(self, *args, **kwargs):  # pragma: no cover - simple stub
            pass

    class _DummyModule:
        Client = _DummyClient

    amadeus_client = _DummyModule()  # type: ignore

    class ResponseError(Exception):
        pass

from ..models import Offer

__all__ = ["AmadeusFlightFetcher"]

logger = logging.getLogger(__name__)


class AmadeusFlightFetcher:
    """Client for fetching flight offers from the Amadeus API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        host: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("AMADEUS_API_KEY")
        self.api_secret = api_secret or os.getenv("AMADEUS_API_SECRET")
        self.host = host or os.getenv("AMADEUS_HOST")
        if not self.api_key or not self.api_secret:
            raise RuntimeError("AMADEUS_API_KEY and AMADEUS_API_SECRET must be set")
        self._amadeus: Optional[amadeus_client.Client] = None

    # ------------------------------------------------------------------
    @property
    def amadeus(self) -> amadeus_client.Client:
        if self._amadeus is None:
            if amadeus_client is None:
                raise RuntimeError("amadeus package not installed")
            self._amadeus = amadeus_client.Client(
                client_id=self.api_key,
                client_secret=self.api_secret,
                host=self.host,
            )
        return self._amadeus

    # ------------------------------------------------------------------
    def fetch_offers(self, dest: str, date: str, origin: Optional[str] = None) -> List[Offer]:
        origin_code = origin or os.getenv("ORIGIN_IATA", "WAW")
        params = {
            "originLocationCode": origin_code,
            "destinationLocationCode": dest,
            "departureDate": date,
            "adults": 1,
            "currencyCode": "PLN",
            "max": 20,
        }

        backoff = 1.0
        for attempt in range(3):
            try:
                response = self.amadeus.shopping.flight_offers_search.get(**params)
                headers = getattr(response, "headers", {})
                remaining = int(headers.get("X-RateLimit-Remaining", "1"))
                if remaining == 0:
                    reset = headers.get("X-RateLimit-Reset")
                    try:
                        wait = max(int(reset) - int(time.time()), 1) if reset else 1
                        time.sleep(wait)
                    except Exception:  # pragma: no cover - just sleep best effort
                        time.sleep(1)
                data = getattr(response, "data", [])
                return self._map_offers(data, dest, date)
            except ResponseError as exc:
                logger.error(
                    "Amadeus HTTP %s \u2013 %s",
                    getattr(exc.response, "status_code", ""),
                    getattr(exc.response, "body", ""),
                )
                if attempt == 2:
                    raise RuntimeError("Failed to fetch data from Amadeus API") from exc
                time.sleep(backoff)
                backoff *= 2
            except Exception as exc:  # noqa: BLE001
                logger.warning("Amadeus request failed (attempt %s): %s", attempt + 1, exc)
                if attempt == 2:
                    raise RuntimeError("Failed to fetch data from Amadeus API") from exc
                time.sleep(backoff)
                backoff *= 2
        return []

    # ------------------------------------------------------------------
    def _map_offers(self, data: List[Any], dest: str, date: str) -> List[Offer]:
        result: List[Offer] = []
        for item in data:
            try:
                itinerary = item["itineraries"][0]
                segments = itinerary["segments"]
                dep = self._parse_date(segments[0]["departure"]["at"])
                arr = self._parse_date(segments[-1]["arrival"]["at"])
                duration = int((arr - dep).total_seconds() / 60)
                price_pp = float(item["price"]["grandTotal"])
                offer = Offer(
                    id=str(item["id"]),
                    price_per_person=price_pp,
                    avg_price=price_pp,
                    hotel_rating=0.0,
                    stars=0,
                    distance_from_beach=0.0,
                    direct=len(segments) == 1,
                    total_duration=duration,
                    date=self._parse_date(date),
                    location=dest,
                    attraction_score=0.0,
                    visible_from=datetime.utcnow(),
                )
                result.append(offer)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to map offer: %s", exc)
        return result

    @staticmethod
    def _parse_date(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        try:
            if isinstance(value, str) and value.endswith("Z"):
                value = value[:-1] + "+00:00"
            return datetime.fromisoformat(str(value))
        except Exception:  # noqa: BLE001
            return datetime.utcnow()
