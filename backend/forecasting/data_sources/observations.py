"""Aviation Weather METAR + NWS helpers (best-effort, optional)."""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def fetch_latest_metar(icao: str) -> dict | None:
    if not icao:
        return None
    settings = get_settings()
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(
                settings.metar_api_url,
                params={"ids": icao, "format": "json", "hours": 24},
                headers={"User-Agent": "TempEdge/1.0"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            latest = data[0] if isinstance(data, list) else data
            temp_c = latest.get("temp")
            return {
                "icao": icao,
                "temp_c": float(temp_c) if temp_c is not None else None,
                "observed_at": latest.get("reportTime") or datetime.utcnow().isoformat(),
                "raw": latest.get("rawOb") or "",
            }
    except Exception as exc:
        logger.warning("METAR fetch failed for %s: %s", icao, exc)
        return None


def fetch_nws_latest_obs(lat: float, lon: float) -> dict | None:
    """NWS points → stations → latest observation (US only)."""
    headers = {"User-Agent": "TempEdge/1.0 (mlops-demo)", "Accept": "application/geo+json"}
    try:
        with httpx.Client(timeout=20.0, headers=headers) as client:
            points = client.get(f"https://api.weather.gov/points/{lat},{lon}")
            if points.status_code != 200:
                return None
            stations_url = points.json()["properties"]["observationStations"]
            stations = client.get(stations_url)
            if stations.status_code != 200:
                return None
            features = stations.json().get("features") or []
            if not features:
                return None
            station_id = features[0]["properties"]["stationIdentifier"]
            obs = client.get(f"https://api.weather.gov/stations/{station_id}/observations/latest")
            if obs.status_code != 200:
                return None
            props = obs.json().get("properties") or {}
            temp = (props.get("temperature") or {}).get("value")
            return {
                "station": station_id,
                "temp_c": float(temp) if temp is not None else None,
                "observed_at": props.get("timestamp"),
            }
    except Exception as exc:
        logger.warning("NWS fetch failed: %s", exc)
        return None
