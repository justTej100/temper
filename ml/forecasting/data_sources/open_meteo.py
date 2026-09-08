"""Open-Meteo local-day historical high-temperature observations."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pandas as pd

from app.config import get_settings

logger = logging.getLogger(__name__)


def _get_json(url: str, params: dict) -> dict:
    settings = get_settings()
    last_error: Exception | None = None
    with httpx.Client(timeout=settings.http_timeout_seconds) as client:
        for attempt in range(settings.http_max_retries):
            try:
                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise TypeError("Expected a JSON object")
                return payload
            except (httpx.HTTPError, TypeError, ValueError) as exc:
                last_error = exc
                if attempt + 1 < settings.http_max_retries:
                    time.sleep(min(2 ** attempt, 4))
    raise RuntimeError(f"Open-Meteo request failed after bounded retries: {last_error}")


def fetch_daily_history(
    lat: float, lon: float, timezone: str, days: int | None = None
) -> pd.DataFrame:
    settings = get_settings()
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or not timezone:
        raise ValueError("Valid coordinates and an IANA timezone are required")
    days = days or settings.history_days
    end = datetime.now(ZoneInfo(timezone)).date() - timedelta(days=1)
    start = end - timedelta(days=days)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "celsius",
        "timezone": timezone,
    }
    data = _get_json(settings.open_meteo_url, params)
    units = data.get("daily_units") or {}
    if units.get("temperature_2m_max") not in {"°C", "C", "celsius"}:
        raise ValueError("Open-Meteo returned unexpected temperature units")
    returned_timezone = str(data.get("timezone") or "")
    if returned_timezone and returned_timezone != timezone:
        raise ValueError(
            f"Open-Meteo timezone mismatch: expected {timezone}, got {returned_timezone}"
        )
    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    highs = daily.get("temperature_2m_max") or []
    if len(dates) != len(highs):
        raise ValueError("Open-Meteo returned misaligned daily data")
    rows = []
    for i, d in enumerate(dates):
        value = highs[i]
        if value is None:
            continue
        value = float(value)
        if not -90.0 <= value <= 65.0:
            raise ValueError(f"Implausible daily high temperature: {value}")
        rows.append({
            "observed_on": datetime.fromisoformat(d).date(),
            "high_c": value,
        })
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("Open-Meteo returned no historical observations")
    expected = pd.date_range(frame.observed_on.min(), frame.observed_on.max(), freq="D")
    missing = len(expected) - len(frame)
    if missing > settings.max_missing_days:
        raise ValueError(f"Historical series has {missing} missing local dates")
    return frame


def geocode_city(name: str) -> dict | None:
    """Return a validated but explicitly unaligned geocoding fallback."""
    settings = get_settings()
    payload = _get_json(
        settings.geocoding_api_url,
        {"name": name, "count": 5, "language": "en", "format": "json"},
    )
    results = payload.get("results") or []
    normalized = name.casefold().strip()
    exact = [
        hit for hit in results if str(hit.get("name") or "").casefold() == normalized
    ]
    if len(exact) != 1:
        return None
    hit = exact[0]
    timezone = str(hit.get("timezone") or "")
    lat = float(hit["latitude"])
    lon = float(hit["longitude"])
    if not timezone or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return {
        "name": hit.get("name") or name,
        "lat": lat,
        "lon": lon,
        "timezone": timezone,
        "country": hit.get("country_code") or "",
        "icao": "",
        "resolution_source": "open-meteo-geocoding",
        "resolution_verified": False,
    }
