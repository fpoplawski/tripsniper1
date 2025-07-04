import pytest
from trip_sniper.fetchers.skyscanner import SkyscannerFetcher


@pytest.fixture
def dummy_responses():
    return [
        {
            "itineraries": [
                {
                    "id": "1",
                    "price": 100,
                    "isDirect": True,
                    "duration": 60,
                    "date": "2023-01-01",
                    "destination": "LON",
                }
            ],
            "nextPageToken": "t1",
        },
        {
            "itineraries": [
                {
                    "id": "2",
                    "price": 200,
                    "isDirect": True,
                    "duration": 60,
                    "date": "2023-01-02",
                    "destination": "LON",
                }
            ],
            "nextPageToken": "t2",
        },
        {
            "itineraries": [
                {
                    "id": "3",
                    "price": 300,
                    "isDirect": True,
                    "duration": 60,
                    "date": "2023-01-03",
                    "destination": "LON",
                }
            ]
        },
    ]


def make_fetcher(monkeypatch, responses):
    f = SkyscannerFetcher(api_key="x")
    idx = 0

    def fake_request(method, url, **kwargs):
        nonlocal idx
        data = responses[idx]
        idx += 1
        return data

    monkeypatch.setattr(f, "_request", fake_request)
    return f, lambda: idx


def test_fetch_offers_respects_max_pages(monkeypatch, dummy_responses):
    fetcher, calls = make_fetcher(monkeypatch, dummy_responses)
    offers = fetcher.fetch_offers("LON", "2023-01-01", max_pages=2)

    assert len(offers) == 2
    assert [o.id for o in offers] == ["1", "2"]
    assert calls() == 2


def test_fetch_offers_no_limit(monkeypatch, dummy_responses):
    fetcher, calls = make_fetcher(monkeypatch, dummy_responses)
    offers = fetcher.fetch_offers("LON", "2023-01-01")

    assert len(offers) == 3
    assert [o.id for o in offers] == ["1", "2", "3"]
    assert calls() == 3
