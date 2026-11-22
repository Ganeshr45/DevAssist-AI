import mimetypes
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.config import settings
from app.core.rate_limit import enforce_limit
from app.db.session import get_db
from app.models.telemetry import AuditLog
from app.models.user import User
from app.models.workspace import Document
from app.schemas.workspace import DocumentResponse, SearchRequest
from app.services.documents import ALLOWED_EXTENSIONS, document_checksum
from app.services.queue import enqueue_document_index
from app.services.storage import delete_document_source, store_document
from app.tools.registry import search_documents

router = APIRouter(prefix="/documents", tags=["knowledge base"])


@router.get("", response_model=list[DocumentResponse])
async def list_documents(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return list(
        await db.scalars(
            select(Document)
            .where(Document.user_id == user.id)
            .order_by(Document.created_at.desc())
            .limit(200)
        )
    )


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await enforce_limit(f"upload:{user.id}", settings.uploads_per_hour, 3600)
    document_count = await db.scalar(
        select(func.count(Document.id)).where(Document.user_id == user.id)
    )
    if document_count >= 100:
        raise HTTPException(413, "A user can store at most 100 documents")
    filename = (file.filename or "").replace("\\", "/").split("/")[-1].strip()
    if not filename or len(filename) > 255:
        raise HTTPException(422, "Provide a valid filename")
    extension = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Supported file types are PDF, Markdown, TXT, and DOCX")
    raw = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds the {settings.max_upload_mb} MB upload limit")
    if not raw:
        raise HTTPException(422, "The uploaded file is empty")
    checksum = document_checksum(raw)
    duplicate = await db.scalar(
        select(Document.id).where(Document.user_id == user.id, Document.checksum == checksum)
    )
    if duplicate:
        raise HTTPException(409, "This document has already been uploaded")
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    document_id = uuid4()
    try:
        storage_key, inline_data = await store_document(user.id, document_id, raw)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from None
    document = Document(
        id=document_id,
        user_id=user.id,
        filename=filename,
        content_type=content_type,
        checksum=checksum,
        status="processing",
        source_data=inline_data,
        storage_key=storage_key,
    )
    db.add(document)
    db.add(
        AuditLog(
            actor_user_id=user.id,
            event_name="document.uploaded",
            safe_metadata={"document_id": str(document_id)},
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        await delete_document_source(storage_key)
        raise HTTPException(409, "This document has already been uploaded") from None
    try:
        await enqueue_document_index(str(document.id))
    except Exception:
        document.status = "failed"
        document.error_message = "Indexing queue is unavailable; retry indexing later."
        await db.commit()
    await db.refresh(document)
    return document


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if not document:
        raise HTTPException(404, "Document not found")
    return document


@router.post("/{document_id}/reindex", response_model=DocumentResponse)
async def reindex_document(
    document_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if not document:
        raise HTTPException(404, "Document not found")
    document.status = "processing"
    await db.commit()
    try:
        await enqueue_document_index(str(document.id))
    except Exception:
        document.status = "failed"
        document.error_message = "Indexing queue is unavailable; retry indexing later."
        await db.commit()
    await db.refresh(document)
    return document


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if not document:
        raise HTTPException(404, "Document not found")
    storage_key = document.storage_key
    db.add(
        AuditLog(
            actor_user_id=user.id,
            event_name="document.deleted",
            safe_metadata={"document_id": str(document_id)},
        )
    )
    await db.delete(document)
    await db.commit()
    await delete_document_source(storage_key)


@router.post("/search")
async def search_knowledge(
    body: SearchRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    try:
        return {"results": await search_documents(db, user.id, body.query)}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Knowledge search is temporarily unavailable") from None
