from datetime import date
import asyncio
import pytest
import httpx

from trip_sniper.fetchers.booking_rapidapi18 import BookingRapidAPI18Fetcher


def test_fetch_offers_mock_transport():
    fixture = {"result": [{"hotel_id": 123, "min_total_price": 200, "review_score": 8.8}]}

    async def run():
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=fixture))
        async with httpx.AsyncClient(transport=transport) as client:
            fetcher = BookingRapidAPI18Fetcher("test", "example.com", http=client)
            return await fetcher.fetch_offers(
                "dest123",
                date(2025, 7, 15),
                date(2025, 7, 22),
            )

    offers = asyncio.run(run())

    assert len(offers) == 1
    offer = offers[0]
    assert offer.price_per_person == 100.0
    assert pytest.approx(offer.hotel_rating / 10) == 0.88
