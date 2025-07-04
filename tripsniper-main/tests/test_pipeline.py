from datetime import datetime, timedelta

import pytest

from trip_sniper.models import Offer
from trip_sniper.pipeline import _combine_offers, run_pipeline
from trip_sniper.fetchers.amadeus import AmadeusFlightFetcher
from trip_sniper import pipeline


def make_offer(**kwargs) -> Offer:
    base = dict(
        id="id",
        price_per_person=100.0,
        avg_price=150.0,
        hotel_rating=5.0,
        stars=4,
        distance_from_beach=0.2,
        direct=True,
        total_duration=120,
        date=datetime(2023, 1, 1),
        location="AAA",
        attraction_score=0.0,
        visible_from=datetime(2023, 1, 1),
    )
    base.update(kwargs)
    return Offer(**base)


def test_only_matching_destination_and_date_are_combined():
    now = datetime(2023, 1, 1)
    flight1 = make_offer(id="F1", location="PAR", date=now)
    flight2 = make_offer(id="F2", location="LON", date=now)

    hotel1 = make_offer(id="H1", location="PAR", date=now)
    hotel2 = make_offer(id="H2", location="PAR", date=now + timedelta(days=1))

    combined = _combine_offers([flight1, flight2], [hotel1, hotel2])

    assert len(combined) == 1
    offer = combined[0]
    assert offer.id == "F1-H1"
    assert offer.location == "PAR"
    assert offer.date == now


def test_visible_from_is_max_of_flight_and_hotel():
    now = datetime(2023, 1, 1)
    flight_visible = now + timedelta(hours=1)
    hotel_visible = now + timedelta(hours=2)
    flight = make_offer(id="F1", location="PAR", date=now, visible_from=flight_visible)
    hotel = make_offer(id="H1", location="PAR", date=now, visible_from=hotel_visible)

    combined = _combine_offers([flight], [hotel])

    assert len(combined) == 1
    assert combined[0].visible_from == hotel_visible


def test_run_pipeline_flights_only(monkeypatch, tmp_path):
    calls = {
        "booking_init": False,
        "booking_fetch": False,
    }

    def dummy_flights(self, dest, date, origin=None):
        return [
            make_offer(id="F1", location=dest, date=datetime.fromisoformat(date))
        ]

    class DummyBookingFetcher:
        def __init__(self, *a, **k):
            calls["booking_init"] = True

        def fetch_offers(self, *a, **k):  # pragma: no cover - should not be called
            calls["booking_fetch"] = True
            return []

    recorded: list[str] = []

    def dummy_upsert(session, offer, score):
        recorded.append(offer.id)

    monkeypatch.setattr(AmadeusFlightFetcher, "fetch_offers", dummy_flights)
    monkeypatch.setenv("AMADEUS_API_KEY", "k")
    monkeypatch.setenv("AMADEUS_API_SECRET", "s")
    monkeypatch.setattr(pipeline, "BookingFetcher", DummyBookingFetcher)
    monkeypatch.setattr(pipeline, "_upsert_offer", dummy_upsert)

    run_pipeline(["PAR"], ["PAR"], ["2024-01-01"], database_url="sqlite:///ignored.db", flights_only=True)

    assert recorded == ["F1"]
    assert not calls["booking_init"]
    assert not calls["booking_fetch"]
