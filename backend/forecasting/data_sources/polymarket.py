"""Discover active Polymarket daily-high temperature markets."""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from typing import Any

import httpx

from app.config import get_settings
from forecasting.stations import resolve_city

logger = logging.getLogger(__name__)

TITLE_RE = re.compile(
    r"Highest\s+temperature\s+in\s+(?P<city>.+?)\s+on\s+"
    r"(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2})(?:,?\s+(?P<year>\d{4}))?",
    re.IGNORECASE,
)
BUCKET_RE = re.compile(
    r"(?P<temp>-?\d+(?:\.\d+)?)\s*°?\s*(?P<unit>[CF])"
    r"(?:\s+or\s+(?P<bound>higher|lower))?",
    re.IGNORECASE,
)
STATION_RE = re.compile(
    r"(?:station|airport)\s+(?:at\s+)?(?:\()?([A-Z]{4})(?:\))?", re.IGNORECASE
)
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_json_field(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def parse_title(question: str, *, today: date | None = None) -> dict | None:
    m = TITLE_RE.search(question or "")
    if not m:
        return None
    month = MONTHS.get(m.group("month").lower())
    if not month:
        return None
    today = today or datetime.now().date()
    explicit_year = m.group("year")
    year = int(explicit_year) if explicit_year else today.year
    day = int(m.group("day"))
    try:
        target = date(year, month, day)
    except ValueError:
        return None
    # Active markets omit the year. Select the next occurrence, which safely
    # handles December/January rollover without guessing from month numbers.
    if not explicit_year and target < today:
        target = date(year + 1, month, day)
    return {
        "temp_type": "high",
        "city_raw": m.group("city").strip(),
        "target_date": target,
    }


def parse_bucket_label(label: str) -> dict:
    m = BUCKET_RE.search(label or "")
    if not m:
        return {
            "temp_c": None,
            "source_unit": "",
            "bucket_width_c": 1.0,
            "is_or_higher": False,
            "is_or_lower": False,
        }
    bound = (m.group("bound") or "").lower()
    value = float(m.group("temp"))
    unit = m.group("unit").upper()
    temp_c = (value - 32.0) * 5.0 / 9.0 if unit == "F" else value
    return {
        "temp_c": temp_c,
        "source_unit": unit,
        "bucket_width_c": 5.0 / 9.0 if unit == "F" else 1.0,
        "is_or_higher": bound == "higher",
        "is_or_lower": bound == "lower",
    }


def _request_json(client: httpx.Client, url: str, *, params: dict) -> Any:
    settings = get_settings()
    last_error: Exception | None = None
    for attempt in range(settings.http_max_retries):
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt + 1 < settings.http_max_retries:
                import time

                time.sleep(min(2 ** attempt, 4))
    raise RuntimeError(f"Polymarket request failed after bounded retries: {last_error}")


def _resolution_metadata(event: dict, station: dict) -> tuple[str, str, bool]:
    text = " ".join(
        str(event.get(key) or "")
        for key in ("description", "resolutionSource", "resolution_source")
    )
    match = STATION_RE.search(text)
    explicit_station = match.group(1).upper() if match else ""
    expected = str(station.get("icao") or "").upper()
    if explicit_station:
        return text.strip(), explicit_station, explicit_station == expected
    verified = bool(station.get("resolution_verified"))
    return text.strip(), expected, verified


def fetch_weather_events(limit: int = 100, max_pages: int = 10) -> list[dict]:
    settings = get_settings()
    results: list[dict] = []
    offset = 0
    seen_ids: set[str] = set()
    with httpx.Client(timeout=settings.http_timeout_seconds) as client:
        for _ in range(max_pages):
            batch = _request_json(
                client,
                f"{settings.gamma_api_url}/events",
                params={
                    "active": "true",
                    "closed": "false",
                    "limit": limit,
                    "offset": offset,
                    "order": "volume24hr",
                    "ascending": "false",
                },
            )
            if not isinstance(batch, list) or not batch:
                break
            for event in sorted(batch, key=lambda item: str(item.get("id") or "")):
                if not event.get("active", True) or event.get("closed", False):
                    continue
                title = event.get("title") or event.get("question") or ""
                parsed = parse_title(title)
                if not parsed:
                    # Also check nested markets
                    markets = event.get("markets") or []
                    if markets:
                        parsed = parse_title(markets[0].get("question") or title)
                    if not parsed:
                        continue
                if parsed["temp_type"] != "high" or parsed["target_date"] < date.today():
                    continue
                station = resolve_city(parsed["city_raw"])
                if not station:
                    station = {
                        "name": parsed["city_raw"],
                        "icao": "",
                        "lat": None,
                        "lon": None,
                        "timezone": "",
                        "country": "",
                        "resolution_source": "geocoding-fallback",
                        "resolution_verified": False,
                    }
                resolution_source, resolution_station, aligned = _resolution_metadata(
                    event, station
                )
                markets_out = []
                for market in event.get("markets") or []:
                    outcomes = _parse_json_field(market.get("outcomes") or "[]")
                    prices = _parse_json_field(market.get("outcomePrices") or "[]")
                    tokens = _parse_json_field(market.get("clobTokenIds") or "[]")
                    label = market.get("groupItemTitle") or market.get("question") or ""
                    # Prefer outcome "Yes" price
                    yes_price = 0.0
                    token_id = ""
                    if isinstance(outcomes, list) and isinstance(prices, list):
                        for i, o in enumerate(outcomes):
                            if str(o).lower() == "yes" and i < len(prices):
                                yes_price = float(prices[i])
                                if isinstance(tokens, list) and i < len(tokens):
                                    token_id = str(tokens[i])
                                break
                        if yes_price == 0.0 and prices:
                            yes_price = float(prices[0])
                            if isinstance(tokens, list) and tokens:
                                token_id = str(tokens[0])
                    bucket_meta = parse_bucket_label(label)
                    if bucket_meta["temp_c"] is None:
                        continue
                    markets_out.append({
                        "label": label,
                        "yes_price": yes_price,
                        "token_id": token_id,
                        **bucket_meta,
                    })
                slug = event.get("slug") or ""
                event_id = str(event.get("id") or event.get("conditionId") or slug)
                if not event_id or event_id in seen_ids or not markets_out:
                    continue
                seen_ids.add(event_id)
                results.append({
                    **parsed,
                    "station": station,
                    "event_id": event_id,
                    "slug": slug,
                    "question": title,
                    "volume": float(event.get("volume") or event.get("volume24hr") or 0),
                    "url": f"https://polymarket.com/event/{slug}" if slug else "",
                    "buckets": markets_out,
                    "resolution_source": resolution_source
                    or station.get("resolution_source", ""),
                    "resolution_station": resolution_station,
                    "supported": aligned,
                    "unsupported_reason": ""
                    if aligned
                    else "Market resolution station is unavailable or does not match the observation location",
                })
            offset += limit
            if len(batch) < limit:
                break
    return results
