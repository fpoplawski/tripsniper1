"""Data models for trip_sniper."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base

__all__ = ["Base", "OfferRecord", "Offer"]

Base = declarative_base()


@dataclass
class Offer:
    """Representation of a travel offer."""

    id: str
    price_per_person: float
    avg_price: float
    hotel_rating: float
    stars: int
    distance_from_beach: float
    direct: bool
    total_duration: int  # minutes
    date: datetime
    location: str
    attraction_score: float
    visible_from: datetime

    def __post_init__(self) -> None:
        """Basic validation of numeric fields."""
        if self.price_per_person < 0:
            raise ValueError("price_per_person must be non-negative")
        if self.avg_price < 0:
            raise ValueError("avg_price must be non-negative")
        if self.hotel_rating < 0:
            raise ValueError("hotel_rating must be non-negative")
        if self.stars < 0:
            raise ValueError("stars must be non-negative")
        if self.distance_from_beach < 0:
            raise ValueError("distance_from_beach must be non-negative")
        if self.total_duration < 0:
            raise ValueError("total_duration must be non-negative")
        if self.attraction_score < 0:
            raise ValueError("attraction_score must be non-negative")


class OfferRecord(Base):
    """SQLAlchemy ORM model mirroring :class:`Offer`."""

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
    category = Column(String(20), nullable=False)
    steal_score = Column(Float, nullable=False)

