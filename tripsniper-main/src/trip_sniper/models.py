"""Data models for trip_sniper."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = ["Offer"]


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
