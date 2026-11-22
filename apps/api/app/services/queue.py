from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings


async def enqueue_document_index(document_id: str) -> None:
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await pool.enqueue_job("index_document_job", document_id)
    finally:
        await pool.close()
