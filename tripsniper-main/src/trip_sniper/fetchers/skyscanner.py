"""Skyscanner flight fetcher."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import httpx
import asyncio

from ..models import Offer

__all__ = ["SkyscannerFetcher"]

logger = logging.getLogger(__name__)


@dataclass
class _PaginationState:
    page: int = 0
    next_page_token: Optional[str] = None


class SkyscannerFetcher:
    """Client for fetching flights from the Skyscanner API."""

    BASE_URL = "https://partners.api.skyscanner.net/apiservices/v3/flights/extended-search"
    RATE_LIMIT_INTERVAL = 60 / 100  # 100 requests per minute

    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None) -> None:
        self.api_key = api_key or os.getenv("SKYSCANNER_API_KEY")
        if not self.api_key:
            raise RuntimeError("SKYSCANNER_API_KEY environment variable not set")
        self.session = session or requests.Session()
        self._last_request_ts = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _rate_limit(self) -> None:
        """Ensure we don't exceed the allowed request rate."""
        elapsed = time.monotonic() - self._last_request_ts
        wait = self.RATE_LIMIT_INTERVAL - elapsed
        if wait > 0:
            time.sleep(wait)

    async def _rate_limit_async(self) -> None:
        """Async variant of :py:meth:`_rate_limit`."""
        elapsed = time.monotonic() - self._last_request_ts
        wait = self.RATE_LIMIT_INTERVAL - elapsed
        if wait > 0:
            await asyncio.sleep(wait)

    def _request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Perform a HTTP request with retry and rate limiting."""
        headers = kwargs.pop("headers", {})
        headers["apikey"] = self.api_key
        kwargs["headers"] = headers

        backoff = 1.0
        for attempt in range(5):
            self._rate_limit()
            try:
                response = self.session.request(method, url, **kwargs)
                self._last_request_ts = time.monotonic()
                if response.status_code >= 500:
                    raise requests.HTTPError(f"server error {response.status_code}")
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skyscanner request failed (attempt %s): %s", attempt + 1, exc)
                time.sleep(backoff)
                backoff *= 2
        raise RuntimeError("Failed to fetch data from Skyscanner after retries")

    async def _request_async(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Async HTTP request with retry and rate limiting."""
        headers = kwargs.pop("headers", {})
        headers["apikey"] = self.api_key
        kwargs["headers"] = headers

        backoff = 1.0
        for attempt in range(5):
            await self._rate_limit_async()
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(method, url, **kwargs)
                self._last_request_ts = time.monotonic()
                if response.status_code >= 500:
                    raise requests.HTTPError(f"server error {response.status_code}")
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Skyscanner request failed (attempt %s): %s",
                    attempt + 1,
                    exc,
                )
                await asyncio.sleep(backoff)
                backoff *= 2
        raise RuntimeError("Failed to fetch data from Skyscanner after retries")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch_offers(
        self, destination: str, date: str, max_pages: Optional[int] = None
    ) -> List[Offer]:
        """Fetch offers for a destination on a given date.

        Parameters
        ----------
        destination:
            Airport or city code to search connections to.
        date:
            Date of departure.
        max_pages:
            Optional limit for how many pages should be fetched. When provided,
            pagination stops once the limit is reached regardless of whether a
            ``next_page_token`` is returned by the API.
        """
        state = _PaginationState()
        offers: List[Offer] = []
        pages_fetched = 0

        origin = os.getenv("ORIGIN_IATA", "WAW")
        while True:
            params = {
                "origin": origin,
                "destination": destination,
                "date": date,
                "page": state.page,
            }
            if state.next_page_token:
                params["next_page_token"] = state.next_page_token

            data = self._request("GET", self.BASE_URL, params=params)
            page_offers = self._map_offers(data, destination)
            offers.extend(page_offers)

            pages_fetched += 1
            if max_pages is not None and pages_fetched >= max_pages:
                break

            state.next_page_token = data.get("nextPageToken")
            if not state.next_page_token:
                break
            state.page += 1

        return offers

    async def async_fetch_offers(self, destination: str, date: str) -> List[Offer]:
        """Asynchronously fetch offers for a destination on a given date."""
        state = _PaginationState()
        offers: List[Offer] = []

        origin = os.getenv("ORIGIN_IATA", "WAW")
        while True:
            params = {
                "origin": origin,
                "destination": destination,
                "date": date,
                "page": state.page,
            }
            if state.next_page_token:
                params["next_page_token"] = state.next_page_token

            data = await self._request_async("GET", self.BASE_URL, params=params)
            page_offers = self._map_offers(data, destination)
            offers.extend(page_offers)

            state.next_page_token = data.get("nextPageToken")
            if not state.next_page_token:
                break
            state.page += 1

        return offers

    # ------------------------------------------------------------------
    def _map_offers(self, data: Dict[str, Any], destination: str) -> List[Offer]:
        """Map API response JSON into Offer objects."""
        itineraries = data.get("itineraries", [])
        result: List[Offer] = []
        for item in itineraries:
            try:
                offer = Offer(
                    id=str(item.get("id")),
                    price_per_person=float(item.get("price", 0)),
                    avg_price=float(item.get("price", 0)),
                    hotel_rating=0.0,
                    stars=0,
                    distance_from_beach=0.0,
                    direct=bool(item.get("isDirect", False)),
                    total_duration=int(item.get("duration", 0)),
                    date=self._parse_date(item.get("date")),
                    location=str(item.get("destination", destination)),
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
            return datetime.fromisoformat(str(value))
        except Exception:  # noqa: BLE001
            return datetime.utcnow()
