import os
from trip_sniper.fetchers.amadeus import AmadeusFlightFetcher


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} environment variable not set")
    return value


def main() -> None:
    api_key = _require_env("AMADEUS_API_KEY")
    api_secret = _require_env("AMADEUS_API_SECRET")
    host = os.getenv("AMADEUS_HOST")
    origin = os.getenv("ORIGIN_IATA")

    fetcher = AmadeusFlightFetcher(api_key=api_key, api_secret=api_secret, host=host)
    offers = fetcher.fetch_offers("BCN", "2025-07-01", origin=origin)
    offers.sort(key=lambda o: o.price_per_person)

    for offer in offers[:3]:
        print(f"{offer.id}: {offer.price_per_person}")


if __name__ == "__main__":
    main()
