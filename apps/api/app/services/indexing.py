from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.workspace import Document, DocumentChunk, Embedding
from app.services.documents import chunk_text, parse_document
from app.services.llm import embed_texts
from app.services.storage import load_document_source


async def index_document(document: Document, db: AsyncSession) -> None:
    try:
        raw = await load_document_source(document.storage_key, document.source_data)
        content, pages = parse_document(document.filename, raw)
        pieces = chunk_text(content)
        vectors = await embed_texts(pieces)
        if len(vectors) != len(pieces) or any(len(vector) != 1536 for vector in vectors):
            raise ValueError("Embedding provider dimension mismatch")
        await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        for index, (piece, vector) in enumerate(zip(pieces, vectors, strict=True)):
            chunk = DocumentChunk(
                document_id=document.id,
                ordinal=index + 1,
                content=piece,
                metadata_json={"page_count": pages},
            )
            db.add(chunk)
            await db.flush()
            db.add(
                Embedding(chunk_id=chunk.id, vector=vector, model=settings.openai_embedding_model)
            )
        document.status = "indexed"
        document.error_message = None
        document.page_count = pages
    except HTTPException as exc:
        document.status = "failed"
        document.error_message = str(exc.detail)[:500]
    except Exception as exc:
        document.status = "failed"
        document.error_message = (
            f"Indexing failed ({type(exc).__name__}). Check provider and document format."
        )
