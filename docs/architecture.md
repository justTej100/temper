# Architecture

This document describes the implemented Temperature Predictor system. It is high-temperature-only:
Polymarket supplies market definitions and prices; Open-Meteo supplies historical observations,
not weather forecasts.

## System context

```mermaid
flowchart LR
  Person["Forecast reader / operator"]
  System["Temperature Predictor"]
  Gamma["Polymarket Gamma API<br/>markets and bucket prices"]
  OpenMeteo["Open-Meteo archive API<br/>historical daily highs"]
  Render["Render managed services<br/>PostgreSQL and Key Value"]

  Person -->|"HTTPS: inspect forecasts; request admin jobs"| System
  System -->|"Keyless HTTPS"| Gamma
  System -->|"Keyless HTTPS"| OpenMeteo
  System -->|"Private connection strings"| Render
```

## Container and trust-boundary design

```mermaid
flowchart TB
  subgraph Public["Public internet"]
    Browser["Browser"]
    Gamma["Polymarket Gamma"]
    OM["Open-Meteo archive"]
  end

  subgraph Ingress["Public HTTPS boundary"]
    Next["Next.js 15<br/>responsive dashboard"]
    API["FastAPI<br/>read API and job commands"]
  end

  subgraph Private["Private service network"]
    Worker["Celery worker<br/>concurrency 1 on Render"]
    Scheduler["Render cron<br/>scheduled workflow"]
    Redis[("Redis / Key Value<br/>queue and results")]
    Postgres[("PostgreSQL<br/>authoritative domain data")]
    MLflow["MLflow tracking server"]
    Artifact[("MLflow service-local disk<br/>authoritative artifacts")]
  end

  Browser -->|"HTML and assets"| Next
  Browser -->|"JSON; admin token only for operator writes"| API
  API --> Postgres
  API --> Redis
  Redis --> Worker
  Scheduler -->|"invoke scheduled workflow"| Postgres
  Scheduler --> Redis
  Worker --> Gamma
  Worker --> OM
  Worker --> Postgres
  Worker --> MLflow
  MLflow --> Artifact
```

The browser uses the build-time `NEXT_PUBLIC_API_URL`. The API and frontend are the only public
services. Reads are unauthenticated. Production sync/training actions require `X-Admin-Token` when
configured; if production has no token, public write actions return `503`.

## Render deployment

```mermaid
flowchart TB
  Internet["Internet"] -->|"HTTPS"| Web["web: temperature-predictor-web<br/>Node runtime; / health check"]
  Internet -->|"HTTPS"| API["web: temperature-predictor-api<br/>Docker; /health"]
  Web -->|"https://API_HOST"| API

  subgraph RenderPrivate["Render private network"]
    API --> DB[("managed PostgreSQL<br/>internal connectionString")]
    API --> KV[("managed Key Value<br/>internal connectionString")]
    KV --> Worker["worker: Docker<br/>Celery concurrency 1"]
    Cron["cron: every 3 hours<br/>Docker scheduled workflow"] --> DB
    Cron --> KV
    Worker --> DB
    Worker --> MLF["private service: MLflow<br/>port 5000; /health"]
    MLF --> Disk[("10 GB service-local disk<br/>/var/data/artifacts")]
  end

  Deploy["API pre-deploy"] -->|"alembic upgrade head"| DB
```

The MLflow disk cannot be mounted by API or worker because Render disks are service-local.
Workers upload artifacts through MLflow. The backend’s `/tmp/model_artifacts` path is scratch
storage and is not authoritative. PostgreSQL currently also stores MLflow tracking metadata; the
MLflow disk stores served artifacts.

## Backend package/component design

