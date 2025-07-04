from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Generator, List, Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ..models import Base, OfferRecord

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

app = FastAPI(title="Trip Sniper Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("%s %s", request.method, request.url.path)
    response = await call_next(request)
    logger.info("completed %s", response.status_code)
    return response


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _record_to_dict(record: OfferRecord) -> dict:
    return {
        "id": record.id,
        "price_per_person": record.price_per_person,
        "avg_price": record.avg_price,
        "hotel_rating": record.hotel_rating,
        "stars": record.stars,
        "distance_from_beach": record.distance_from_beach,
        "direct": record.direct,
        "total_duration": record.total_duration,
        "date": record.date.isoformat(),
        "location": record.location,
        "attraction_score": record.attraction_score,
        "visible_from": record.visible_from.isoformat(),
        "steal_score": record.steal_score,
    }


@app.get("/offers")
def get_offers(
    *,
    limit: int = Query(10, ge=1, le=100),
    account_type: str = Query("free", pattern="^(free|premium)$"),
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    direct_only: bool = False,
    db: Session = Depends(get_db),
) -> List[dict]:
    now = datetime.utcnow()
    if account_type == "free":
        now -= timedelta(hours=1)

    stmt = select(OfferRecord).where(OfferRecord.visible_from <= now)
    if price_min is not None:
        stmt = stmt.where(OfferRecord.price_per_person >= price_min)
    if price_max is not None:
        stmt = stmt.where(OfferRecord.price_per_person <= price_max)
    if direct_only:
        stmt = stmt.where(OfferRecord.direct.is_(True))

    stmt = stmt.order_by(OfferRecord.steal_score.desc()).limit(limit)
    records = db.execute(stmt).scalars().all()
    return [_record_to_dict(rec) for rec in records]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
