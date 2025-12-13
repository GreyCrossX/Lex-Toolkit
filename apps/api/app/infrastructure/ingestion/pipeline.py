from pathlib import Path
from typing import Dict, List, Tuple

from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from app.infrastructure.ingestion.pdf_text import extract_plain_text_from_pdf
from app.infrastructure.llm import openai_client as llm


DOC_TYPE_CONFIG: Dict[str, Dict[str, int]] = {
    "statute": {"max_pages": 20, "chunk_chars": 1200, "overlap": 200, "max_chunks": 6},
    "jurisprudence": {
        "max_pages": 14,
        "chunk_chars": 900,
        "overlap": 150,
        "max_chunks": 8,
    },
    "contract": {"max_pages": 10, "chunk_chars": 850, "overlap": 120, "max_chunks": 8},
    "policy": {"max_pages": 12, "chunk_chars": 900, "overlap": 140, "max_chunks": 8},
}

DEFAULT_CONFIG = {"max_pages": 20, "chunk_chars": 1200, "overlap": 200, "max_chunks": 6}


def _chunk_text(text: str, max_chars: int, overlap: int) -> List[str]:
    if max_chars <= overlap:
        max_chars = overlap + 1
    chunks: List[str] = []
    start = 0
    step = max_chars - overlap
    length = len(text)
    while start < length:
        end = min(length, start + max_chars)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


def ingest_pdf(
    pool: ConnectionPool,
    file_path: Path,
    doc_id: str,
    doc_type: str = "statute",
) -> Tuple[str, int]:
    """
    Parse PDF with pdfplumber, chunk, embed, and upsert into legal_chunks.
    We cap pages/chunks to keep ingestion fast inside the worker.

    Returns (doc_id, chunk_count_inserted).
    """
    raw_bytes = file_path.read_bytes()
    config = {**DEFAULT_CONFIG, **DOC_TYPE_CONFIG.get(doc_type, {})}
    preview_text = extract_plain_text_from_pdf(raw_bytes, max_pages=config["max_pages"])
    if not preview_text.strip():
        preview_text = f"Uploaded file {file_path.name}"

    metadata_common = _build_metadata(doc_type, file_path, preview_text, config)

    chunk_payloads: List[Tuple[str, str, dict]] = []
    for idx, chunk in enumerate(
        _chunk_text(preview_text, config["chunk_chars"], config["overlap"])
    ):
        chunk_id = f"{doc_id}:c{idx}"
        metadata = {**metadata_common, "chunk_index": idx}
        chunk_payloads.append((chunk_id, chunk, metadata))
        # Keep it small to avoid long-running ingests in the worker container.
        if config["max_chunks"] and len(chunk_payloads) >= config["max_chunks"]:
            break

    if not chunk_payloads:
        raise ValueError("No se generaron chunks a partir del PDF.")

    embeddings = llm.embed_texts([content for _, content, _ in chunk_payloads])

    with pool.connection() as conn, conn.cursor() as cur:
        for (chunk_id, content, metadata), embedding in zip(chunk_payloads, embeddings):
            cur.execute(
                """
                INSERT INTO legal_chunks (
                    chunk_id,
                    doc_id,
                    section,
                    jurisdiction,
                    tokenizer_model,
                    metadata,
                    content,
                    embedding
                )
                VALUES (%(chunk_id)s, %(doc_id)s, %(section)s, %(jurisdiction)s, %(tokenizer_model)s, %(metadata)s, %(content)s, %(embedding)s)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    content=EXCLUDED.content,
                    metadata=EXCLUDED.metadata,
                    embedding=EXCLUDED.embedding
                """,
                {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "section": None,
                    "jurisdiction": None,
                    "tokenizer_model": None,
                    "metadata": Json(metadata),
                    "content": content,
                    "embedding": embedding,
                },
            )
        conn.commit()

    return doc_id, len(chunk_payloads)


def _build_metadata(
    doc_type: str, file_path: Path, text: str, config: Dict[str, int]
) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = lines[0][:160] if lines else file_path.name
    text_lower = text.lower()

    tags = [doc_type]
    if doc_type == "jurisprudence":
        if "tesis" in text_lower or "jurisprudencia" in text_lower:
            tags.append("precedent")
    if doc_type == "contract":
        if "confidencial" in text_lower or "confidential" in text_lower:
            tags.append("nda")
        if "arrend" in text_lower:
            tags.append("lease")
    if doc_type == "policy":
        if "privacy" in text_lower or "privacidad" in text_lower:
            tags.append("privacy")
        if "seguridad" in text_lower:
            tags.append("security")

    jurisdiction = _guess_jurisdiction(text_lower)

    metadata = {
        "source": file_path.name,
        "ingest": "upload",
        "doc_type": doc_type,
        "title": title,
        "tags": tags,
        "jurisdiction_hint": jurisdiction,
        "chunking": {
            "max_pages": config["max_pages"],
            "chunk_chars": config["chunk_chars"],
            "overlap": config["overlap"],
            "max_chunks": config["max_chunks"],
        },
    }
    return {key: value for key, value in metadata.items() if value is not None}


def _guess_jurisdiction(text_lower: str) -> str | None:
    if "ciudad de méxico" in text_lower or "cdmx" in text_lower:
        return "cdmx"
    if "suprema corte" in text_lower or "poder judicial de la federación" in text_lower:
        return "federal"
    if "méxico" in text_lower:
        return "mx"
    return None
