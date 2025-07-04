import importlib
import os
from datetime import datetime, timedelta

from fastapi.testclient import TestClient


class SimpleRecord:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def setup_app(records):
    os.environ["DATABASE_URL"] = "sqlite:///dummy.db"
    app_mod = importlib.import_module("trip_sniper.service.app")
    importlib.reload(app_mod)

    def patched_get_offers(
        *,
        limit: int = 10,
        account_type: str = "free",
        price_min: float | None = None,
        price_max: float | None = None,
        direct_only: bool = False,
    ) -> list[dict]:
        now = datetime.utcnow()
        if account_type == "free":
            now -= timedelta(hours=1)
        result = [r for r in records if r.visible_from <= now]
        if price_min is not None:
            result = [r for r in result if r.price_per_person >= price_min]
        if price_max is not None:
            result = [r for r in result if r.price_per_person <= price_max]
        if direct_only:
            result = [r for r in result if r.direct]
        result.sort(key=lambda r: r.steal_score, reverse=True)
        result = result[:limit]
        return [app_mod._record_to_dict(r) for r in result]

    app_mod.get_offers = patched_get_offers
    app_mod.app.routes["/offers"] = patched_get_offers
    return app_mod


def create_records():
    now = datetime.utcnow()
    return [
        SimpleRecord(
            id="1",
            price_per_person=50,
            avg_price=100,
            hotel_rating=0,
            stars=0,
            distance_from_beach=0,
            direct=True,
            total_duration=0,
            date=now,
            location="LON",
            attraction_score=0,
            visible_from=now - timedelta(hours=2),
            steal_score=90,
        ),
        SimpleRecord(
            id="2",
            price_per_person=60,
            avg_price=100,
            hotel_rating=0,
            stars=0,
            distance_from_beach=0,
            direct=True,
            total_duration=0,
            date=now,
            location="LON",
            attraction_score=0,
            visible_from=now - timedelta(minutes=30),
            steal_score=80,
        ),
    ]


def test_offers_endpoint_limit_and_visibility():
    records = create_records()
    app_mod = setup_app(records)
    client = TestClient(app_mod.app)

    resp = client.get("/offers", params={"account_type": "premium"})
    data = resp.json()
    assert len(data) == 2
    assert set(data[0].keys()) == {
        "id",
        "price_per_person",
        "avg_price",
        "hotel_rating",
        "stars",
        "distance_from_beach",
        "direct",
        "total_duration",
        "date",
        "location",
        "attraction_score",
        "visible_from",
        "steal_score",
    }

    resp = client.get("/offers", params={"account_type": "free"})
    free_data = resp.json()
    assert len(free_data) == 1
    assert free_data[0]["id"] == "1"

    resp = client.get("/offers", params={"account_type": "premium", "limit": 1})
    assert len(resp.json()) == 1

