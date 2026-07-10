"""Known sale days and holidays for exogenous features in ARIMAX/SARIMAX."""

import pandas as pd

# Major US retail sale events (month, day)
SALE_DAYS = [
    (1, 1),    # New Year
    (2, 14),   # Valentine's Day
    (7, 4),    # Independence Day
    (11, 11),  # Veterans Day / Singles Day
    (11, 29),  # Black Friday (approx — varies)
    (12, 25),  # Christmas
    (12, 26),  # Boxing Day
    (7, 15),   # Prime Day (approx)
]

# Prime Day and Black Friday shift yearly; these are approximations for demo
PRIME_DAY_RANGES = [
    ("2023-07-11", "2023-07-12"),
    ("2024-07-16", "2024-07-17"),
    ("2025-07-08", "2025-07-11"),
]

BLACK_FRIDAY_DATES = [
    "2023-11-24",
    "2024-11-29",
    "2025-11-28",
]


def build_exogenous_features(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Build exogenous feature matrix for ARIMAX/SARIMAX."""
    dates = pd.DatetimeIndex(dates).tz_localize(None)
    features = pd.DataFrame(index=dates)
    features["is_weekend"] = (dates.dayofweek >= 5).astype(int)
    features["is_sale_day"] = 0
    features["is_prime_day"] = 0
    features["is_black_friday"] = 0

    for month, day in SALE_DAYS:
        mask = (dates.month == month) & (dates.day == day)
        features.loc[mask, "is_sale_day"] = 1

    for start, end in PRIME_DAY_RANGES:
        mask = (dates >= start) & (dates <= end)
        features.loc[mask, "is_prime_day"] = 1

    for bf in BLACK_FRIDAY_DATES:
        bf_date = pd.Timestamp(bf)
        mask = (dates >= bf_date - pd.Timedelta(days=1)) & (dates <= bf_date + pd.Timedelta(days=3))
        features.loc[mask, "is_black_friday"] = 1

    return features