```mermaid
flowchart LR
  Main["app.main<br/>FastAPI, CORS, health, request IDs"]
  Routes["app.api.routes<br/>HTTP schemas and job commands"]
  Schemas["app.schemas<br/>Pydantic contracts"]
  Services["app.services<br/>sync, persistence, forecast orchestration"]
  Tasks["app.tasks<br/>Celery lifecycle and scheduled workflow"]
  Models["app.models<br/>SQLModel domain tables"]
  DB["app.db<br/>engine and sessions"]
  Config["app.config<br/>environment settings"]
  Trainer["forecasting.trainer<br/>rolling evaluation, refit, forecast"]
  Buckets["forecasting.buckets<br/>calibration and bucket math"]
  Metrics["forecasting.metrics<br/>MAE, RMSE, bias"]
  Stations["forecasting.stations<br/>city and station resolution"]
  GammaAdapter["forecasting.data_sources.polymarket"]
  OpenAdapter["forecasting.data_sources.open_meteo"]

  Main --> Routes
  Main --> Config
  Routes --> Schemas
  Routes --> Services
  Routes --> Tasks
  Routes --> Models
  Routes --> DB
  Tasks --> Services
  Tasks --> Models
  Tasks --> DB
  Services --> Models
  Services --> Trainer
  Services --> Buckets
  Services --> GammaAdapter
  Services --> OpenAdapter
  Services --> Stations
  Trainer --> Metrics
  Trainer --> Buckets
  DB --> Config
```

Dependency direction is from delivery/orchestration toward domain and forecasting utilities.
External adapters do not call API routes.

## UML class view

```mermaid
classDiagram
  class City {
    +int id
    +str name
    +str country
    +float latitude
    +float longitude
    +str icao
    +str timezone
    +str data_source
    +bool resolution_verified
  }
  class Market {
    +int id
    +int city_id
    +str polymarket_event_id
    +date target_date
    +TempType temp_type
    +bool active
    +bool supported
    +str resolution_station
  }
  class TempBucket {
    +int id
    +int market_id
    +str label
    +float temp_c
    +float yes_price
    +bool is_or_higher
    +bool is_or_lower
  }
  class Observation {
    +int city_id
    +date observed_on
    +float high_c
    +str source
  }
  class ForecastJob {
    +int market_id
    +JobType job_type
    +JobStatus status
    +int attempts
    +str error_message
  }
  class CityModel {
    +int city_id
    +str model_type
    +float mae
    +float rmse
    +float bias
    +date data_start
    +date data_end
    +str artifact_uri
    +bool is_best
  }
  class ModelPrediction {
    +int market_id
    +int city_model_id
    +date target_date
    +float point_forecast_c
    +dict bucket_probs
    +list forecast_dates
  }
  class EdgeSnapshot {
    +int market_id
    +int bucket_id
    +float model_prob
    +float market_prob
    +float edge
  }
  class ForecastTrainer {
    +rolling_origin_evaluate()
    +select_model()
    +refit_full_history()
    +forecast_exact_horizon()
  }
  class MarketSyncService {
    +sync_markets()
    +upsert_market()
    +upsert_buckets()
  }

  City "1" --> "0..*" Market
  City "1" --> "0..*" Observation
  City "1" --> "0..*" CityModel
  Market "1" --> "1..*" TempBucket
  Market "1" --> "0..*" ForecastJob
  Market "1" --> "0..*" ModelPrediction
  Market "1" --> "0..*" EdgeSnapshot
  CityModel "0..1" --> "0..*" ModelPrediction
  TempBucket "1" --> "0..*" EdgeSnapshot
  ForecastTrainer ..> CityModel
  ForecastTrainer ..> ModelPrediction
  MarketSyncService ..> Market
  MarketSyncService ..> TempBucket
```

## Entity relationships and constraints

```mermaid
erDiagram
  CITY ||--o{ MARKET : owns
  CITY ||--o{ OBSERVATION : has
  CITY ||--o{ CITY_MODEL : trains
  MARKET ||--|{ TEMP_BUCKET : defines
  MARKET ||--o{ FORECAST_JOB : queues
  MARKET ||--o{ MODEL_PREDICTION : receives
  MARKET ||--o{ EDGE_SNAPSHOT : records
  CITY_MODEL o|--o{ MODEL_PREDICTION : generates
  TEMP_BUCKET ||--o{ EDGE_SNAPSHOT : compares

  CITY {
    int id PK
    string name "UQ with country"
    string country "UQ with name"
    string icao "indexed"
    string timezone
  }
  MARKET {
    int id PK
    int city_id FK
    string polymarket_event_id UK
    string polymarket_slug UK
    string temp_type "CHECK high"
    date target_date "indexed"
    boolean active
  }
  TEMP_BUCKET {
    int id PK
    int market_id FK "UQ with label and token"
    string label
    string token_id
    float yes_price
  }
  OBSERVATION {
    int id PK
    int city_id FK "UQ with observed_on and source"
    date observed_on
    string source
    float high_c
  }
  FORECAST_JOB {
    int id PK
    int market_id FK "partial UQ while active forecast"
    string job_type
    string status
    datetime created_at
  }
  CITY_MODEL {
    int id PK
    int city_id FK
    int job_id FK
    string model_type
    string dataset_fingerprint
    string mlflow_run_id
  }
  MODEL_PREDICTION {
    int id PK
    int market_id FK
    int city_model_id FK
    date target_date
    json bucket_probs
    datetime generated_at
  }
  EDGE_SNAPSHOT {
    int id PK
    int market_id FK
    int bucket_id FK
    float edge
    datetime generated_at
  }
```

