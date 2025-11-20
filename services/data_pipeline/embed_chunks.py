#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Sequence


ChunkRecord = Dict[str, object]
EmbeddingBatchFn = Callable[[List[str]], List[List[float]]]


@dataclass
class ChunkFile:
    path: Path
    jurisdiction: str
    doc_id: str


def iter_chunk_files(
    chunks_dir: Path,
    jurisdictions: Optional[Sequence[str]],
    doc_ids: Optional[Sequence[str]],
) -> Iterator[ChunkFile]:
    doc_filter = {doc_id for doc_id in doc_ids} if doc_ids else None
    jur_filter = {j.lower() for j in jurisdictions} if jurisdictions else None

    for path in sorted(chunks_dir.rglob("*_chunks.jsonl")):
        if not path.is_file():
            continue

        rel_parts = path.relative_to(chunks_dir).parts
        jurisdiction = rel_parts[0] if rel_parts else ""
        if jur_filter and jurisdiction.lower() not in jur_filter:
            continue

        doc_id = path.name[: -len("_chunks.jsonl")]
        if doc_filter is not None and doc_id not in doc_filter:
            continue

        yield ChunkFile(path=path, jurisdiction=jurisdiction, doc_id=doc_id)
        if doc_filter is not None:
            doc_filter.discard(doc_id)

    if doc_filter:
        missing = ", ".join(sorted(doc_filter))
        raise FileNotFoundError(f"Chunk files not found for doc_ids: {missing}")


def iter_chunk_records(file_path: Path) -> Iterator[ChunkRecord]:
    with file_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS legal_chunks (
            chunk_id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            article_number TEXT,
            fraction_label TEXT,
            paragraph_index INTEGER,
            chunk_index INTEGER,
            section TEXT,
            content TEXT,
            metadata TEXT,
            embedding TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_legal_chunks_doc
        ON legal_chunks(doc_id)
        """
    )
    conn.commit()


def upsert_chunk(
    conn: sqlite3.Connection,
    record: ChunkRecord,
    embedding: Optional[List[float]],
) -> None:
    metadata = json.dumps(record.get("metadata", {}), ensure_ascii=False)
    embedding_json = (
        json.dumps(embedding, ensure_ascii=False) if embedding is not None else None
    )
    conn.execute(
        """
        INSERT INTO legal_chunks (
            chunk_id,
            doc_id,
            article_number,
            fraction_label,
            paragraph_index,
            chunk_index,
            section,
            content,
            metadata,
            embedding
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(chunk_id) DO UPDATE SET
            doc_id=excluded.doc_id,
            article_number=excluded.article_number,
            fraction_label=excluded.fraction_label,
            paragraph_index=excluded.paragraph_index,
            chunk_index=excluded.chunk_index,
            section=excluded.section,
            content=excluded.content,
            metadata=excluded.metadata,
            embedding=excluded.embedding
        """,
        (
            record["chunk_id"],
            record["doc_id"],
            record.get("article_number"),
            record.get("fraction_label"),
            record.get("paragraph_index"),
            record.get("chunk_index"),
            record.get("section"),
            record.get("content"),
            metadata,
            embedding_json,
        ),
    )


class OpenAIEmbedder:
    def __init__(self, model: str):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "openai package is required for embedding unless --dry-run is used."
            ) from exc

        self._client = OpenAI()
        self._model = model

    def __call__(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(model=self._model, input=texts)
        data = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in data]


class LocalEmbedder:
    def __init__(
        self,
        model_name: str,
        *,
        device: Optional[str] = None,
        prefix: str = "passage: ",
        normalize: bool = True,
    ):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "sentence-transformers is required for local embeddings. "
                "Install it with `pipenv install sentence-transformers`."
            ) from exc

        self._model = SentenceTransformer(model_name, device=device)
        self._prefix = prefix or ""
        self._normalize = normalize

    def __call__(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        prefixed = [f"{self._prefix}{text}" for text in texts]
        embeddings = self._model.encode(
            prefixed,
            convert_to_numpy=True,
            normalize_embeddings=self._normalize,
        )
        return embeddings.tolist()


def process_batches(
    conn: sqlite3.Connection,
    records: List[ChunkRecord],
    embed_fn: Optional[EmbeddingBatchFn],
) -> int:
    if not records:
        return 0

    texts = [str(rec.get("content") or "") for rec in records]
    if embed_fn is None:
        embeddings: List[Optional[List[float]]] = [None] * len(records)
    else:
        embeddings = embed_fn(texts)  # type: ignore[assignment]
        if len(embeddings) != len(records):
            raise RuntimeError("Embedding provider returned mismatched batch size.")

    for record, embedding in zip(records, embeddings):
        upsert_chunk(conn, record, embedding)
    conn.commit()
    return len(records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Embed chunk JSONL files and store them in SQLite."
    )
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        default=Path("data/chunks"),
        help="Directory containing chunk JSONL files.",
    )
    parser.add_argument(
        "--output-db",
        type=Path,
        default=Path("data/legal_chunks.db"),
        help="SQLite database path to store embeddings.",
    )
    parser.add_argument(
        "--backend",
        choices=("local", "openai"),
        default="local",
        help="Embedding backend to use (default: local).",
    )
    parser.add_argument(
        "--embedding-model",
        default="text-embedding-3-large",
        help="Embedding model identifier when --backend=openai.",
    )
    parser.add_argument(
        "--local-model",
        default="intfloat/multilingual-e5-base",
        help="Sentence-Transformers model name when --backend=local.",
    )
    parser.add_argument(
        "--local-device",
        default=None,
        help="Torch device for local embeddings (e.g., cuda, cuda:0, cpu).",
    )
    parser.add_argument(
        "--local-prefix",
        default="passage: ",
        help="Text prefix applied before encoding chunks (e5 uses 'passage: ').",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Number of chunks per embedding batch.",
    )
    parser.add_argument(
        "--jurisdiction",
        action="append",
        help="Optional jurisdiction filter matching chunk subdirectories.",
    )
    parser.add_argument(
        "--doc-id",
        action="append",
        help="Optional doc id filter (filename prefix before _chunks.jsonl).",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=None,
        help="Optional limit on number of chunks to process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip embedding generation and only load chunk metadata.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    chunks_dir: Path = args.chunks_dir
    if not chunks_dir.exists():
        raise FileNotFoundError(f"Chunks directory not found: {chunks_dir}")

    args.output_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.output_db)
    ensure_tables(conn)

    embed_fn: Optional[EmbeddingBatchFn]
    if args.dry_run:
        embed_fn = None
    else:
        if args.backend == "openai":
            embed_fn = OpenAIEmbedder(args.embedding_model)
        else:
            embed_fn = LocalEmbedder(
                args.local_model,
                device=args.local_device,
                prefix=args.local_prefix,
            )

    processed = 0
    batch: List[ChunkRecord] = []

    for chunk_file in iter_chunk_files(
        chunks_dir, jurisdictions=args.jurisdiction, doc_ids=args.doc_id
    ):
        for record in iter_chunk_records(chunk_file.path):
            if args.max_chunks is not None and processed >= args.max_chunks:
                break

            batch.append(record)
            processed += 1
            if len(batch) >= args.batch_size:
                process_batches(conn, batch, embed_fn)
                batch = []

        if args.max_chunks is not None and processed >= args.max_chunks:
            break

    if batch:
        process_batches(conn, batch, embed_fn)

    conn.close()
    print(f"[DONE] Stored {processed} chunk(s) in {args.output_db}")


if __name__ == "__main__":
    main()
