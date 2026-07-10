"""Keepa API data source for legitimate Amazon price history."""

import logging
from datetime import datetime, timedelta, timezone

import requests
from django.conf import settings

from .base import PriceRecord

logger = logging.getLogger(__name__)

KEEPA_API_URL = "https://api.keepa.com"


class KeepaDataSource:
    """Fetches price history from the Keepa API."""

    def __init__(self):
        self.api_key = settings.KEEPA_API_KEY

    def search(self, query: str) -> list[dict]:
        """Search Keepa product database."""
        response = requests.get(
            f"{KEEPA_API_URL}/search",
            params={
                "key": self.api_key,
                "domain": 1,  # amazon.com
                "type": "product",
                "term": query,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for product in data.get("products", [])[:5]:
            asin = product.get("asin", "")
            title = product.get("title", "Unknown Product")
            results.append({
                "name": title,
                "external_id": asin,
                "source_url": f"https://www.amazon.com/dp/{asin}",
            })
        return results

    def fetch_price_history(self, external_id: str, days: int = 365) -> list[PriceRecord]:
        """Fetch price history for an ASIN."""
        response = requests.get(
            f"{KEEPA_API_URL}/product",
            params={
                "key": self.api_key,
                "domain": 1,
                "asin": external_id,
                "history": 1,
                "days": days,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        products = data.get("products", [])
        if not products:
            raise ValueError(f"No product found for ASIN {external_id}")

        product = products[0]
        csv_data = product.get("csv", [])
        if not csv_data or len(csv_data) < 2:
            raise ValueError(f"No price history for ASIN {external_id}")

        # Keepa CSV index 1 = Amazon price (in cents, Keepa time format)
        amazon_prices = csv_data[1] if len(csv_data) > 1 else []
        records = self._parse_keepa_csv(amazon_prices)
        return records

    @staticmethod
    def _parse_keepa_csv(csv_array: list) -> list[PriceRecord]:
        """Parse Keepa's interleaved [time, value, time, value, ...] format."""
        records = []
        for i in range(0, len(csv_array) - 1, 2):
            keepa_time = csv_array[i]
            price_cents = csv_array[i + 1]
            if keepa_time is None or price_cents is None or price_cents < 0:
                continue
            # Keepa time: minutes since Jan 1, 2011 UTC
            recorded_at = datetime(2011, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=keepa_time)
            price = price_cents / 100.0
            records.append(PriceRecord(price=price, recorded_at=recorded_at))
        return records
