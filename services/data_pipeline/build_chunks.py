#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import tiktoken

from services.data_pipeline.legal_chunker import (
    ArticleUnit,
    build_chunks_from_units,
    split_article_into_units,
)


@dataclass
class SimpleLegalArt:
    number: str
    heading: Optional[str]
    text: str


@dataclass
class SimpleLegalDoc:
    id: str
    title: str
    type: str
    source: str
    jurisdiction: str
    source_url: str
    publication_date: Optional[str]
    status: Optional[str]
    metadata: Dict[str, str]


@dataclass
class SimpleLegalTransient:
    label: str
    text: str


def normalize_metadata(raw: Optional[Dict]) -> Dict[str, str]:
    if not raw:
        return {}
    normalized: Dict[str, str] = {}
    for key, value in raw.items():
        if value is None:
            normalized[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            normalized[key] = str(value)
        else:
            normalized[key] = json.dumps(value, ensure_ascii=False)
    return normalized


def load_doc(
    path: Path,
) -> tuple[SimpleLegalDoc, List[SimpleLegalArt], List[SimpleLegalTransient]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = normalize_metadata(data.get("metadata"))
    doc = SimpleLegalDoc(
        id=str(data["id"]),
        title=data.get("title", ""),
        type=data.get("type", ""),
        source=data.get("source", ""),
        jurisdiction=data.get("jurisdiction", ""),
        source_url=data.get("source_url", ""),
        publication_date=data.get("publication_date"),
        status=data.get("status"),
        metadata=metadata,
    )

    articles_data = data.get("articles") or []
    articles: List[SimpleLegalArt] = []
    for art in articles_data:
        text = art.get("text") or ""
        articles.append(
            SimpleLegalArt(
                number=str(art.get("number", "")),
                heading=art.get("heading"),
                text=text,
            )
        )
    transitory_data = data.get("transitory") or []
    transitory_items: List[SimpleLegalTransient] = []
    for idx, item in enumerate(transitory_data, start=1):
        label = (item.get("label") or "").strip() or f"TRANSITORIO_{idx}"
        transitory_items.append(
            SimpleLegalTransient(
                label=label,
                text=item.get("text") or "",
            )
        )
    return doc, articles, transitory_items


def transitory_to_articles(items: List[SimpleLegalTransient]) -> List[SimpleLegalArt]:
    pseudo_articles: List[SimpleLegalArt] = []
    for idx, trans in enumerate(items, start=1):
        label = trans.label.strip() or f"TRANSITORIO_{idx}"
        pseudo_articles.append(
            SimpleLegalArt(
                number=label,
                heading=None,
                text=trans.text or "",
            )
        )
    return pseudo_articles


def iter_doc_paths(
    normalized_root: Path,
    jurisdictions: Optional[Sequence[str]] = None,
) -> Iterable[Path]:
    jurisdiction_set = {j.lower() for j in jurisdictions} if jurisdictions else None

    for path in sorted(normalized_root.rglob("*.json")):
        # Skip directories like .jsonl etc.
        if not path.is_file():
            continue
        if jurisdiction_set:
            parts = path.parts
            if not any(part.lower() in jurisdiction_set for part in parts):
                continue
        yield path


def write_chunks(
    chunks_dir: Path,
    jurisdiction: str,
    doc_id: str,
    chunk_payloads: Iterable[Dict],
) -> Path:
    out_dir = chunks_dir / jurisdiction.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{doc_id}_chunks.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for payload in chunk_payloads:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return out_path


def build_chunk_payloads(
    doc: SimpleLegalDoc,
    items: List[SimpleLegalArt],
    *,
    encoding: tiktoken.Encoding,
    max_tokens: int,
    overlap_tokens: int,
    section: str,
) -> List[Dict]:
    if not items:
        return []

    article_units: List[ArticleUnit] = []
    for article in items:
        units = split_article_into_units(article)
        article_units.extend(units)

    if not article_units:
        return []

    legal_chunks = build_chunks_from_units(
        doc,
        article_units,
        encoding=encoding,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
        section=section,  # type: ignore[arg-type]
    )

    payloads: List[Dict] = []
    for chunk in legal_chunks:
        payloads.append(
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "article_number": chunk.article_number,
                "fraction_label": chunk.fraction_label,
                "paragraph_index": chunk.paragraph_index,
                "chunk_index": chunk.chunk_index,
                "section": chunk.section,
                "content": chunk.content,
                "metadata": chunk.metadata,
            }
        )
    return payloads


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split normalized legal documents into citation-aligned RAG chunks."
    )
    parser.add_argument(
        "--normalized-root",
        type=Path,
        default=Path("data/normalized"),
        help="Directory containing normalized JSON documents.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/chunks"),
        help="Where to write chunk JSONL files.",
    )
    parser.add_argument(
        "--jurisdiction",
        action="append",
        help="Filter input by jurisdiction subdirectory (e.g., cdmx, dof).",
    )
    parser.add_argument(
        "--doc-id",
        action="append",
        help="Process only the given document id(s).",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=None,
        help="Optional cap on number of documents to process.",
    )
    parser.add_argument(
        "--tokenizer-model",
        default="gpt-4o-mini",
        help="Model name used to pick the tokenizer for chunk sizing.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=320,
        help="Maximum tokens per chunk (based on tokenizer-model).",
    )
    parser.add_argument(
        "--overlap-tokens",
        type=int,
        default=60,
        help="Token overlap between consecutive chunks.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    normalized_root: Path = args.normalized_root
    output_dir: Path = args.output_dir

    if not normalized_root.exists():
        raise FileNotFoundError(f"Normalized root not found: {normalized_root}")

    try:
        encoding = tiktoken.encoding_for_model(args.tokenizer_model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")

    processed_docs = 0
    total_chunks = 0
    doc_id_filter = set(args.doc_id or [])

    for doc_path in iter_doc_paths(
        normalized_root,
        jurisdictions=args.jurisdiction,
    ):
        if args.max_docs is not None and processed_docs >= args.max_docs:
            break

        try:
            doc, articles, transitory_items = load_doc(doc_path)
        except Exception as exc:  # pragma: no cover - debugging aid
            raise RuntimeError(f"Failed to load {doc_path}") from exc

        if doc_id_filter and doc.id not in doc_id_filter:
            continue

        payloads_articles = build_chunk_payloads(
            doc,
            articles,
            encoding=encoding,
            max_tokens=args.max_tokens,
            overlap_tokens=args.overlap_tokens,
            section="article",
        )
        payloads_transitory = build_chunk_payloads(
            doc,
            transitory_to_articles(transitory_items),
            encoding=encoding,
            max_tokens=args.max_tokens,
            overlap_tokens=args.overlap_tokens,
            section="transitory",
        )
        payloads = payloads_articles + payloads_transitory

        if not payloads:
            print(f"[SKIP] {doc.id}: no article/transitory chunks")
            continue

        write_chunks(
            output_dir,
            doc.jurisdiction or "unknown",
            doc.id,
            payloads,
        )

        processed_docs += 1
        total_chunks += len(payloads)
        doc_id_filter.discard(doc.id)
        print(
            f"[OK] {doc.id}: {len(payloads)} chunks (jurisdiction={doc.jurisdiction})"
        )

    if doc_id_filter:
        missing = ", ".join(sorted(doc_id_filter))
        print(f"[WARN] Requested doc ids not found: {missing}")

    print(
        f"[DONE] Processed {processed_docs} document(s), "
        f"generated {total_chunks} chunks."
    )


if __name__ == "__main__":
    main()
