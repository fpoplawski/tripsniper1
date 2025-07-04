import pytest
from datetime import datetime, timedelta

from trip_sniper.models import Offer
from trip_sniper.scoring import features
from trip_sniper.scoring.steal_score import steal_score, weights


FIXED_NOW = datetime(2020, 1, 1, 12, 0, 0)


def make_offer(**kwargs):
    base = dict(
        id="x",
        price_per_person=80.0,
        avg_price=100.0,
        hotel_rating=8.0,
        stars=4,
        distance_from_beach=0.2,
        direct=True,
        total_duration=360,
        date=FIXED_NOW + timedelta(days=10),
        location="LON",
        attraction_score=5.0,
        visible_from=FIXED_NOW - timedelta(hours=3),
    )
    base.update(kwargs)
    return Offer(**base)


def test_discount_pct():
    offer = make_offer()
    assert features.discount_pct(offer) == 20.0


def test_absolute_price_score():
    offer = make_offer()
    expected = (1 - 80.0 / 120.0) * 100.0
    assert features.absolute_price_score(offer, 120.0) == pytest.approx(expected)


def test_hotel_quality():
    offer = make_offer()
    expected = (8.0 / 10.0) * 60.0 + (4 / 5) * 40.0
    assert features.hotel_quality(offer) == pytest.approx(expected)


def test_flight_comfort():
    offer = make_offer()
    expected = (1.0 - 360 / 720.0) * 80.0 + 20.0
    assert features.flight_comfort(offer) == pytest.approx(expected)


def test_urgency_score(monkeypatch):
    offer = make_offer()
    monkeypatch.setattr(features, "datetime", type("dt", (), {"utcnow": lambda: FIXED_NOW}))
    expected = (1 - 10 / 30.0) * 100.0
    assert features.urgency_score(offer) == pytest.approx(expected)


def test_novelty_score(monkeypatch):
    offer = make_offer()
    monkeypatch.setattr(features, "datetime", type("dt", (), {"utcnow": lambda: FIXED_NOW}))
    expected = (1 - 3 / 24.0) * 100.0
    assert features.novelty_score(offer) == pytest.approx(expected)


def test_category_match():
    offer = make_offer()
    prefs = {"locations": ["LON"], "max_price": 150, "min_stars": 3}
    expected = 40.0 + (1 - 80 / 150) * 30.0 + 30.0
    assert features.category_match(offer, prefs) == pytest.approx(expected)


def test_steal_score_known_input(monkeypatch):
    offer = make_offer()
    prefs = {"locations": ["LON"], "max_price": 150, "min_stars": 3}
    monkeypatch.setattr(features, "datetime", type("dt", (), {"utcnow": lambda: FIXED_NOW}))
    score = steal_score(offer, prefs)
    w = weights
    expected = (
        20.0 * w["discount_pct"]
        + ((1 - 80 / 150) * 100) * w["absolute_price_score"]
        + ((8 / 10) * 60 + (4 / 5) * 40) * w["hotel_quality"]
        + ((1 - 360 / 720) * 80 + 20) * w["flight_comfort"]
        + ((1 - 10 / 30) * 100) * w["urgency_score"]
        + ((1 - 3 / 24) * 100) * w["novelty_score"]
        + (40 + (1 - 80 / 150) * 30 + 30) * w["category_match"]
    )
    assert score == pytest.approx(expected)

