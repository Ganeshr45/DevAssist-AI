import re
import zipfile
from hashlib import sha256
from io import BytesIO

from docx import Document as WordDocument
from fastapi import HTTPException
from pypdf import PdfReader

from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt", ".docx"}


def parse_document(filename: str, raw: bytes) -> tuple[str, int]:
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Supported file types are PDF, Markdown, TXT, and DOCX")
    try:
        if ext == ".pdf":
            reader = PdfReader(BytesIO(raw), strict=True)
            if reader.is_encrypted:
                raise HTTPException(422, "Password-protected PDFs are not supported")
            if len(reader.pages) > settings.max_pdf_pages:
                raise HTTPException(413, f"PDF exceeds the {settings.max_pdf_pages} page limit")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            pages = len(reader.pages)
        elif ext == ".docx":
            with zipfile.ZipFile(BytesIO(raw)) as archive:
                if len(archive.namelist()) > 5000:
                    raise HTTPException(422, "Document archive contains too many entries")
                expanded_size = sum(item.file_size for item in archive.infolist())
                if expanded_size > settings.max_upload_mb * 15 * 1024 * 1024:
                    raise HTTPException(422, "Document expands beyond the allowed size")
            doc = WordDocument(BytesIO(raw))
            text = "\n".join(p.text for p in doc.paragraphs)
            pages = 0
        else:
            text = raw.decode("utf-8-sig")
            pages = 0
    except HTTPException:
        raise
    except (UnicodeDecodeError, zipfile.BadZipFile, ValueError, OSError) as exc:
        raise HTTPException(
            422, "The document could not be parsed; verify that it is valid and unprotected"
        ) from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[\t ]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    if not normalized:
        raise HTTPException(422, "The document contains no extractable text")
    if len(normalized) > settings.max_document_chars:
        raise HTTPException(413, "Extracted text exceeds the indexing limit")
    return normalized, pages


def chunk_text(text: str) -> list[str]:
    size, overlap = settings.chunk_size, settings.chunk_overlap
    if overlap >= size:
        raise ValueError("Chunk overlap must be smaller than chunk size")
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        part = text[start:end]
        if part:
            chunks.append(part)
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def document_checksum(raw: bytes) -> str:
    return sha256(raw).hexdigest()
