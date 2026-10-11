"""Object storage (ADR-006): one interface, a local adapter for development, S3 for servers."""

from functools import lru_cache

from app.config import Settings, get_settings
from app.object_store.base import (
    WRITE_ONCE,
    Bucket,
    IntegrityError,
    ObjectExists,
    ObjectNotFound,
    ObjectStore,
    ObjectTooLarge,
    StorageError,
    StoredObject,
    new_key,
)
from app.object_store.local import LocalObjectStore
from app.object_store.s3 import S3ObjectStore

__all__ = [
    "WRITE_ONCE",
    "Bucket",
    "IntegrityError",
    "LocalObjectStore",
    "ObjectExists",
    "ObjectNotFound",
    "ObjectStore",
    "ObjectTooLarge",
    "S3ObjectStore",
    "StorageError",
    "StoredObject",
    "build_object_store",
    "get_object_store",
    "new_key",
]


def bucket_names(settings: Settings) -> dict[Bucket, str]:
    return {
        Bucket.QUARANTINE: settings.bucket_quarantine,
        Bucket.ORIGINALS: settings.bucket_originals,
        Bucket.DERIVED: settings.bucket_derived,
        Bucket.CONSENT_EVIDENCE: settings.bucket_consent_evidence,
        Bucket.EXPORTS: settings.bucket_exports,
    }


def build_object_store(settings: Settings) -> ObjectStore:
    names = bucket_names(settings)
    if settings.storage_backend == "local":
        return LocalObjectStore(
            settings.local_storage_dir,
            names,
            base_url=settings.base_url,
            secret=settings.secret_key.get_secret_value(),
        )
    return S3ObjectStore.from_settings(
        names,
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=(
            settings.s3_access_key_id.get_secret_value() if settings.s3_access_key_id else None
        ),
        aws_secret_access_key=(
            settings.s3_secret_access_key.get_secret_value()
            if settings.s3_secret_access_key
            else None
        ),
        force_path_style=settings.s3_force_path_style,
    )


@lru_cache
def get_object_store() -> ObjectStore:
    return build_object_store(get_settings())
