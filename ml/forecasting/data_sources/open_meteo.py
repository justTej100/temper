def fetch_daily_forecast(lat: float, lon: float, timezone: str, days: int = 16) -> pd.DataFrame:
    """Open-Meteo's own forward-looking daily forecast. Display only."""
    settings = get_settings()
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or not timezone:
        raise ValueError("Valid coordinates and an IANA timezone are required")
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "celsius",
        "timezone": timezone,
        "forecast_days": max(1, min(int(days), 16)),
    }
    data = _get_json(settings.open_meteo_forecast_url, params)
    units = data.get("daily_units") or {}
    if units.get("temperature_2m_max") not in {"°C", "C", "celsius"}:
        raise ValueError("Open-Meteo returned unexpected temperature units")
    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    if len(dates) != len(highs) or len(dates) != len(lows):
        raise ValueError("Open-Meteo returned misaligned daily forecast data")
    rows = [
        {
            "forecast_date": datetime.fromisoformat(d).date(),
            "high_c": float(highs[i]) if highs[i] is not None else None,
            "low_c": float(lows[i]) if lows[i] is not None else None,
        }
        for i, d in enumerate(dates)
    ]
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("Open-Meteo returned no forecast data")
    return frame