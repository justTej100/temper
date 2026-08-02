"""Polymarket Gamma API — discover high/low temperature markets."""

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
    r"(?P<kind>Highest|Lowest)\s+temperature\s+in\s+(?P<city>.+?)\s+on\s+(?P<month>\w+)\s+(?P<day>\d{1,2})",
    re.IGNORECASE,
)
BUCKET_RE = re.compile(
    r"(?P<temp>-?\d+(?:\.\d+)?)\s*°?\s*C(?:\s+or\s+(?P<bound>higher|lower))?",
    re.IGNORECASE,
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


def parse_title(question: str) -> dict | None:
    m = TITLE_RE.search(question or "")
    if not m:
        return None
    month = MONTHS.get(m.group("month").lower())
    if not month:
        return None
    year = datetime.utcnow().year
    day = int(m.group("day"))
    try:
        target = date(year, month, day)
    except ValueError:
        return None
    # If target date is > 6 months in the past, assume next year wrap isn't needed;
    # if far in future relative to now+60d with past month, bump year.
    today = date.today()
    if target < today.replace(month=1, day=1) and month < today.month - 1:
        target = date(year + 1, month, day)
    return {
        "temp_type": "high" if m.group("kind").lower() == "highest" else "low",
        "city_raw": m.group("city").strip(),
        "target_date": target,
    }


def parse_bucket_label(label: str) -> dict:
    m = BUCKET_RE.search(label or "")
    if not m:
        return {"temp_c": None, "is_or_higher": False, "is_or_lower": False}
    bound = (m.group("bound") or "").lower()
    return {
        "temp_c": float(m.group("temp")),
        "is_or_higher": bound == "higher",
        "is_or_lower": bound == "lower",
    }


def fetch_weather_events(limit: int = 100, max_pages: int = 10) -> list[dict]:
    settings = get_settings()
    results: list[dict] = []
    offset = 0
    with httpx.Client(timeout=30.0) as client:
        for _ in range(max_pages):
            resp = client.get(
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
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            for event in batch:
                title = event.get("title") or event.get("question") or ""
                parsed = parse_title(title)
                if not parsed:
                    # Also check nested markets
                    markets = event.get("markets") or []
                    if markets:
                        parsed = parse_title(markets[0].get("question") or title)
                    if not parsed:
                        continue
                station = resolve_city(parsed["city_raw"])
                if not station:
                    logger.debug("No station map for city %s", parsed["city_raw"])
                    # Still include with geocode fallback coords (0,0) — open-meteo needs real coords
                    station = {
                        "name": parsed["city_raw"],
                        "icao": "",
                        "lat": 0.0,
                        "lon": 0.0,
                        "country": "",
                    }
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
                    markets_out.append({
                        "label": label,
                        "yes_price": yes_price,
                        "token_id": token_id,
                        **bucket_meta,
                    })
                slug = event.get("slug") or ""
                results.append({
                    **parsed,
                    "station": station,
                    "event_id": str(event.get("id") or event.get("conditionId") or slug),
                    "slug": slug,
                    "question": title,
                    "volume": float(event.get("volume") or event.get("volume24hr") or 0),
                    "url": f"https://polymarket.com/event/{slug}" if slug else "",
                    "buckets": markets_out,
                })
            offset += limit
            if len(batch) < limit:
                break
    return results