Important constraints are migration-owned: city `(name, country)`, observation
`(city_id, observed_on, source)`, market event ID and slug, bucket `(market_id, label)`,
nonempty bucket token per market, and one active forecast job per market. Predictions, edges,
jobs, and models are historical records with configurable retention targets; cleanup scheduling
is an operational responsibility.

## Market synchronization sequence

```mermaid
sequenceDiagram
  actor Operator
  participant API as FastAPI
  participant Redis
  participant Worker
  participant Gamma
  participant DB as PostgreSQL

  Operator->>API: POST /api/sync/
  API->>DB: find active sync job
  alt active job exists
    API-->>Operator: existing job_id; deduplicated=true
  else create
    API->>DB: insert queued ForecastJob
    API->>Redis: enqueue sync_polymarket_markets
    API-->>Operator: job_id; queued
    Redis->>Worker: deliver task
    Worker->>DB: status=fetching
    Worker->>Gamma: paginated active high-temperature events
    Gamma-->>Worker: events, buckets, prices, resolution metadata
    Worker->>DB: upsert cities, markets, buckets; deactivate missing markets
    Worker->>DB: status=complete or failed
  end
```

## Scheduled training and forecast sequence

```mermaid
sequenceDiagram
  participant Cron as Render cron / Celery beat
  participant Workflow as scheduled workflow
  participant Gamma
  participant DB as PostgreSQL
  participant Redis
  participant Worker
  participant OM as Open-Meteo
  participant MLflow

  Cron->>Workflow: run_scheduled_workflow
  Workflow->>Gamma: synchronize markets
  Workflow->>DB: select active supported markets
  loop each market without active job
    Workflow->>DB: create queued forecast job
    Workflow->>Redis: enqueue run_forecast_pipeline
  end
  Redis->>Worker: forecast task
  Worker->>OM: local-time historical daily highs
  Worker->>DB: upsert observations; status=training/evaluating
  Worker->>Worker: rolling evaluation, select, full-history refit
  Worker->>MLflow: metrics, lineage, model artifact
  Worker->>DB: CityModel, ModelPrediction, EdgeSnapshot, complete
```

## On-demand retraining sequence

```mermaid
sequenceDiagram
  actor Operator
  participant UI as Next.js
  participant API as FastAPI
  participant DB as PostgreSQL
  participant Redis
  participant Worker

  Operator->>UI: Refresh forecast
  UI->>API: POST /api/markets/{id}/train
  API->>DB: validate supported market; deduplicate active job
  API->>Redis: enqueue when newly created
  API-->>UI: job_id and status
  loop until terminal state
    UI->>API: GET /api/jobs/{job_id}
    API-->>UI: queued/fetching/training/evaluating
  end
  Worker->>DB: persist forecast or failure
  UI->>API: GET /api/markets/{id}
  API-->>UI: refreshed detail
```

## Frontend polling and recovery sequence

```mermaid
sequenceDiagram
  actor User
  participant UI as Responsive UI
  participant API

  User->>UI: request refresh
  UI->>UI: retain content; announce queued state
  UI->>API: POST command
  alt accepted
    API-->>UI: job_id
    loop bounded polling
      UI->>API: GET job
      API-->>UI: stage
      UI->>UI: aria-live stage update
    end
    UI->>API: refetch market
  else disabled or invalid
    API-->>UI: structured error
    UI->>UI: actionable inline error and retry
  end
```

