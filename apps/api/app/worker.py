from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.orm import undefer

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.workspace import Document
from app.services.indexing import index_document


async def index_document_job(ctx, document_id: str):
    async with SessionLocal() as db:
        document = await db.scalar(
            select(Document)
            .options(undefer(Document.source_data))
            .where(Document.id == document_id)
        )
        if not document:
            return "missing"
        await index_document(document, db)
        await db.commit()
        return document.status


class WorkerSettings:
    functions = [index_document_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 8
    job_timeout = 900
