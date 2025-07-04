import pytest
from datetime import datetime
from trip_sniper.models import Offer


def make_offer(**kwargs):
    base = dict(
        id="id",
        price_per_person=100.0,
        avg_price=120.0,
        hotel_rating=8.0,
        stars=4,
        distance_from_beach=0.5,
        direct=True,
        total_duration=180,
        date=datetime.utcnow(),
        location="LON",
        attraction_score=5.0,
        visible_from=datetime.utcnow(),
    )
    base.update(kwargs)
    return Offer(**base)


def test_offer_validation_raises_for_negative_fields():
    numeric_fields = [
        "price_per_person",
        "avg_price",
        "hotel_rating",
        "stars",
        "distance_from_beach",
        "total_duration",
        "attraction_score",
    ]
    for field in numeric_fields:
        kwargs = {field: -1}
        with pytest.raises(ValueError):
            make_offer(**kwargs)


def test_offer_validation_accepts_non_negative():
    offer = make_offer()
    assert isinstance(offer, Offer)
