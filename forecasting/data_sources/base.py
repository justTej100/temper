"""Data source interface and factory."""

from dataclasses import dataclass
from datetime import datetime

from django.conf import settings


@dataclass
class PriceRecord:
    price: float
    recorded_at: datetime


def get_data_source():
    """Return the configured data source adapter."""
    if settings.DATA_SOURCE == "keepa" and settings.KEEPA_API_KEY:
        from .keepa import KeepaDataSource

        return KeepaDataSource()
    from .demo import DemoDataSource

    return DemoDataSource()
