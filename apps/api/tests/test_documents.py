import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services.documents import chunk_text, document_checksum, parse_document


def test_text_document_normalizes_and_extracts():
    text, pages = parse_document("notes.txt", b"Hello\r\n\r\n\r\nWorld  \t!")
    assert text == "Hello\n\nWorld !"
    assert pages == 0


def test_markdown_text_is_preserved():
    text, _ = parse_document("guide.md", b"# Setup\n\nRun `pip install`.")
    assert text.startswith("# Setup")
    assert "pip install" in text


def test_unsupported_extension_is_rejected():
    with pytest.raises(HTTPException) as error:
        parse_document("program.py", b"print('x')")
    assert error.value.status_code == 415


def test_chunking_respects_configured_overlap_and_keeps_all_text():
    text = ("alpha beta gamma delta " * 200).strip()
    parts = chunk_text(text)
    assert len(parts) > 1
    assert all(part for part in parts)
    assert parts[0][:40] == text[:40]
    assert parts[-1][-40:] == text[-40:]
    assert all(
        parts[i][-settings.chunk_overlap :] == parts[i + 1][: settings.chunk_overlap]
        for i in range(len(parts) - 1)
    )


def test_document_checksum_is_stable_and_content_sensitive():
    assert document_checksum(b"a") == document_checksum(b"a")
    assert document_checksum(b"a") != document_checksum(b"b")
