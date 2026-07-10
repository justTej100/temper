"""Demo data source — generates realistic synthetic price history with dips."""

import hashlib
import random
from datetime import datetime, timedelta, timezone

from .base import PriceRecord


class DemoDataSource:
    """Generates synthetic price history for development and demos."""

    def search(self, query: str) -> list[dict]:
        """Return mock search results."""
        products = [
            {
                "name": f"{query} — Wireless Bluetooth Headphones",
                "external_id": self._hash_id(query, "headphones"),
                "source_url": f"https://example.com/product/{self._hash_id(query, 'headphones')}",
            },
            {
                "name": f"{query} Pro — Noise Cancelling Earbuds",
                "external_id": self._hash_id(query, "earbuds"),
                "source_url": f"https://example.com/product/{self._hash_id(query, 'earbuds')}",
            },
            {
                "name": f"{query} Max — Over-Ear Studio Headphones",
                "external_id": self._hash_id(query, "studio"),
                "source_url": f"https://example.com/product/{self._hash_id(query, 'studio')}",
            },
        ]
        return products

    def fetch_price_history(self, external_id: str, days: int = 365) -> list[PriceRecord]:
        """Generate synthetic daily price history with seasonal dips."""
        rng = random.Random(external_id)
        base_price = rng.uniform(29.99, 299.99)
        records = []
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(days, 0, -1):
            date = today - timedelta(days=i)
            day_of_year = date.timetuple().tm_yday

            # Weekly cycle (weekend dips)
            weekly = -2.0 if date.weekday() >= 5 else 0.0

            # Seasonal sale events
            sale_dip = 0.0
            if date.month == 11 and 24 <= date.day <= 28:
                sale_dip = -base_price * 0.25
            elif date.month == 7 and 10 <= date.day <= 17:
                sale_dip = -base_price * 0.20
            elif date.month == 12 and date.day >= 20:
                sale_dip = -base_price * 0.15

            # Random noise
            noise = rng.gauss(0, base_price * 0.02)

            # Slow trend
            trend = base_price * 0.0001 * (days - i)

            price = max(base_price + weekly + sale_dip + noise + trend, base_price * 0.5)
            price = round(price, 2)

            records.append(PriceRecord(price=price, recorded_at=date.replace(tzinfo=None)))

        return records

    @staticmethod
    def _hash_id(query: str, suffix: str) -> str:
        return hashlib.md5(f"{query}:{suffix}".encode()).hexdigest()[:12]
