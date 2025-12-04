from pathlib import Path
from typing import List, Tuple

from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from app.infrastructure.ingestion.pdf_text import extract_plain_text_from_pdf
from app.infrastructure.llm import openai_client as llm


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> List[str]:
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
    max_chunks: int = 6,
    doc_type: str = "statute",
) -> Tuple[str, int]:
    """
    Parse PDF with pdfplumber, chunk, embed, and upsert into legal_chunks.
    We cap pages/chunks to keep ingestion fast inside the worker.

    Returns (doc_id, chunk_count_inserted).
    """
    raw_bytes = file_path.read_bytes()
    preview_text = extract_plain_text_from_pdf(raw_bytes, max_pages=20)
    if not preview_text.strip():
        preview_text = f"Uploaded file {file_path.name}"

    chunk_payloads: List[Tuple[str, str, dict]] = []
    for idx, chunk in enumerate(_chunk_text(preview_text)):
        chunk_id = f"{doc_id}:c{idx}"
        metadata = {
            "source": file_path.name,
            "ingest": "upload",
            "doc_type": doc_type,
        }
        chunk_payloads.append((chunk_id, chunk, metadata))
        # Keep it small to avoid long-running ingests in the worker container.
        if max_chunks and len(chunk_payloads) >= max_chunks:
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
