import asyncio
import logging
from functools import lru_cache
from uuid import UUID

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client():
    return boto3.client(
        "s3",
        region_name=settings.storage_region,
        endpoint_url=settings.storage_endpoint_url or None,
    )


async def store_document(
    user_id: UUID, document_id: UUID, content: bytes
) -> tuple[str | None, bytes | None]:
    if not settings.storage_bucket:
        return None, content
    key = f"private/{user_id}/{document_id}/source"
    try:
        await asyncio.to_thread(
            _client().put_object,
            Bucket=settings.storage_bucket,
            Key=key,
            Body=content,
            ServerSideEncryption="AES256",
            ContentType="application/octet-stream",
        )
    except (BotoCoreError, ClientError):
        logger.exception("document_object_store_write_failed")
        raise RuntimeError("Private document storage is unavailable") from None
    return key, None


async def load_document_source(storage_key: str | None, inline_data: bytes | None) -> bytes:
    if not storage_key:
        if inline_data is None:
            raise RuntimeError("Document source is unavailable")
        return inline_data
    try:
        response = await asyncio.to_thread(
            _client().get_object, Bucket=settings.storage_bucket, Key=storage_key
        )
        return await asyncio.to_thread(response["Body"].read)
    except (BotoCoreError, ClientError, KeyError):
        logger.exception("document_object_store_read_failed")
        raise RuntimeError("Private document storage is unavailable") from None


async def delete_document_source(storage_key: str | None) -> None:
    if not storage_key or not settings.storage_bucket:
        return
    try:
        await asyncio.to_thread(
            _client().delete_object, Bucket=settings.storage_bucket, Key=storage_key
        )
    except (BotoCoreError, ClientError):
        logger.exception("document_object_store_delete_failed")