## Forecasting data flow

```mermaid
flowchart LR
  Gamma["Gamma markets<br/>buckets and odds"] --> ValidateMarket["high-only parsing<br/>station support check"]
  OM["Open-Meteo archive<br/>local daily highs"] --> ValidateSeries["units, continuity,<br/>minimum history"]
  ValidateMarket --> Persist["idempotent persistence"]
  ValidateSeries --> Persist
  Persist --> Splits["horizon-aware<br/>rolling-origin folds"]
  Splits --> Candidates["last value · seasonal naive<br/>ARIMA · SARIMA · Prophet"]
  Candidates --> Metrics["MAE ranking<br/>RMSE and bias"]
  Metrics --> Select["quality gate and select"]
  Select --> Refit["refit on full validated history"]
  Refit --> Exact["exact target-date horizon"]
  Splits --> Errors["out-of-fold errors"]
  Errors --> Calibration["empirical calibration<br/>normalized buckets"]
  Exact --> Calibration
  Calibration --> Storage["CityModel · ModelPrediction<br/>EdgeSnapshot · MLflow"]
  Storage --> API["FastAPI contracts"]
  API --> UI["summary · uncertainty · accessible chart<br/>bucket comparison · limitations"]
```

The chart’s shaded guide uses historical RMSE around forecast values. It is explicitly labeled as
an error guide, not a guaranteed confidence interval, and the same forecast values are available in
a text table.

## Codebase tree and ownership

```text
.
├── backend/
│   ├── app/
│   │   ├── api/routes.py       HTTP queries, write authorization, job endpoints
│   │   ├── config.py           environment configuration
│   │   ├── db.py               SQLModel engine and sessions
│   │   ├── main.py             FastAPI app, CORS, request IDs, health/readiness
│   │   ├── models.py           persisted domain entities and constraints
│   │   ├── schemas.py          external API contracts
│   │   ├── services.py         synchronization and forecast orchestration
│   │   └── tasks.py            Celery tasks, retries, scheduled workflow
│   ├── forecasting/
│   │   ├── data_sources/       Polymarket and Open-Meteo adapters
│   │   ├── buckets.py          probability calibration and bucket semantics
│   │   ├── metrics.py          forecast evaluation metrics
│   │   ├── stations.py         city/station resolution
│   │   └── trainer.py          splits, candidates, selection, refit, forecast
│   ├── alembic/                versioned PostgreSQL schema
│   └── tests/                  backend unit/integration tests
├── frontend/
│   ├── public/                 favicon and static assets
│   └── src/
│       ├── app/                dashboard, detail route, metadata, theme
│       ├── components/         chart, tables, header, loading states
│       ├── lib/                API client, contracts, labeled example fixture
│       └── test/               loading/error/success/filter/chart UI tests
├── docs/                       architecture, deployment, model, operations
├── .github/workflows/          CI
├── docker-compose.yml          production-like local orchestration
├── docker-compose.dev.yml      source-mounted development behavior
└── render.yaml                 complete Render Blueprint
```

## API-to-storage trace

| API operation | Route layer | Service/task path | Primary storage effects |
| --- | --- | --- | --- |
| List markets | `list_markets` | read queries | `Market`, `City`, latest `CityModel`, `TempBucket`, `EdgeSnapshot` |
| Market detail | `get_market` | read queries | `Observation`, `ModelPrediction`, `CityModel`, `ForecastJob`, buckets/edges |
| Sync | `trigger_sync` | `sync_polymarket_markets` → `sync_markets` | upsert cities/markets/buckets; deactivate stale markets; update job |
| Forecast | `forecast` / `train` | `run_forecast_pipeline` → `run_forecast_for_market` | observations, model provenance, prediction, immutable edge snapshots, job |
| Job status | `get_job` | read query | `ForecastJob` |
| Disagreements | `list_edges` | read query | latest `EdgeSnapshot` joined to market/bucket/city |

The route module currently performs some joining and sorting directly; services own mutations and
forecast orchestration. This distinction is the contributor ownership boundary, even where query
optimization remains possible.
