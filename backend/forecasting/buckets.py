"""Convert continuous temp forecast into Polymarket bucket probabilities."""

from __future__ import annotations

from math import erf, sqrt
from typing import Iterable

import numpy as np


def _norm_cdf(x: float, mu: float, sigma: float) -> float:
    if sigma <= 1e-6:
        return 1.0 if x >= mu else 0.0
    z = (x - mu) / (sigma * sqrt(2.0))
    return 0.5 * (1.0 + erf(z))


def bucket_probabilities(
    point_c: float,
    residual_rmse: float,
    buckets: Iterable[dict],
    calibration_errors: Iterable[float] | None = None,
) -> dict[str, float]:
    """
    buckets items: {label, temp_c, is_or_higher, is_or_lower}
    Returns label -> probability mass (sums ~1).
    """
    sigma = max(float(residual_rmse), 0.75)
    items = list(buckets)
    if not items:
        return {}

    # Source-unit width is retained during parsing (1°F != 1°C).
    discrete = [b for b in items if b.get("temp_c") is not None and not b.get("is_or_higher") and not b.get("is_or_lower")]
    higher = [b for b in items if b.get("is_or_higher")]
    lower = [b for b in items if b.get("is_or_lower")]
    discrete.sort(key=lambda b: b["temp_c"])

    probs: dict[str, float] = {}
    errors = np.asarray(list(calibration_errors or []), dtype=float)
    errors = errors[np.isfinite(errors)]
    samples = point_c + errors if len(errors) >= 20 else None

    def interval_probability(lower_bound: float, upper_bound: float) -> float:
        if samples is not None:
            return float(np.mean((samples >= lower_bound) & (samples < upper_bound)))
        return _norm_cdf(upper_bound, point_c, sigma) - _norm_cdf(
            lower_bound, point_c, sigma
        )

    for b in discrete:
        t = float(b["temp_c"])
        half_width = float(b.get("bucket_width_c") or 1.0) / 2.0
        p = interval_probability(t - half_width, t + half_width)
        probs[b["label"]] = max(p, 0.0)

    for b in higher:
        t = float(b["temp_c"])
        half_width = float(b.get("bucket_width_c") or 1.0) / 2.0
        if samples is not None:
            probability = float(np.mean(samples >= t - half_width))
        else:
            probability = 1.0 - _norm_cdf(t - half_width, point_c, sigma)
        probs[b["label"]] = max(probability, 0.0)

    for b in lower:
        t = float(b["temp_c"])
        half_width = float(b.get("bucket_width_c") or 1.0) / 2.0
        if samples is not None:
            probability = float(np.mean(samples < t + half_width))
        else:
            probability = _norm_cdf(t + half_width, point_c, sigma)
        probs[b["label"]] = max(probability, 0.0)

    # Labels with no temp_c
    for b in items:
        if b["label"] not in probs:
            probs[b["label"]] = 0.0

    total = sum(probs.values())
    if total > 0:
        probs = {k: v / total for k, v in probs.items()}
    else:
        closest = min(
            (b for b in items if b.get("temp_c") is not None),
            key=lambda b: abs(float(b["temp_c"]) - point_c),
            default=None,
        )
        if closest:
            probs[closest["label"]] = 1.0
    return probs
