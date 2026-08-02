"""Open-Meteo historical + forecast temperature data."""

from __future__ import annotations

import logging
from datetime import date, timedelta

import httpx
import pandas as pd

from app.config import get_settings

logger = logging.getLogger(__name__)


def fetch_daily_history(lat: float, lon: float, days: int | None = None) -> pd.DataFrame:
    settings = get_settings()
    days = days or settings.history_days
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": "UTC",
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(settings.open_meteo_url, params=params)
        resp.raise_for_status()
        data = resp.json()
    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    rows = []
    for i, d in enumerate(dates):
        rows.append({
            "observed_on": date.fromisoformat(d),
            "high_c": highs[i] if i < len(highs) else None,
            "low_c": lows[i] if i < len(lows) else None,
        })
    return pd.DataFrame(rows)


def fetch_forecast_high_low(lat: float, lon: float, days: int = 7) -> pd.DataFrame:
    settings = get_settings()
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min",
        "forecast_days": days,
        "timezone": "UTC",
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(settings.open_meteo_forecast_url, params=params)
        resp.raise_for_status()
        data = resp.json()
    daily = data.get("daily") or {}
    return pd.DataFrame({
        "date": daily.get("time") or [],
        "high_c": daily.get("temperature_2m_max") or [],
        "low_c": daily.get("temperature_2m_min") or [],
    })


def geocode_city(name: str) -> dict | None:
    """Fallback geocoding via Open-Meteo geocoding API."""
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": name, "count": 1},
        )
        if resp.status_code != 200:
            return None
        results = (resp.json() or {}).get("results") or []
        if not results:
            return None
        hit = results[0]
        return {
            "name": hit.get("name") or name,
            "lat": float(hit["latitude"]),
            "lon": float(hit["longitude"]),
            "country": hit.get("country_code") or "",
            "icao": "",
        }
