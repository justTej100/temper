"""Convert continuous temp forecast into Polymarket bucket probabilities."""

from __future__ import annotations

from math import erf, sqrt
from typing import Iterable


def _norm_cdf(x: float, mu: float, sigma: float) -> float:
    if sigma <= 1e-6:
        return 1.0 if x >= mu else 0.0
    z = (x - mu) / (sigma * sqrt(2.0))
    return 0.5 * (1.0 + erf(z))


def bucket_probabilities(
    point_c: float,
    residual_rmse: float,
    buckets: Iterable[dict],
) -> dict[str, float]:
    """
    buckets items: {label, temp_c, is_or_higher, is_or_lower}
    Returns label -> probability mass (sums ~1).
    """
    sigma = max(float(residual_rmse), 0.75)
    items = list(buckets)
    if not items:
        return {}

    # Sort discrete °C buckets; handle open-ended tails
    discrete = [b for b in items if b.get("temp_c") is not None and not b.get("is_or_higher") and not b.get("is_or_lower")]
    higher = [b for b in items if b.get("is_or_higher")]
    lower = [b for b in items if b.get("is_or_lower")]
    discrete.sort(key=lambda b: b["temp_c"])

    probs: dict[str, float] = {}
    # Treat each discrete label as [t-0.5, t+0.5) °C bin (Polymarket whole degrees)
    for b in discrete:
        t = float(b["temp_c"])
        p = _norm_cdf(t + 0.5, point_c, sigma) - _norm_cdf(t - 0.5, point_c, sigma)
        probs[b["label"]] = max(p, 0.0)

    for b in higher:
        t = float(b["temp_c"])
        probs[b["label"]] = max(1.0 - _norm_cdf(t - 0.5, point_c, sigma), 0.0)

    for b in lower:
        t = float(b["temp_c"])
        probs[b["label"]] = max(_norm_cdf(t + 0.5, point_c, sigma), 0.0)

    # Labels with no temp_c
    for b in items:
        if b["label"] not in probs:
            probs[b["label"]] = 0.0

    total = sum(probs.values())
    if total > 0:
        probs = {k: v / total for k, v in probs.items()}
    return probs
