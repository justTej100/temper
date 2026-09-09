"""Event weather context, backed entirely by Open-Meteo's own forecast.

This is explicitly separate from the historical archive data used to train
models (`forecasting.data_sources.open_meteo.fetch_daily_history`): what's
shown here is Open-Meteo's own forward-looking forecast, for human context
only. It is never fed into the trainer.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_city_or_404, get_market_or_404
from app.db import get_session
from app.db.models import WeatherForecast
from forecasting.data_sources.open_meteo import fetch_daily_forecast

router = APIRouter(
    prefix="/events",
    tags=["Events - Weather"],
)


@router.get("/{event_slug}/weather")
async def get_event_weather(event_slug: str, session: Session = Depends(get_session)):
    market = get_market_or_404(event_slug, session)
    city = get_city_or_404(market, session)

    if not city.timezone:
        raise HTTPException(
            status_code=422,
            detail="This event's city doesn't have a verified timezone for a weather lookup",
        )

    try:
        forecast_frame = fetch_daily_forecast(city.latitude, city.longitude, city.timezone)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=f"Open-Meteo lookup failed: {exc}") from exc

    existing = {
        row.forecast_date: row
        for row in session.exec(
            select(WeatherForecast).where(WeatherForecast.city_id == city.id)
        ).all()
    }
    daily_out = []
    for row in forecast_frame.itertuples(index=False):
        record = existing.get(row.forecast_date)
        if record is None:
            record = WeatherForecast(city_id=city.id, forecast_date=row.forecast_date)
        record.high_c = row.high_c
        record.low_c = row.low_c
        session.add(record)
        daily_out.append(
            {
                "date": row.forecast_date,
                "high_c": row.high_c,
                "low_c": row.low_c,
                "is_target_date": row.forecast_date == market.target_date,
            }
        )
    session.commit()

    return {
        "event_slug": market.polymarket_slug,
        "city": {"name": city.name, "country": city.country, "timezone": city.timezone},
        "target_date": market.target_date,
        "target_date_forecast": next((d for d in daily_out if d["is_target_date"]), None),
        "daily": daily_out,
        "source": "open-meteo",
        "note": (
            "Open-Meteo's own forecast, shown for context only. "
            "The model is trained on historical observations, never on this forecast."
        ),
    }
