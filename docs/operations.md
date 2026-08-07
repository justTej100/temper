# Operations

## Health and logs

- `/health` confirms the API process can answer.
- `/ready` verifies PostgreSQL and Redis; use it for diagnostics, not liveness restarts.
- Search API logs by `x-request-id`. The same value is returned on responses.
- Celery task logs and `ForecastJob.error_message` provide job failure context.
- MLflow `/health` verifies the private tracking service, not artifact correctness.

## Migrations

Render runs `alembic upgrade head` before API deployment. Locally:

```bash
docker compose run --rm api alembic current
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic check
```

Back up PostgreSQL before destructive schema changes. Never run concurrent migration writers.

## Scheduling and retraining

Render cron runs the synchronized workflow every three hours. Local Compose uses Celery beat at the
configured `SCHEDULE_MINUTES`. The workflow syncs once, selects supported active markets, and
deduplicates forecast jobs. Keep worker concurrency at one on memory-constrained Render instances
because Prophet and model search are memory-intensive.

For an on-demand run, submit the market forecast endpoint with the admin token and poll its job ID.
Do not retry by repeatedly creating requests: active jobs are deduplicated.

## Model rollback

1. Identify the previous acceptable `CityModel.mlflow_run_id`, data window, metrics, and artifact.
2. Confirm the artifact’s dataset fingerprint and code/model version.
3. Restore model-selection metadata through a reviewed maintenance script or migration; do not
   mutate MLflow run history.
4. Regenerate the affected market prediction and edge snapshot.
5. Verify the dashboard identifies the restored model and expected training window.

The current API does not expose a public rollback endpoint by design.

## Backup, retention, and recovery

- Enable Render PostgreSQL backups according to the service plan and periodically test restoration.
- Back up the MLflow disk or export critical artifacts to durable external storage before disk
  replacement. A database backup alone does not contain model binaries.
- Configuration defines retention targets: predictions/edges 180 days, jobs 30 days, models 365
  days by default. Automated cleanup is not implemented; schedule reviewed maintenance before data
  volume requires it.
- Redis is a queue/result transport, not authoritative storage. After Redis loss, failed/in-flight
  jobs may need to be marked failed and safely requeued.
- After PostgreSQL recovery, run migrations, check `/ready`, verify foreign-key history, then resume
  workers and cron.

## Incident checklist

1. Stop cron or scale the worker to zero if repeated tasks may corrupt or overload data.
2. Preserve API, worker, PostgreSQL, Redis, and MLflow logs.
3. Determine whether the failure is source availability, data quality, model quality, queue,
   database, or artifact storage.
4. Keep stale forecasts visibly stale rather than deleting historical predictions.
5. Restore dependencies, run one supported city forecast, verify probability normalization and
   artifact retrieval, then resume scheduling.
