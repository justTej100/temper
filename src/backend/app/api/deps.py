from __future__ import annotations

from fastapi import Header, HTTPException
from sqlmodel import Session, select

from app.api.sync import sync_markets
from app.config import get_settings
from app.db.models import City, Market


def get_market_or_404(event_slug: str, session: Session) -> Market:
    """Look up a market by its Polymarket slug.

    If it isn't in the database yet, this triggers one fresh sync against
    Polymarket before giving up — new markets shouldn't 404 just because
    nobody has hit `GET /events` since they went live.
    """
    market = session.exec(select(Market).where(Market.polymarket_slug == event_slug)).first()
    if market is None:
        sync_markets(session)
        market = session.exec(select(Market).where(Market.polymarket_slug == event_slug)).first()
    if market is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return market


def get_city_or_404(market: Market, session: Session) -> City:
    city = session.get(City, market.city_id)
    if city is None:
        raise HTTPException(status_code=500, detail="Event is missing its city record")
    return city


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """Gate expensive writes in production, matching the documented contract:

    production writes need `X-Admin-Token` when one is configured; if
    production has no token configured at all, the write is disabled (503)
    rather than silently left open.
    """
    settings = get_settings()
    if settings.environment != "production":
        return
    if not settings.admin_token:
        raise HTTPException(
            status_code=503,
            detail="Writes are disabled in production until ADMIN_TOKEN is configured",
        )
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Admin-Token")
