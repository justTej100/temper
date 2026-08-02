# TempEdge

Polymarket daily **high/low temperature** forecasting. We discover active weather markets from the [Polymarket Gamma API](https://gamma-api.polymarket.com), train an ARIMA-family + Prophet bakeoff on free station history (Open-Meteo / METAR / NWS), turn the best model into bucket probabilities, and surface **edges** vs crowd odds.

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

First load: click **Sync Polymarket**, open a market, wait for the Celery job to fetch history and train (~1 min).

## Architecture

```mermaid
flowchart TB
  subgraph clients [Clients]
    UI[Next.js TempEdge UI]
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
    METAR[Aviation METAR]
    NWS[NWS api.weather.gov]
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
  Worker --> METAR
  Worker --> NWS
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
  API->>Celery: sync_polymarket_markets
  Celery->>Gamma: GET /events
  Celery->>API: upsert City/Market/TempBucket

  User->>Next: Open market detail
  Next->>API: GET /api/markets/{id}
  API->>Celery: run_forecast_pipeline (if stale)
  Celery->>OM: daily high/low history
  Celery->>Celery: bakeoff ARIMA..Prophet
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
| Weather | Open-Meteo, METAR, NWS |
| Markets | Polymarket Gamma |

## What it does

1. **Discover** all active high/low temp markets from Polymarket  
2. **Bakeoff** ARIMA / SARIMA / ARIMAX / SARIMAX / Prophet per city series  
3. **Predict** target-day temp; map residual RMSE → °C bucket probabilities  
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
| GET | `/api/markets/` | List markets (`?temp_type=&sort=edge\|volume\|date`) |
| GET | `/api/markets/{id}` | Detail + history + bakeoff + buckets/edges |
| POST | `/api/markets/{id}/retrain` | Force train |
| GET | `/api/jobs/{id}` | Job status |
| GET | `/api/edges/` | Top disagreements |
| POST | `/api/sync/` | Refresh Polymarket catalog |

## License

MIT — see [LICENSE](LICENSE).
