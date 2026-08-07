# Model card

## Intended use

Temperature Predictor estimates an active market city’s daily high for the exact market target
date and compares calibrated temperature-bucket probabilities with Polymarket prices. It is an
experimental analytical aid, not an official meteorological forecast, automated trading system, or
financial recommendation.

## Data

- Polymarket Gamma: active high-temperature event identity, target date, bucket definitions,
  prices, volume, and available resolution metadata.
- Open-Meteo archive: historical daily maximum temperature at a validated city/station coordinate,
  requested in the city’s local timezone.

No paid API key, private user data, weather forecast feed, METAR feed, or NWS feed is used.
Open-Meteo grid values may differ from an official resolution station; ambiguous mappings are
marked unsupported.

## Evaluation and selection

Validated history is split with horizon-aware rolling origins that approximate target horizons.
Transparent last-value and seasonal-naive baselines are evaluated with bounded ARIMA, SARIMA, and
optional Prophet candidates. Mean absolute error ranks comparable models; RMSE and signed bias are
reported. Candidate failures are isolated, and a baseline remains available when optional models
fail.

The winning model is refit on all validated history before producing the exact horizon from the
last observation to target date. Expired or out-of-range targets fail rather than silently selecting
the nearest date.

## Probability calibration

Out-of-fold forecast errors form an empirical residual distribution. Bucket math handles bounded
and open-ended Celsius/Fahrenheit labels, applies a fallback when calibration samples are
insufficient, and normalizes probabilities to sum to one. “Difference” in the UI means model
probability minus market probability; it is not guaranteed edge or expected profit.

## Lineage

Each model record includes city/station, data start/end, dataset fingerprint, target horizon,
candidate parameters, backtest folds, MAE/RMSE/bias, calibration sample size, training time,
code/model version, MLflow run ID, and artifact URI where available. Predictions reference model
metadata and preserve generated bucket probabilities and forecast path.

## Limitations

- Historical temperature alone cannot represent current atmospheric conditions or abrupt changes.
- Missing, revised, or spatially mismatched observations can bias results.
- Backtests may not cover future extremes or distribution shift.
- RMSE shown around the line is an understandable historical error guide, not a formal guaranteed
  confidence interval.
- Calibration quality depends on enough representative out-of-fold errors.
- Market probabilities can move after collection and prices do not necessarily sum cleanly across
  illiquid buckets.
- Model quality varies by city, season, horizon, and station history.

## Monitoring

Investigate minimum-history, continuity, implausible-value, candidate-failure, baseline-regression,
and probability-normalization gates. Compare recent city error with seasonal naive, watch signed
bias and calibration sample size, and suppress unsupported/low-quality results instead of presenting
false precision. Record every deployed model change in MLflow and retain a rollback artifact.
