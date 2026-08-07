"""Initial Temperature Predictor schema.

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

temp_type = sa.Enum("high", name="temptype")
job_status = sa.Enum(
    "queued", "fetching", "training", "evaluating", "complete", "failed",
    name="jobstatus",
)
job_type = sa.Enum("sync", "forecast", "scheduled", name="jobtype")


def upgrade() -> None:
    op.create_table(
        "city",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("icao", sa.String(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("data_source", sa.String(), nullable=False),
        sa.Column("resolution_source", sa.String(), nullable=False),
        sa.Column("resolution_verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("name", "country", name="uq_city_name_country"),
    )
    op.create_index("ix_city_name", "city", ["name"])
    op.create_index("ix_city_icao", "city", ["icao"])

    op.create_table(
        "market",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("city.id"), nullable=False),
        sa.Column("polymarket_event_id", sa.String(), nullable=False),
        sa.Column("polymarket_slug", sa.String(), nullable=False),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("temp_type", temp_type, nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("supported", sa.Boolean(), nullable=False),
        sa.Column("unsupported_reason", sa.String(), nullable=False),
        sa.Column("resolution_source", sa.String(), nullable=False),
        sa.Column("resolution_station", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("temp_type = 'high'", name="ck_market_high_only"),
        sa.UniqueConstraint("polymarket_event_id"),
        sa.UniqueConstraint("polymarket_slug"),
    )
    op.create_index("ix_market_city_id", "market", ["city_id"])
    op.create_index("ix_market_target_date", "market", ["target_date"])

    op.create_table(
        "tempbucket",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("market.id"), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("temp_c", sa.Float()),
        sa.Column("source_unit", sa.String(), nullable=False),
        sa.Column("bucket_width_c", sa.Float(), nullable=False),
        sa.Column("is_or_higher", sa.Boolean(), nullable=False),
        sa.Column("is_or_lower", sa.Boolean(), nullable=False),
        sa.Column("token_id", sa.String(), nullable=False),
        sa.Column("yes_price", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("market_id", "label", name="uq_bucket_market_label"),
    )
    op.create_index("ix_tempbucket_market_id", "tempbucket", ["market_id"])
    op.create_index(
        "uq_bucket_market_token",
        "tempbucket",
        ["market_id", "token_id"],
        unique=True,
        postgresql_where=sa.text("token_id <> ''"),
        sqlite_where=sa.text("token_id <> ''"),
    )

    op.create_table(
        "observation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("city.id"), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("high_c", sa.Float(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.UniqueConstraint(
            "city_id", "observed_on", "source",
            name="uq_observation_city_day_source",
        ),
    )
    op.create_index("ix_observation_city_id", "observation", ["city_id"])
    op.create_index("ix_observation_observed_on", "observation", ["observed_on"])

    op.create_table(
        "forecastjob",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("market.id")),
        sa.Column("job_type", job_type, nullable=False),
        sa.Column("celery_task_id", sa.String(), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("error_message", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime()),
    )
    op.create_index("ix_forecastjob_market_id", "forecastjob", ["market_id"])
    op.create_index("ix_forecastjob_job_type", "forecastjob", ["job_type"])
    op.create_index(
        "uq_active_forecast_job",
        "forecastjob",
        ["market_id"],
        unique=True,
        postgresql_where=sa.text(
            "job_type = 'forecast' AND status IN "
            "('queued', 'fetching', 'training', 'evaluating')"
        ),
        sqlite_where=sa.text(
            "job_type = 'forecast' AND status IN "
            "('queued', 'fetching', 'training', 'evaluating')"
        ),
    )

    op.create_table(
        "citymodel",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("city.id"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("forecastjob.id")),
        sa.Column("temp_type", temp_type, nullable=False),
        sa.Column("model_type", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("artifact_uri", sa.String(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("mae", sa.Float()),
        sa.Column("rmse", sa.Float()),
        sa.Column("bias", sa.Float()),
        sa.Column("data_start", sa.Date(), nullable=False),
        sa.Column("data_end", sa.Date(), nullable=False),
        sa.Column("dataset_fingerprint", sa.String(), nullable=False),
        sa.Column("code_version", sa.String(), nullable=False),
        sa.Column("target_horizon_days", sa.Integer(), nullable=False),
        sa.Column("backtest_folds", sa.Integer(), nullable=False),
        sa.Column("calibration_sample_size", sa.Integer(), nullable=False),
        sa.Column("mlflow_run_id", sa.String(), nullable=False),
        sa.Column("trained_at", sa.DateTime(), nullable=False),
        sa.Column("is_best", sa.Boolean(), nullable=False),
        sa.Column("is_comparable", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_citymodel_city_id", "citymodel", ["city_id"])

    op.create_table(
        "modelprediction",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("market.id"), nullable=False),
        sa.Column("city_model_id", sa.Integer(), sa.ForeignKey("citymodel.id")),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("point_forecast_c", sa.Float(), nullable=False),
        sa.Column("residual_rmse", sa.Float(), nullable=False),
        sa.Column("calibration_method", sa.String(), nullable=False),
        sa.Column("mlflow_run_id", sa.String(), nullable=False),
        sa.Column("bucket_probs", sa.JSON(), nullable=False),
        sa.Column("forecast_dates", sa.JSON(), nullable=False),
        sa.Column("forecast_temps", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_modelprediction_market_id", "modelprediction", ["market_id"])
    op.create_index("ix_modelprediction_target_date", "modelprediction", ["target_date"])

    op.create_table(
        "edgesnapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("market.id"), nullable=False),
        sa.Column("bucket_id", sa.Integer(), sa.ForeignKey("tempbucket.id"), nullable=False),
        sa.Column("model_prob", sa.Float(), nullable=False),
        sa.Column("market_prob", sa.Float(), nullable=False),
        sa.Column("edge", sa.Float(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_edgesnapshot_market_id", "edgesnapshot", ["market_id"])
    op.create_index("ix_edgesnapshot_bucket_id", "edgesnapshot", ["bucket_id"])


def downgrade() -> None:
    op.drop_table("edgesnapshot")
    op.drop_table("modelprediction")
    op.drop_table("citymodel")
    op.drop_table("forecastjob")
    op.drop_table("observation")
    op.drop_table("tempbucket")
    op.drop_table("market")
    op.drop_table("city")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        job_type.drop(bind, checkfirst=True)
        job_status.drop(bind, checkfirst=True)
        temp_type.drop(bind, checkfirst=True)
