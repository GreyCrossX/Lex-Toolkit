from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Literal, Optional, Protocol

import tiktoken


class LegalArtLike(Protocol):
    number: str
    heading: Optional[str]
    text: str


class LegalDocLike(Protocol):
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
class ArticleUnit:
    kind: Literal["lead_paragraph", "fraction_paragraph"]
    article_number: str
    fraction_label: Optional[str]
    paragraph_index: int
    text: str


@dataclass
class LegalChunk:
    chunk_id: str
    doc_id: str
    article_number: str
    fraction_label: Optional[str]
    paragraph_index: int
    chunk_index: int
    section: Literal["article", "transitory"]
    content: str
    metadata: Dict[str, str]


_ID_SAFE_RE = re.compile(r"[^0-9A-Za-z]+")


def _safe_id_component(value: str) -> str:
    slug = _ID_SAFE_RE.sub("-", value or "").strip("-")
    return slug or "na"


FRACTION_START_RE = re.compile(
    r"""
    ^\s*
    (?:fracci[oó]n\s+|fraccion\s+)?
    ([IVXLCDM]+)            # capture the roman numeral
    \s*
    [\.\)\-]*               # allow punctuation like ".", ")", "-".
    \s+
    (?=\S)                  # require content afterwards
    """,
    re.IGNORECASE | re.VERBOSE,
)


def normalize_article_lines(text: str) -> List[str]:
    raw_lines = text.splitlines()
    normalized_lines: List[str] = []
    prev_blank = False

    for ln in raw_lines:
        if ln.strip() == "":
            if not prev_blank:
                normalized_lines.append("")
                prev_blank = True
            continue

        normalized_lines.append(ln.strip())
        prev_blank = False

    return normalized_lines


def split_article_into_units(art: LegalArtLike) -> List[ArticleUnit]:
    lines = normalize_article_lines(art.text)
    units: List[ArticleUnit] = []
    current_fraction: Optional[str] = None
    current_para_lines: List[str] = []
    paragraph_index = 0

    def flush_para() -> None:
        nonlocal current_para_lines, paragraph_index
        if not current_para_lines:
            return

        paragraph_index += 1
        text = " ".join(current_para_lines).strip()
        if not text:
            current_para_lines = []
            return

        kind: Literal["lead_paragraph", "fraction_paragraph"]
        if current_fraction is None:
            kind = "lead_paragraph"
        else:
            kind = "fraction_paragraph"

        units.append(
            ArticleUnit(
                kind=kind,
                article_number=art.number,
                fraction_label=current_fraction,
                paragraph_index=paragraph_index,
                text=text,
            )
        )

        current_para_lines = []

    for ln in lines:
        if ln == "":
            flush_para()
            continue

        match = FRACTION_START_RE.match(ln)
        if match:
            flush_para()
            current_fraction = match.group(1).upper()
            paragraph_index = 0

            remainder = ln[match.end() :].strip()
            if remainder:
                current_para_lines.append(remainder)
            continue

        current_para_lines.append(ln)

    flush_para()
    return units


def chunk_text(
    text: str,
    *,
    max_chars: int = 1200,
    overlap_chars: int = 200,
) -> List[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be between 0 and max_chars")

    if len(cleaned) <= max_chars:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + max_chars, len(cleaned))
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(cleaned):
            break

        start = end - overlap_chars

    return chunks


def chunk_text_by_tokens(
    text: str,
    encoding: tiktoken.Encoding,
    *,
    max_tokens: int = 320,
    overlap_tokens: int = 60,
) -> List[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be between 0 and max_tokens")

    tokens = encoding.encode_ordinary(cleaned)
    if len(tokens) <= max_tokens:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    step = max_tokens - overlap_tokens
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        decoded = encoding.decode(chunk_tokens)
        if decoded:
            chunks.append(decoded.strip())

        if end >= len(tokens):
            break
        start += step

    return chunks


def build_chunks_from_units(
    doc: LegalDocLike,
    units: Iterable[ArticleUnit],
    *,
    encoding: Optional[tiktoken.Encoding] = None,
    max_tokens: int = 320,
    overlap_tokens: int = 60,
    section: Literal["article", "transitory"] = "article",
) -> List[LegalChunk]:
    """
    Build overlapping chunks based on token lengths for the chosen encoding.
    """
    chunks: List[LegalChunk] = []
    enc = encoding or tiktoken.get_encoding("cl100k_base")
    seen_ids: Dict[str, int] = {}
    doc_meta = {
        "title": doc.title,
        "type": doc.type,
        "source": doc.source,
        "jurisdiction": doc.jurisdiction,
        "source_url": doc.source_url,
        "publication_date": doc.publication_date or "",
        "status": doc.status or "",
    }
    if getattr(doc, "metadata", None):
        doc_meta.update(doc.metadata)

    for unit in units:
        chunk_segments = chunk_text_by_tokens(
            unit.text,
            enc,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        )
        if not chunk_segments:
            continue

        for idx, content in enumerate(chunk_segments):
            article_part = _safe_id_component(unit.article_number)
            if unit.fraction_label:
                fraction_part = f"frac{_safe_id_component(unit.fraction_label)}"
            else:
                fraction_part = "fraclead"
            base_chunk_id = (
                f"{doc.id}:{section}:art{article_part}:"
                f"{fraction_part}:p{unit.paragraph_index}:c{idx}"
            )
            dup_count = seen_ids.get(base_chunk_id, 0)
            seen_ids[base_chunk_id] = dup_count + 1
            chunk_id = base_chunk_id if dup_count == 0 else f"{base_chunk_id}:v{dup_count}"
            chunks.append(
                LegalChunk(
                    chunk_id=chunk_id,
                    doc_id=doc.id,
                    article_number=unit.article_number,
                    fraction_label=unit.fraction_label,
                    paragraph_index=unit.paragraph_index,
                    chunk_index=idx,
                    section=section,
                    content=content,
                    metadata=doc_meta.copy(),
                )
            )

    return chunks


__all__ = [
    "ArticleUnit",
    "LegalChunk",
    "normalize_article_lines",
    "split_article_into_units",
    "chunk_text",
    "chunk_text_by_tokens",
    "build_chunks_from_units",
]
