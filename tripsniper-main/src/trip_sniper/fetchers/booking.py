"""Booking.com hotel fetcher with Redis caching."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import httpx

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - Redis optional
    redis = None  # type: ignore

from ..models import Offer

__all__ = ["BookingFetcher"]

logger = logging.getLogger(__name__)


class BookingFetcher:
    """Client for fetching hotel offers from the Booking.com API."""

    AUTH_URL = "https://distribution-xml.booking.com/oauth2/token"
    BASE_URL = "https://distribution-xml.booking.com/2.0/json/hotels"
    CACHE_TTL = 3600

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        session: Optional[requests.Session] = None,
        redis_client: Optional["redis.Redis"] = None,
    ) -> None:
        self.client_id = client_id or os.getenv("BOOKING_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("BOOKING_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "BOOKING_CLIENT_ID and BOOKING_CLIENT_SECRET environment variables not set"
            )
        self.session = session or requests.Session()
        self.redis = redis_client
        if self.redis is None and redis is not None:
            try:
                self.redis = redis.Redis()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to connect to Redis: %s", exc)
                self.redis = None
        self._access_token: Optional[str] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _authenticate(self) -> str:
        """Retrieve an OAuth access token."""
        if self._access_token:
            return self._access_token
        try:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
            response = self.session.post(self.AUTH_URL, data=data, timeout=10)
            response.raise_for_status()
            payload = response.json()
            self._access_token = str(payload.get("access_token"))
            return self._access_token
        except Exception as exc:  # noqa: BLE001
            logger.error("Authentication failed: %s", exc)
            raise RuntimeError("Failed to authenticate with Booking API") from exc

    def _request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Perform a HTTP request and return JSON data."""
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("Booking request failed: %s", exc)
            raise RuntimeError("Failed to fetch data from Booking API") from exc

    async def _authenticate_async(self) -> str:
        """Async variant of :py:meth:`_authenticate`."""
        if self._access_token:
            return self._access_token
        try:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(self.AUTH_URL, data=data, timeout=10)
            response.raise_for_status()
            payload = response.json()
            self._access_token = str(payload.get("access_token"))
            return self._access_token
        except Exception as exc:  # noqa: BLE001
            logger.error("Authentication failed: %s", exc)
            raise RuntimeError("Failed to authenticate with Booking API") from exc

    async def _request_async(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Async HTTP request helper."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("Booking request failed: %s", exc)
            raise RuntimeError("Failed to fetch data from Booking API") from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch_offers(self, destination: str, checkin: str, checkout: str) -> List[Offer]:
        """Fetch hotel offers for a destination and date range."""
        cache_key = f"booking:{destination}:{checkin}:{checkout}"
        if self.redis is not None:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    data = json.loads(cached.decode("utf-8"))
                    return self._map_offers(data, destination, checkin)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to read from cache: %s", exc)

        token = self._authenticate()
        headers = {"Authorization": f"Bearer {token}"}
        params = {"destination": destination, "checkin": checkin, "checkout": checkout}
        data = self._request("GET", self.BASE_URL, headers=headers, params=params)

        if self.redis is not None:
            try:
                self.redis.setex(cache_key, self.CACHE_TTL, json.dumps(data))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to write to cache: %s", exc)

        hotels = data.get("hotels", [])
        offers: List[Offer] = []
        for item in hotels:
            try:
                mapped = self._map_offers({"hotels": [item]}, destination, checkin)
                offers.extend(mapped)
            except ValueError as exc:
                logger.error("Invalid date for hotel %s: %s", item.get("id"), exc)
        return offers

    async def async_fetch_offers(self, destination: str, checkin: str, checkout: str) -> List[Offer]:
        """Asynchronously fetch hotel offers."""
        cache_key = f"booking:{destination}:{checkin}:{checkout}"
        if self.redis is not None:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    data = json.loads(cached.decode("utf-8"))
                    return self._map_offers(data, destination, checkin)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to read from cache: %s", exc)

        token = await self._authenticate_async()
        headers = {"Authorization": f"Bearer {token}"}
        params = {"destination": destination, "checkin": checkin, "checkout": checkout}
        data = await self._request_async("GET", self.BASE_URL, headers=headers, params=params)

        if self.redis is not None:
            try:
                self.redis.setex(cache_key, self.CACHE_TTL, json.dumps(data))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to write to cache: %s", exc)

        return self._map_offers(data, destination, checkin)

    # ------------------------------------------------------------------
    def _map_offers(self, data: Dict[str, Any], destination: str, checkin: str) -> List[Offer]:
        """Map API response JSON into Offer objects."""
        hotels = data.get("hotels", [])
        result: List[Offer] = []
        for item in hotels:
            try:
                offer = Offer(
                    id=str(item.get("id")),
                    price_per_person=float(item.get("price", 0)),
                    avg_price=float(item.get("price", 0)),
                    hotel_rating=float(item.get("rating", 0)),
                    stars=int(item.get("stars", 0)),
                    distance_from_beach=0.0,
                    direct=False,
                    total_duration=0,
                    date=self._parse_date(checkin),
                    location=str(item.get("location", destination)),
                    attraction_score=0.0,
                    visible_from=datetime.utcnow(),
                )
                result.append(offer)
            except ValueError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to map offer: %s", exc)
        return result

    @staticmethod
    def _parse_date(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"invalid date value: {value}") from exc

