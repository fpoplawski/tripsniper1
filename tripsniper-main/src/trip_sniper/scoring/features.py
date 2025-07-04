# -*- coding: utf-8 -*-
"""Feature computation utilities for offer scoring."""

from __future__ import annotations

from datetime import datetime
from typing import Dict

from ..models import Offer

__all__ = [
    "discount_pct",
    "absolute_price_score",
    "hotel_quality",
    "flight_comfort",
    "urgency_score",
    "novelty_score",
    "category_match",
]


def _clamp(value: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    """Clamp ``value`` to the inclusive ``min_value`` and ``max_value`` range."""
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def discount_pct(offer: Offer) -> float:
    """Return the discount percentage for ``offer`` compared to ``avg_price``.

    If ``avg_price`` is not positive the discount is assumed to be ``0``.
    The result is clamped to the ``0``–``100`` range.
    """
    avg = offer.avg_price
    if avg <= 0:
        return 0.0

    discount = (avg - offer.price_per_person) / avg * 100.0
    return _clamp(discount)


def absolute_price_score(offer: Offer, price_limit: float) -> float:
    """Score ``offer`` price relative to ``price_limit``.

    ``price_limit`` represents the maximum price that still yields a score of
    ``0``. Prices at ``0`` yield ``100``. Values between scale linearly.
    """
    if price_limit <= 0:
        return 0.0

    score = (1.0 - offer.price_per_person / price_limit) * 100.0
    return _clamp(score)


def hotel_quality(offer: Offer) -> float:
    """Return a hotel quality score based on rating and stars."""
    rating_score = _clamp((offer.hotel_rating / 10.0) * 60.0)
    star_score = _clamp((offer.stars / 5.0) * 40.0)
    return _clamp(rating_score + star_score)


def flight_comfort(offer: Offer) -> float:
    """Score flight comfort using directness and duration."""
    duration_factor = max(0.0, 1.0 - offer.total_duration / 720.0)
    direct_bonus = 20.0 if offer.direct else 0.0
    score = duration_factor * 80.0 + direct_bonus
    return _clamp(score)


def urgency_score(offer: Offer) -> float:
    """Return urgency score based on days until departure."""
    days = (offer.date - datetime.utcnow()).days
    if days < 0:
        days = 0
    score = (1.0 - min(days, 30) / 30.0) * 100.0
    return _clamp(score)


def novelty_score(offer: Offer) -> float:
    """Score how recently the offer was published."""
    hours = (datetime.utcnow() - offer.visible_from).total_seconds() / 3600.0
    if hours < 0:
        hours = 0.0
    score = (1.0 - min(hours, 24) / 24.0) * 100.0
    return _clamp(score)


def category_match(offer: Offer, user_prefs: Dict[str, object]) -> float:
    """Compute a score describing how well ``offer`` matches ``user_prefs``."""
    score = 0.0

    locations = user_prefs.get("locations")
    if isinstance(locations, (list, tuple, set)) and offer.location in locations:
        score += 40.0

    try:
        max_price = float(user_prefs.get("max_price"))  # type: ignore[arg-type]
        if max_price > 0:
            score += _clamp((1.0 - offer.price_per_person / max_price) * 30.0)
    except Exception:
        pass

    try:
        min_stars = int(user_prefs.get("min_stars"))  # type: ignore[arg-type]
        if min_stars > 0:
            if offer.stars >= min_stars:
                star_score = 30.0
            else:
                star_score = (offer.stars / min_stars) * 30.0
            score += _clamp(star_score)
    except Exception:
        pass

    return _clamp(score)

