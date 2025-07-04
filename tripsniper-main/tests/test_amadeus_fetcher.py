import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from trip_sniper.fetchers.amadeus import AmadeusFlightFetcher
from trip_sniper.models import Offer


class DummyResponse:
    def __init__(self, data, headers=None):
        self.data = data
        self.headers = headers or {}


def make_fetcher(monkeypatch, data, headers=None):
    fetcher = AmadeusFlightFetcher(api_key="k", api_secret="s")

    class DummySearch:
        def __init__(self):
            self.params = None

        def get(self, **kwargs):
            self.params = kwargs
            return DummyResponse(data, headers)

    dummy = DummySearch()
    client = type("C", (), {"shopping": type("S", (), {"flight_offers_search": dummy})()})()
    fetcher._amadeus = client
    return fetcher, dummy


def test_fetch_offers_maps_response(monkeypatch):
    data = [
        {
            "id": "1",
            "price": {"grandTotal": "120.0"},
            "itineraries": [
                {
                    "segments": [
                        {
                            "departure": {"at": "2024-01-01T10:00:00"},
                            "arrival": {"at": "2024-01-01T12:00:00"},
                        }
                    ]
                }
            ],
        }
    ]
    fetcher, dummy = make_fetcher(monkeypatch, data, {"X-RateLimit-Remaining": "1"})
    offers = fetcher.fetch_offers("LON", "2024-01-01", origin="WAW")
    assert dummy.params["originLocationCode"] == "WAW"
    assert isinstance(offers[0], Offer)
    assert offers[0].id == "1"
    assert offers[0].price_per_person == 120.0
    assert offers[0].total_duration == 120
    assert offers[0].location == "LON"
    assert offers[0].date == datetime(2024, 1, 1)


def test_fetch_offers_uses_env_origin(monkeypatch):
    monkeypatch.setenv("ORIGIN_IATA", "XYZ")
    data = []
    fetcher, dummy = make_fetcher(monkeypatch, data, {"X-RateLimit-Remaining": "1"})
    fetcher.fetch_offers("LON", "2024-01-01")
    assert dummy.params["originLocationCode"] == "XYZ"


def test_fetch_offers_with_patched_client():
    dummy_offers = [
        {
            "id": "O1",
            "price": {"grandTotal": "100"},
            "itineraries": [
                {
                    "segments": [
                        {
                            "departure": {"at": "2025-07-01T10:00:00"},
                            "arrival": {"at": "2025-07-01T12:00:00"},
                        }
                    ]
                }
            ],
        },
        {
            "id": "O2",
            "price": {"grandTotal": "200"},
            "itineraries": [
                {
                    "segments": [
                        {
                            "departure": {"at": "2025-07-01T13:00:00"},
                            "arrival": {"at": "2025-07-01T14:00:00"},
                        },
                        {
                            "departure": {"at": "2025-07-01T15:00:00"},
                            "arrival": {"at": "2025-07-01T16:00:00"},
                        },
                    ]
                }
            ],
        },
    ]

    with patch("trip_sniper.fetchers.amadeus.amadeus_client.Client") as MockClient:
        client_instance = MagicMock()
        MockClient.return_value = client_instance
        client_instance.shopping.flight_offers_search.get.return_value.data = dummy_offers

        fetcher = AmadeusFlightFetcher(api_key="k", api_secret="s")
        offers = fetcher.fetch_offers("BCN", "2025-07-01")

        assert isinstance(offers[0], Offer)
        assert offers[0].id == "O1"
        assert offers[0].price_per_person == 100.0
        assert offers[0].direct is True
