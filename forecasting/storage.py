"""Model serialization and storage (local or S3-compatible)."""

import os
import pickle
from pathlib import Path

import boto3
from django.conf import settings


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def save_model(model, product_id: int, model_type: str) -> str:
    """Serialize and store a fitted model. Returns storage key/path."""
    key = f"product_{product_id}/{model_type}.pkl"

    if settings.MODEL_STORAGE_BACKEND == "s3":
        client = _get_s3_client()
        data = pickle.dumps(model)
        client.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key,
            Body=data,
        )
        return key

    storage_dir = Path(settings.MODEL_STORAGE_PATH) / f"product_{product_id}"
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / f"{model_type}.pkl"
    with open(file_path, "wb") as f:
        pickle.dump(model, f)
    return str(file_path)


def load_model(file_path: str):
    """Load a serialized model from storage."""
    if settings.MODEL_STORAGE_BACKEND == "s3":
        client = _get_s3_client()
        response = client.get_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=file_path,
        )
        return pickle.loads(response["Body"].read())

    with open(file_path, "rb") as f:
        return pickle.load(f)


def save_prophet_model(model, product_id: int) -> str:
    """Prophet uses JSON serialization."""
    import json

    from prophet.serialize import model_to_json

    key = f"product_{product_id}/prophet.json"
    data = model_to_json(model)

    if settings.MODEL_STORAGE_BACKEND == "s3":
        client = _get_s3_client()
        client.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key,
            Body=data,
        )
        return key

    storage_dir = Path(settings.MODEL_STORAGE_PATH) / f"product_{product_id}"
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / "prophet.json"
    with open(file_path, "w") as f:
        f.write(data)
    return str(file_path)


def load_prophet_model(file_path: str):
    """Load a Prophet model from JSON."""
    from prophet import Prophet
    from prophet.serialize import model_from_json

    if settings.MODEL_STORAGE_BACKEND == "s3":
        client = _get_s3_client()
        response = client.get_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=file_path,
        )
        data = response["Body"].read().decode("utf-8")
        return model_from_json(data)

    with open(file_path) as f:
        return model_from_json(f.read())
