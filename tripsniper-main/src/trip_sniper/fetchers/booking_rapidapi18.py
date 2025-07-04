"""Fetcher using Booking-com18 endpoints from RapidAPI."""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import List, Optional

import httpx
import logging

from ..models import Offer

__all__ = ["BookingRapidAPI18Fetcher"]


class BookingRapidAPI18Fetcher:
    """Client for Booking-com18 hotel offers on RapidAPI."""

    def __init__(
        self,
        rapidapi_key: Optional[str] = None,
        host: Optional[str] = None,
        http: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.rapidapi_key = rapidapi_key or os.getenv("BOOKING_RAPIDAPI_KEY")
        self.host = host or os.getenv("BOOKING_RAPIDAPI_HOST")
        if not self.rapidapi_key:
            raise RuntimeError("BOOKING_RAPIDAPI_KEY not set")
        self._http = http

    # ------------------------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover - simple representation
        key_preview = self.rapidapi_key[:4] if self.rapidapi_key else ""
        return f"BookingRapidAPI18Fetcher(host={self.host!r}, key={key_preview}...)"

    # ------------------------------------------------------------------
    async def fetch_offers(
        self,
        dest_id: str,
        checkin: date,
        checkout: date,
        adults: int = 2,
        currency: Optional[str] = None,
        limit: int = 30,
    ) -> List[Offer]:
        endpoint = f"https://{self.host}/v3/hotels/search"
        params = {
            "checkin_date": checkin,
            "checkout_date": checkout,
            "adults_number": adults,
            "dest_id": dest_id,
            "dest_type": "city",
            "order_by": "price",
            "room_number": 1,
            "units": "metric",
            "locale": "en-gb",
            "filter_by_currency": currency
            or os.getenv("BOOKING_RAPIDAPI_CURRENCY", "EUR"),
            "page_number": 0,
            "include_adjacency": "true",
        }
        headers = {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": self.host,
        }

        client = self._http or httpx.AsyncClient()
        created = self._http is None
        try:
            resp = await client.get(endpoint, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logging.error(
                "Booking18 HTTP %s \u2013 %s",
                e.response.status_code,
                e.response.text,
            )
            return []
        finally:
            if created:
                await client.aclose()

        offers: List[Offer] = []
        for hotel in data.get("result", [])[:limit]:
            try:
                price_total = float(hotel.get("min_total_price", 0))
                rating = float(hotel.get("review_score", 0))
                stars = int(hotel.get("class", 0))
                offer = Offer(
                    id=f"BK18-{hotel.get('hotel_id')}",
                    price_per_person=price_total / max(adults, 1),
                    avg_price=price_total / max(adults, 1),
                    hotel_rating=rating,
                    stars=stars,
                    distance_from_beach=0.0,
                    direct=True,
                    total_duration=0,
                    date=datetime.combine(checkin, datetime.min.time()),
                    location=dest_id,
                    attraction_score=0.0,
                    visible_from=datetime.utcnow(),
                )
                offers.append(offer)
            except Exception:  # noqa: BLE001 - skip malformed entries
                continue
        return offers
