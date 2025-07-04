import logging
from datetime import datetime

import pytest

from trip_sniper.fetchers.booking import BookingFetcher
from trip_sniper.models import Offer


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    monkeypatch.setenv("BOOKING_CLIENT_ID", "id")
    monkeypatch.setenv("BOOKING_CLIENT_SECRET", "secret")


def test_parse_date_valid():
    dt = BookingFetcher._parse_date("2024-01-02T03:04:05")
    assert isinstance(dt, datetime)
    assert dt == datetime(2024, 1, 2, 3, 4, 5)


def test_parse_date_invalid():
    with pytest.raises(ValueError):
        BookingFetcher._parse_date("not-a-date")


def test_fetch_offers_invalid_date_skips(monkeypatch, caplog):
    fetcher = BookingFetcher()
    monkeypatch.setattr(fetcher, "_authenticate", lambda: "token")
    monkeypatch.setattr(fetcher, "_request", lambda *a, **k: {"hotels": [{"id": "h1", "price": 10, "rating": 7, "stars": 3}]})
    caplog.set_level(logging.ERROR)
    offers = fetcher.fetch_offers("PAR", "bad-date", "bad-date")
    assert offers == []
    assert any("Invalid date" in record.message for record in caplog.records)

