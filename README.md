# Temperature Predictor

Polymarket daily **highest-temperature** forecasting. The service discovers active high-temperature markets, evaluates transparent baselines plus ARIMA/SARIMA/Prophet candidates against local-day Open-Meteo history, calibrates bucket probabilities, and records their disagreement with market odds.

No paid price APIs. No Django. No auth.

## Run

```bash
docker compose up --build --watch
```

| Service | URL |
|---|---|
| UI | http://localhost:3000 |
| API + OpenAPI | http://localhost:8000/docs |
| MLflow | http://localhost:5000 |
| Example UI (no ML) | http://localhost:3000/example |

First load: queue **Sync Polymarket**, then explicitly start a market training job and poll its returned job ID.

## Architecture

```mermaid
flowchart TB
  subgraph clients [Clients]
    UI[Next.js Temperature Predictor UI]
    Docs[OpenAPI /docs]
  end

  subgraph apiLayer [API Layer]
    API[FastAPI]
  end

  subgraph workers [Workers]
    Beat[Celery Beat]
    Worker[Celery Worker]
  end

  subgraph data [Data Sources]
    Gamma[Polymarket Gamma]
    OM[Open-Meteo]
  end

  subgraph store [Storage]
    PG[(Postgres)]
    Redis[(Redis)]
    Artifacts[Model artifacts]
    MLflow[(MLflow)]
  end

  UI --> API
  Docs --> API
  API --> PG
  API --> Redis
  Beat -->|sync markets| Worker
  Worker --> Gamma
  Worker --> OM
  Worker --> PG
  Worker --> Artifacts
  Worker --> MLflow
  API -->|enqueue forecast| Redis
  Redis --> Worker
```

### Request flow

```mermaid
sequenceDiagram
  participant User
  participant Next as Next.js
  participant API as FastAPI
  participant Celery as Celery Worker
  participant Gamma as Polymarket Gamma
  participant OM as Open-Meteo

  User->>Next: Open markets / Sync
  Next->>API: POST /api/sync/
  API->>Celery: queued sync job
  Celery->>Gamma: GET /events
  Celery->>API: upsert City/Market/TempBucket

  User->>Next: Request market training
  Next->>API: POST /api/markets/{id}/train
  API->>Celery: run_forecast_pipeline
  Celery->>OM: local-day daily-high history
  Celery->>Celery: rolling-origin model evaluation
  Celery->>Celery: bucket probs + edges
  Next->>API: poll until complete
  API-->>Next: history, forecast, bakeoff, edges
```

## Stack

| Layer | Choice |
|---|---|
| API | FastAPI + SQLModel |
| Jobs | Celery + Redis (+ beat) |
| DB | PostgreSQL |
| Tracking | MLflow |
| ML | pmdarima, Prophet, statsmodels |
| UI | Next.js 15 + Chart.js |
| Weather observations | Open-Meteo archive API |
| Markets | Polymarket Gamma |

## What it does

1. **Discover** active highest-temperature markets from Polymarket  
2. **Evaluate** last-value, seasonal-naive, ARIMA, SARIMA, and Prophet models per city  
3. **Predict** the exact target day and calibrate °C/°F bucket probabilities  
4. **Compare** to Polymarket Yes prices; flag \|edge\| ≥ 8%  

## Project layout

```
backend/
  app/           FastAPI, models, routes, Celery tasks
  forecasting/   adapters, trainer, bucket math
frontend/        Next.js UI
docker-compose.yml
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/markets/` | List high-temperature markets (`?sort=edge\|volume\|date`) |
| GET | `/api/markets/{id}` | Detail + history + bakeoff + buckets/edges |
| POST | `/api/markets/{id}/train` | Explicitly train/forecast (deduplicated) |
| POST | `/api/markets/{id}/forecast` | Explicitly forecast (deduplicated) |
| GET | `/api/jobs/{id}` | Job status |
| GET | `/api/edges/` | Top disagreements |
| POST | `/api/sync/` | Refresh Polymarket catalog |
| GET | `/health` | Process liveness |
| GET | `/ready` | PostgreSQL/Redis readiness |

## License

MIT — see [LICENSE](LICENSE).
