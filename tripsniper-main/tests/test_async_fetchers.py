import asyncio
from datetime import datetime
import pytest

from trip_sniper.fetchers.booking import BookingFetcher
from trip_sniper.fetchers.skyscanner import SkyscannerFetcher
from trip_sniper.models import Offer


def test_booking_async_matches_sync(monkeypatch):
    fetcher = BookingFetcher(client_id="id", client_secret="secret")
    data = {"hotels": [{"id": 1, "price": 50, "rating": 8, "stars": 4, "location": "LON"}]}

    def sync_auth(*args, **kwargs):
        return "t"

    async def async_auth(*args, **kwargs):
        return "t"

    def sync_req(*args, **kwargs):
        return data

    async def async_req(*args, **kwargs):
        return data

    monkeypatch.setattr(fetcher, "_authenticate", sync_auth)
    monkeypatch.setattr(fetcher, "_authenticate_async", async_auth)
    monkeypatch.setattr(fetcher, "_request", sync_req)
    monkeypatch.setattr(fetcher, "_request_async", async_req)
    const_offer = Offer(
        id="1",
        price_per_person=50.0,
        avg_price=50.0,
        hotel_rating=8.0,
        stars=4,
        distance_from_beach=0.0,
        direct=False,
        total_duration=0,
        date=datetime(2020, 1, 1),
        location="LON",
        attraction_score=0.0,
        visible_from=datetime(2020, 1, 1),
    )

    def map_offers(*args, **kwargs):
        return [const_offer]

    monkeypatch.setattr(fetcher, "_map_offers", map_offers)

    sync_offers = fetcher.fetch_offers("LON", "2020-01-01", "2020-01-02")
    async_offers = asyncio.run(fetcher.async_fetch_offers("LON", "2020-01-01", "2020-01-02"))

    assert sync_offers == async_offers
    assert isinstance(async_offers[0], Offer)


def test_skyscanner_async_matches_sync(monkeypatch):
    fetcher = SkyscannerFetcher(api_key="x")
    data = {
        "itineraries": [
            {
                "id": 1,
                "price": 20,
                "isDirect": True,
                "duration": 120,
                "date": "2020-01-01T00:00:00",
                "destination": "LON",
            }
        ]
    }

    def sync_req(*args, **kwargs):
        return data

    async def async_req(*args, **kwargs):
        return data

    monkeypatch.setattr(fetcher, "_request", sync_req)
    monkeypatch.setattr(fetcher, "_request_async", async_req)
    monkeypatch.setattr(fetcher, "_rate_limit", lambda *a, **k: None)
    async def rla(*args, **kwargs):
        return None
    monkeypatch.setattr(fetcher, "_rate_limit_async", rla)
    const_offer = Offer(
        id="1",
        price_per_person=20.0,
        avg_price=20.0,
        hotel_rating=0.0,
        stars=0,
        distance_from_beach=0.0,
        direct=True,
        total_duration=120,
        date=datetime(2020, 1, 1, 0, 0),
        location="LON",
        attraction_score=0.0,
        visible_from=datetime(2020, 1, 1),
    )

    def map_offers(*args, **kwargs):
        return [const_offer]

    monkeypatch.setattr(fetcher, "_map_offers", map_offers)

    sync_offers = fetcher.fetch_offers("LON", "2020-01-01")
    async_offers = asyncio.run(fetcher.async_fetch_offers("LON", "2020-01-01"))

    assert sync_offers == async_offers
    assert isinstance(async_offers[0], Offer)


