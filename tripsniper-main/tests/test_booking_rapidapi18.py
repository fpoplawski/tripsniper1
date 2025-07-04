from datetime import date
import asyncio
import pytest

from trip_sniper.fetchers.booking_rapidapi18 import BookingRapidAPI18Fetcher
from trip_sniper.models import Offer


class DummyResponse:
    def __init__(self, data):
        self._data = data
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class DummyClient:
    def __init__(self, data):
        self.data = data
        self.request_args = None

    async def get(self, url, params=None, headers=None, timeout=None):
        self.request_args = {
            "url": url,
            "params": params,
            "headers": headers,
            "timeout": timeout,
        }
        return DummyResponse(self.data)

    async def aclose(self):
        pass


def test_init_env(monkeypatch):
    monkeypatch.setenv("BOOKING_RAPIDAPI_KEY", "k1")
    monkeypatch.setenv("BOOKING_RAPIDAPI_HOST", "host")
    f = BookingRapidAPI18Fetcher()
    assert f.rapidapi_key == "k1"
    assert f.host == "host"


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("BOOKING_RAPIDAPI_KEY", raising=False)
    with pytest.raises(RuntimeError):
        BookingRapidAPI18Fetcher()


def test_fetch_offers(monkeypatch):
    resp = {
        "result": [
            {"hotel_id": "1", "min_total_price": 200, "review_score": 8.0, "class": 3}
        ]
    }
    client = DummyClient(resp)
    f = BookingRapidAPI18Fetcher("k", "example.com", http=client)

    offers = asyncio.run(f.fetch_offers("dest", date(2024, 1, 1), date(2024, 1, 2)))

    assert client.request_args["url"] == "https://example.com/v3/hotels/search"
    assert client.request_args["params"]["dest_id"] == "dest"
    assert isinstance(offers, list) and len(offers) == 1
    offer = offers[0]
    assert isinstance(offer, Offer)
    assert offer.id == "BK18-1"
    assert offer.price_per_person == 100.0
    assert offer.hotel_rating == 8.0
    assert offer.stars == 3
    assert offer.location == "dest"
