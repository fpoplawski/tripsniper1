"""Data pipeline for Trip Sniper offers."""

from __future__ import annotations

import logging
import os
import sys
import asyncio
import itertools
from datetime import datetime
from typing import Iterable, List, Sequence

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session

from .fetchers.booking_rapidapi18 import (
    BookingRapidAPI18Fetcher as BookingFetcher,
)
from .fetchers import AmadeusFlightFetcher
from .models import Offer
from .scoring.steal_score import steal_score

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(levelname)s %(name)s:%(lineno)d  %(message)s",
    stream=sys.stdout,
)

__all__ = ["run_pipeline", "OfferRecord"]

logger = logging.getLogger(__name__)

Base = declarative_base()


class OfferRecord(Base):
    """SQLAlchemy ORM model for persisted offers."""

    __tablename__ = "offers"

    id = Column(String, primary_key=True)
    price_per_person = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    hotel_rating = Column(Float, nullable=False)
    stars = Column(Integer, nullable=False)
    distance_from_beach = Column(Float, nullable=False)
    direct = Column(Boolean, nullable=False)
    total_duration = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)
    location = Column(String, nullable=False)
    attraction_score = Column(Float, nullable=False)
    visible_from = Column(DateTime, nullable=False)
    steal_score = Column(Float, nullable=False)


def _combine_offers(flights: Iterable[Offer], hotels: Iterable[Offer]) -> List[Offer]:
    """Join Amadeus flight offers and hotel offers by destination and date."""
    result: List[Offer] = []
    for flight in flights:
        for hotel in hotels:
            if flight.location == hotel.location and flight.date.date() == hotel.date.date():
                visible_from = max(flight.visible_from, hotel.visible_from)
                offer = Offer(
                    id=f"{flight.id}-{hotel.id}",
                    price_per_person=flight.price_per_person + hotel.price_per_person,
                    avg_price=flight.avg_price + hotel.avg_price,
                    hotel_rating=hotel.hotel_rating,
                    stars=hotel.stars,
                    distance_from_beach=hotel.distance_from_beach,
                    direct=flight.direct,
                    total_duration=flight.total_duration,
                    date=flight.date,
                    location=flight.location,
                    attraction_score=max(flight.attraction_score, hotel.attraction_score),
                    visible_from=visible_from,
                )
                result.append(offer)
    return result


def _upsert_offer(session: Session, offer: Offer, score: float) -> None:
    """Insert or update an offer record."""
    existing = session.get(OfferRecord, offer.id)
    if existing is None:
        record = OfferRecord()
        record.id = offer.id
        record.price_per_person = offer.price_per_person
        record.avg_price = offer.avg_price
        record.hotel_rating = offer.hotel_rating
        record.stars = offer.stars
        record.distance_from_beach = offer.distance_from_beach
        record.direct = offer.direct
        record.total_duration = offer.total_duration
        record.date = offer.date
        record.location = offer.location
        record.attraction_score = offer.attraction_score
        record.visible_from = offer.visible_from
        record.steal_score = score
        session.add(record)
    else:
        existing.price_per_person = offer.price_per_person
        existing.avg_price = offer.avg_price
        existing.hotel_rating = offer.hotel_rating
        existing.stars = offer.stars
        existing.distance_from_beach = offer.distance_from_beach
        existing.direct = offer.direct
        existing.total_duration = offer.total_duration
        existing.date = offer.date
        existing.location = offer.location
        existing.attraction_score = offer.attraction_score
        existing.visible_from = offer.visible_from
        existing.steal_score = score


def run_pipeline(
    flight_destinations: Sequence[str],
    hotel_destinations: Sequence[str],
    dates: Sequence[str],
    database_url: str | None = None,
    origin: str | None = None,
    flights_only: bool = False,
) -> None:
    """Fetch offers, score them and persist to PostgreSQL.

    ``flight_destinations`` contains IATA airport codes used for flights while
    ``hotel_destinations`` holds Booking.com city identifiers. The lists are
    paired in order using ``itertools.zip_longest``. Incomplete pairs are
    skipped with a warning. When ``flights_only`` is ``True`` only Amadeus
    flight offers are fetched and persisted without combining them with hotel
    data.
    """
    async_mode = os.getenv("ASYNC_FETCH") == "1"
    if origin is None:
        env_origin = os.getenv("ORIGIN_IATA")
        if env_origin:
            origin = env_origin
    db_url = database_url or os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not provided")

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    flight_fetcher = AmadeusFlightFetcher()
    hotels_enabled = os.getenv("HOTELS_ENABLED", "1") != "0"
    hotel_fetcher = None if flights_only or not hotels_enabled else BookingFetcher()

    async def _gather_offers(airport: str, city_id: str, date_val: str):
        flights_task = asyncio.to_thread(
            flight_fetcher.fetch_offers, airport, date_val, origin
        )
        if hotel_fetcher is None:
            flights = await flights_task
            return flights, []
        hotels_task = hotel_fetcher.async_fetch_offers(city_id, date_val, date_val)
        flights, hotels = await asyncio.gather(flights_task, hotels_task)
        for h in hotels:
            h.location = airport
        return flights, hotels

    with Session(engine) as session:
        for airport, city_id in itertools.zip_longest(flight_destinations, hotel_destinations):
            if not airport or not city_id:
                logging.warning("dest pair incomplete: %s / %s", airport, city_id)
                continue
            for date in dates:
                if async_mode:
                    flights, hotels = asyncio.run(_gather_offers(airport, city_id, date))
                else:
                    flights = flight_fetcher.fetch_offers(airport, date, origin)
                    if hotel_fetcher is None:
                        hotels = []
                    else:
                        hotels = hotel_fetcher.fetch_offers(city_id, date, date)
                        for h in hotels:
                            h.location = airport
                offers = flights if hotel_fetcher is None else _combine_offers(flights, hotels)

                for offer in offers:
                    if offer.visible_from > datetime.utcnow():
                        continue
                    score = steal_score(offer)
                    _upsert_offer(session, offer, score)
        session.commit()



def run(origin: str | None = None) -> None:
    """Entry point used by the scheduler.

    Destinations and dates are read from the environment variables
    ``FLIGHT_DESTS``/``HOTEL_DESTS`` and ``DATES`` (comma separated). Command
    line ``--destinations`` and ``--dates`` still work and override the
    environment when provided.
    """
    flight_dests = os.getenv("FLIGHT_DESTS", "").split(",")
    hotel_dests = os.getenv("HOTEL_DESTS", "").split(",")
    dates = os.getenv("DATES", "").split(",")

    flight_dests = [d.strip() for d in flight_dests if d.strip()]
    hotel_dests = [d.strip() for d in hotel_dests if d.strip()]
    dates = [d.strip() for d in dates if d.strip()]

    if not flight_dests or not hotel_dests or not dates:
        raise RuntimeError("FLIGHT_DESTS, HOTEL_DESTS and DATES must be set")

    flights_only = os.getenv("FLIGHTS_ONLY") == "1"
    run_pipeline(flight_dests, hotel_dests, dates, origin=origin, flights_only=flights_only)

