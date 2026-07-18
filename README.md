# Amazon Price Forecasting

An on-demand product price forecasting site. Search a product, and the system fetches its price history, trains multiple time-series models (ARIMA family + Prophet), compares them on the same train/test split, and predicts when the next price dip is likely.

**Key design:** Models are trained per-product on demand — not pre-computed across an entire catalog. Compute and storage scale with actual user interest.

## Architecture

```
User Search → Cache Check → [hit] Serve instantly
                         → [miss] Celery job:
                                    1. Fetch price history (Keepa API or demo data)
                                    2. Fit ARIMA, SARIMA, ARIMAX, SARIMAX, Prophet (+ GARCH)
                                    3. Log metrics to MLflow
                                    4. Store best model → serve results
```

## Stack

| Layer | Technology |
|---|---|
| Backend | Django + Django REST Framework |
| Background jobs | Celery + Redis |
| Database | PostgreSQL |
| Forecasting | pmdarima, statsmodels, Prophet, arch (GARCH) |
| Experiment tracking | MLflow |
| Frontend | Next.js 15 + React + Tailwind + Chart.js |
| Hosting | Docker Compose (frontend + web + worker + db + redis + mlflow) |

## Quick Start

```bash
# Clone and configure
cp .env.example .env

# Start everything
docker compose up --build

# Open the app
open http://localhost:3000

# API root (JSON)
open http://localhost:8000

# MLflow experiment dashboard
open http://localhost:5000
```

Search for any product (e.g. "Sony headphones"). In demo mode, synthetic price history with realistic sale dips is generated instantly. The first search triggers model training (~30-60s); subsequent searches within 24h serve cached results.

## Data Sources

| Mode | Config | Description |
|---|---|---|
| **Demo** (default) | `DATA_SOURCE=demo` | Synthetic price history — no API key needed |
| **Keepa** | `DATA_SOURCE=keepa` + `KEEPA_API_KEY` | Legitimate Amazon price history API |

Scraping Amazon directly is intentionally not implemented (ToS violation + bot detection).

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/search/` | Search products, trigger forecasting |
| `GET` | `/api/jobs/<id>/` | Poll job status |
| `GET` | `/api/products/<id>/forecast/` | Price history + forecast + model comparison |
| `POST` | `/api/products/<id>/retrain/` | Force retrain all models |

### Search example

```bash
curl -X POST http://localhost:8000/api/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "Sony WH-1000XM5"}'
```

## Models Compared

All evaluated on the same 80/20 train/test split with MAE, MAPE, and RMSE:

- **ARIMA** — baseline, no seasonality
- **SARIMA** — weekly seasonality (m=7)
- **ARIMAX** — exogenous features (sale days, holidays, weekends)
- **SARIMAX** — seasonal + exogenous
- **Prophet** — multiple seasonalities + US holidays
- **GARCH** — volatility modeling (secondary, not directly comparable)

The model with the lowest MAE is flagged `is_best` and used for predictions.

## Project Structure

```
config/           Django settings, Celery, URLs
products/         Models, API views, Celery tasks, admin
forecasting/      Model training, metrics, storage, data sources
frontend/         Next.js React app
```

## Configuration

See `.env.example` for all settings. Key variables:

- `MODEL_CACHE_TTL_HOURS` — how long before retraining (default: 24)
- `MLFLOW_TRACKING_URI` — MLflow server URL
- `MODEL_STORAGE_BACKEND` — `local` or `s3` for model artifacts
- `KEEPA_API_KEY` — for live Amazon price data

## Development (without Docker)

### Backend

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Requires local Postgres + Redis + MLflow running
export DATABASE_URL=postgres://forecast:forecast@localhost:5433/forecast
python manage.py migrate
python manage.py runserver

# In separate terminals:
celery -A config worker -l info
mlflow server --port 5000
```

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Open http://localhost:3000 — the dev server hot-reloads against the Django API on port 8000.

## License

MIT — see [LICENSE](LICENSE).
