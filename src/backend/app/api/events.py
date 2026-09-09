"""Event discovery, backed entirely by Polymarket via `app.api.sync`."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.api.deps import get_market_or_404
from app.api.sync import sync_if_stale
from app.db import get_session
from app.db.models import City, Market, TempBucket

router = APIRouter(
    prefix="/events",
    tags=["Events"],
)


def _bucket_out(bucket: TempBucket) -> dict:
    return {
        "label": bucket.label,
        "temp_c": bucket.temp_c,
        "source_unit": bucket.source_unit,
        "bucket_width_c": bucket.bucket_width_c,
        "is_or_higher": bucket.is_or_higher,
        "is_or_lower": bucket.is_or_lower,
        "yes_price": bucket.yes_price,
        "active": bucket.active,
    }


def _event_out(market: Market, city: City | None, buckets: list[TempBucket]) -> dict:
    return {
        "event_slug": market.polymarket_slug,
        "polymarket_event_id": market.polymarket_event_id,
        "question": market.question,
        "temp_type": market.temp_type,
        "target_date": market.target_date,
        "volume": market.volume,
        "active": market.active,
        "supported": market.supported,
        "unsupported_reason": market.unsupported_reason,
        "resolution_source": market.resolution_source,
        "resolution_station": market.resolution_station,
        "url": market.url,
        "last_synced_at": market.last_synced_at,
        "city": (
            {
                "name": city.name,
                "country": city.country,
                "latitude": city.latitude,
                "longitude": city.longitude,
                "icao": city.icao,
                "timezone": city.timezone,
            }
            if city
            else None
        ),
        "buckets": [_bucket_out(bucket) for bucket in buckets],
    }


@router.get("")
async def get_events(
    session: Session = Depends(get_session),
    active: bool = Query(True, description="Only return currently active markets"),
    sort: Literal["date", "volume"] = Query("date"),
    limit: int = Query(100, ge=1, le=500),
):
    sync_if_stale(session)

    statement = select(Market)
    if active:
        statement = statement.where(Market.active == True)
    statement = statement.order_by(
        Market.volume.desc() if sort == "volume" else Market.target_date.asc()
    ).limit(limit)
    markets = session.exec(statement).all()

    cities = {city.id: city for city in session.exec(select(City)).all()}
    results = []
    for market in markets:
        buckets = session.exec(
            select(TempBucket)
            .where(TempBucket.market_id == market.id, TempBucket.active == True)
            .order_by(TempBucket.temp_c)
        ).all()
        results.append(_event_out(market, cities.get(market.city_id), buckets))
    return results


@router.get("/{event_slug}")
async def get_event(event_slug: str, session: Session = Depends(get_session)):
    market = get_market_or_404(event_slug, session)
    city = session.get(City, market.city_id)
    buckets = session.exec(
        select(TempBucket)
        .where(TempBucket.market_id == market.id, TempBucket.active == True)
        .order_by(TempBucket.temp_c)
    ).all()
    return _event_out(market, city, buckets)
