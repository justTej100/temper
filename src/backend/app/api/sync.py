"""Pull active high-temperature events from Polymarket and upsert them locally.

Polymarket (via `forecasting.data_sources.polymarket`) is the source of truth for
which events/markets/buckets exist. This module is intentionally the *only* place
`app.api` writes City/Market/TempBucket rows, so events.py, weather.py, and ml.py
all see a consistent, idempotent view.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.db.models import City, Market, TempBucket
from forecasting.data_sources.polymarket import fetch_weather_events

logger = logging.getLogger(__name__)

# GET /events re-syncs against Polymarket when the most recent sync is older
# than this. Keeps normal browsing fast without ever going more than a few
# minutes stale.
SYNC_STALE_AFTER = timedelta(minutes=5)


def _get_or_create_city(session: Session, station: dict) -> City:
    name = station.get("name") or "Unknown"
    country = station.get("country") or ""
    city = session.exec(select(City).where(City.name == name, City.country == country)).first()
    if city is None:
        city = City(
            name=name,
            country=country,
            latitude=float(station.get("lat") or 0.0),
            longitude=float(station.get("lon") or 0.0),
            icao=station.get("icao") or "",
            timezone=station.get("timezone") or "",
            resolution_source=station.get("resolution_source") or "",
            resolution_verified=bool(station.get("resolution_verified")),
        )
    else:
        # Refresh in place rather than discarding history tied to this city_id.
        if station.get("lat") is not None:
            city.latitude = float(station["lat"])
        if station.get("lon") is not None:
            city.longitude = float(station["lon"])
        city.icao = station.get("icao") or city.icao
        city.timezone = station.get("timezone") or city.timezone
        city.resolution_source = station.get("resolution_source") or city.resolution_source
        city.resolution_verified = bool(station.get("resolution_verified")) or city.resolution_verified
    session.add(city)
    session.flush()
    return city


def _upsert_buckets(session: Session, market: Market, buckets: list[dict]) -> None:
    existing = {
        bucket.label: bucket
        for bucket in session.exec(
            select(TempBucket).where(TempBucket.market_id == market.id)
        ).all()
    }
    seen_labels: set[str] = set()
    for bucket in buckets:
        label = bucket["label"]
        seen_labels.add(label)
        row = existing.get(label)
        if row is None:
            row = TempBucket(market_id=market.id, label=label)
        row.temp_c = bucket.get("temp_c")
        row.source_unit = bucket.get("source_unit", "C")
        row.bucket_width_c = bucket.get("bucket_width_c") or 1.0
        row.is_or_higher = bool(bucket.get("is_or_higher"))
        row.is_or_lower = bool(bucket.get("is_or_lower"))
        row.token_id = bucket.get("token_id", "")
        row.yes_price = float(bucket.get("yes_price") or 0.0)
        row.active = True
        row.updated_at = datetime.now(UTC)
        session.add(row)
    for label, row in existing.items():
        if label not in seen_labels and row.active:
            row.active = False
            session.add(row)


def sync_markets(session: Session) -> int:
    """Fetch active Polymarket high-temperature events and upsert them.

    Returns the number of markets seen in this sync. Markets previously marked
    active that Polymarket no longer reports are deactivated (not deleted).
    """
    events = fetch_weather_events()
    seen_event_ids: set[str] = set()
    for event in events:
        city = _get_or_create_city(session, event["station"])
        market = session.exec(
            select(Market).where(Market.polymarket_event_id == event["event_id"])
        ).first()
        if market is None:
            market = Market(
                city_id=city.id,
                polymarket_event_id=event["event_id"],
                polymarket_slug=event.get("slug") or "",
            )
        market.city_id = city.id
        market.polymarket_slug = event.get("slug") or market.polymarket_slug
        market.question = event.get("question", "")
        market.temp_type = event.get("temp_type", "high")
        market.target_date = event["target_date"]
        market.volume = float(event.get("volume") or 0.0)
        market.active = True
        market.supported = bool(event.get("supported", True))
        market.unsupported_reason = event.get("unsupported_reason", "")
        market.resolution_source = event.get("resolution_source", "")
        market.resolution_station = event.get("resolution_station", "")
        market.url = event.get("url", "")
        market.last_synced_at = datetime.now(UTC)
        session.add(market)
        session.flush()

        _upsert_buckets(session, market, event.get("buckets", []))
        seen_event_ids.add(market.polymarket_event_id)

    still_active = session.exec(select(Market).where(Market.active == True)).all()
    for market in still_active:
        if market.polymarket_event_id not in seen_event_ids:
            market.active = False
            session.add(market)

    session.commit()
    return len(seen_event_ids)


def sync_if_stale(session: Session) -> None:
    """Best-effort refresh used by read endpoints; never raises."""
    latest = session.exec(
        select(Market.last_synced_at)
        .where(Market.last_synced_at.is_not(None))
        .order_by(Market.last_synced_at.desc())
    ).first()
    if latest is not None and latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)
    if latest is None or latest < datetime.now(UTC) - SYNC_STALE_AFTER:
        try:
            sync_markets(session)
        except Exception:  # noqa: BLE001 - serving cached data beats a hard failure
            logger.exception("Polymarket sync failed; serving cached data instead")
