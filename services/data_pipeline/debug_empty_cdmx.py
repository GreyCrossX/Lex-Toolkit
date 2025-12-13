#!/usr/bin/env python
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from io import BytesIO
from itertools import pairwise
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

import requests
import pdfplumber

from services.data_pipeline.paths import (
    DEFAULT_CDMX_LAW_SOURCE,
    DEFAULT_MISSING_CDMX,
)

# -----------------
# Config
# -----------------

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

SOFT_HYPHEN = "\u00ad"
PARAGRAPH_GAP_MIN = 8.0

# Transitorios patterns (same as scraper)
TRANSITORIOS_ROOT_PATTERN = re.compile(
    r"(?mi)^\s*art[ií]culos\s+transitorios\s*[:\-.]?\s*$"
)
TRANSITORIOS_ALT_PATTERN = re.compile(r"(?mi)^\s*transitorios\s*[:\-.]?\s*$")

TRANSITORY_ITEM_PATTERN = re.compile(
    r"(?mi)^\s*(?:art[ií]culo\s+|transitorio\s+)?"
    r"(primero|primera|segundo|segunda|tercero|tercera|cuarto|cuarta|quinto|quinta|"
    r"sexto|sexta|s[eé]ptimo|s[eé]ptima|octavo|octava|noveno|novena|"
    r"d[eé]cimo|d[eé]cima|\d+o?|\d+º)"
    r"[^\n]*"
)

ARTICLE_INLINE_PATTERN = re.compile(
    r"(?is)^\s*(art[ií]culo\s+\d+(?:o|º)?[^\w]*)\s*(.*)$"
)


@dataclass
class SourceEntry:
    id: str
    title: str
    url: str
    type: str
    source: str
    jurisdiction: str
    publication_date: Optional[str]
    status: Optional[str]


# -----------------
# Core PDF text extraction (same as scraper)
# -----------------


def _normalize_word_text(text: str) -> str:
    text = text.replace(SOFT_HYPHEN, "").strip()
    return re.sub(r"\s+", " ", text)


def _finalize_line(words: List[Dict[str, float | str]]) -> Dict[str, float | str]:
    words_sorted = sorted(words, key=lambda w: float(w["x0"]))
    parts: List[str] = []
    for w in words_sorted:
        token = _normalize_word_text(str(w.get("text", "")))
        if not token:
            continue
        parts.append(token)
    if not parts:
        text = ""
    else:
        text = " ".join(parts)
        text = re.sub(r"\s+([,.;:!?%])", r"\1", text)
        text = re.sub(r"([(\[¿¡])\s+", r"\1", text)
    return {
        "text": text.strip(),
        "top": min(float(w["top"]) for w in words_sorted),
        "bottom": max(float(w["bottom"]) for w in words_sorted),
    }


def _group_words_into_lines(
    words: List[Dict[str, float | str]], *, y_tolerance: float = 2.5
) -> List[Dict[str, float | str]]:
    if not words:
        return []

    grouped: List[Dict[str, float | str]] = []
    current: List[Dict[str, float | str]] = []
    current_top: Optional[float] = None

    for word in sorted(words, key=lambda w: (float(w["top"]), float(w["x0"]))):
        top = float(word["top"])
        if current_top is None or abs(top - current_top) <= y_tolerance:
            current.append(word)
            if current_top is None:
                current_top = top
            continue

        grouped.append(_finalize_line(current))
        current = [word]
        current_top = top

    if current:
        grouped.append(_finalize_line(current))

    return [line for line in grouped if line["text"]]


def _lines_from_words(words: List[Dict[str, float | str]]) -> List[str]:
    line_blocks = _group_words_into_lines(words)
    if not line_blocks:
        return []

    heights = [float(line["bottom"]) - float(line["top"]) for line in line_blocks]
    gap_threshold = PARAGRAPH_GAP_MIN
    if heights:
        gap_threshold = max(gap_threshold, median(heights) * 1.35)

    lines: List[str] = []
    prev_bottom: Optional[float] = None
    for line in line_blocks:
        top = float(line["top"])
        bottom = float(line["bottom"])
        if prev_bottom is not None and top - prev_bottom > gap_threshold:
            lines.append("")
        lines.append(str(line["text"]))
        prev_bottom = bottom
    return lines


def _detect_column_boundary(
    words: List[Dict[str, float | str]], page_width: float
) -> Optional[float]:
    if not words:
        return None

    xs = sorted({float(w["x0"]) for w in words})
    if len(xs) < 2:
        return None

    best_gap = 0.0
    boundary: Optional[float] = None
    for left, right in pairwise(xs):
        gap = right - left
        if gap > best_gap:
            best_gap = gap
            boundary = left + gap / 2.0

    if boundary is None:
        return None

    min_gap = max(page_width * 0.12, 40.0)
    if best_gap < min_gap:
        return None

    left_count = sum(1 for w in words if float(w["x1"]) <= boundary)
    total = len(words)
    left_ratio = left_count / total if total else 0
    if left_ratio < 0.25 or left_ratio > 0.75:
        return None

    if not (page_width * 0.2 < boundary < page_width * 0.8):
        return None

    return boundary


def _page_to_text(page: pdfplumber.page.Page) -> str:
    words = page.extract_words(
        x_tolerance=1.0,
        y_tolerance=3.0,
        keep_blank_chars=False,
        use_text_flow=True,
    )
    if not words:
        extracted = page.extract_text(layout=True) or ""
        return "\n".join(ln.strip() for ln in extracted.splitlines() if ln.strip())

    boundary = _detect_column_boundary(words, page.width)
    columns: Dict[int, List[Dict[str, float | str]]] = {0: words}
    if boundary is not None:
        columns = {0: [], 1: []}
        for word in words:
            center = (float(word["x0"]) + float(word["x1"])) / 2.0
            col_idx = 0 if center < boundary else 1
            columns[col_idx].append(word)

    column_lines: List[str] = []
    for idx in sorted(columns.keys()):
        lines = _lines_from_words(columns[idx])
        if not lines:
            continue
        if column_lines:
            column_lines.append("")
        column_lines.extend(lines)

    return "\n".join(line for line in column_lines if line is not None).strip()


def extract_plain_text_from_pdf(data: bytes) -> str:
    with pdfplumber.open(BytesIO(data)) as pdf:
        page_texts = [
            page_text for page in pdf.pages if (page_text := _page_to_text(page))
        ]
    return "\n".join(page_texts).strip()


# -----------------
# Article / transitory detection (same logic as scraper)
# -----------------


def find_article_positions_sequential(
    plain_text: str,
    max_articles: int = 10000,
) -> List[Tuple[int, int]]:
    positions: List[Tuple[int, int]] = []
    start_pos = 0
    i = 1

    while i <= max_articles:
        pattern = re.compile(rf"(?mi)^\s*art[ií]culo\s+{i}(?:o|º)?\b")
        m = pattern.search(plain_text, start_pos)
        if not m:
            break
        positions.append((i, m.start()))
        start_pos = m.end()
        i += 1

    return positions


def find_transitorios_heading(plain_text: str, search_from: int = 0) -> Optional[int]:
    m = TRANSITORIOS_ROOT_PATTERN.search(plain_text, search_from)
    if m:
        return m.start()
    m = TRANSITORIOS_ALT_PATTERN.search(plain_text, search_from)
    if m:
        return m.start()
    return None


def split_articles_and_tail(
    plain_text: str,
) -> Tuple[List[Dict[str, Any]], str, str]:
    positions = find_article_positions_sequential(plain_text)
    if not positions:
        return [], plain_text.strip(), ""

    first_start = positions[0][1]
    preamble = plain_text[:first_start].strip()

    spans: List[Tuple[int, int, int]] = []
    for idx, (num, start) in enumerate(positions):
        end = positions[idx + 1][1] if idx + 1 < len(positions) else len(plain_text)
        spans.append((num, start, end))

    _, last_article_start, last_end = spans[-1]

    search_start = max(0, last_article_start - 100)
    trans_root_start = find_transitorios_heading(plain_text, search_start)

    articles: List[Dict[str, Any]] = []

    for num, start, end in spans:
        if trans_root_start is not None and start < trans_root_start < end:
            end = trans_root_start

        chunk = plain_text[start:end].strip()
        body_text = chunk

        m_article = ARTICLE_INLINE_PATTERN.match(chunk)
        if m_article:
            # header_line = (m_article.group(1) or "").strip()
            body_text = (m_article.group(2) or "").strip()

        articles.append(
            {
                "number": str(num),
                "heading": None,
                "text": body_text or chunk,
            }
        )

    if trans_root_start is not None:
        tail = plain_text[trans_root_start:].strip()
    else:
        tail = plain_text[last_end:].strip()

    return articles, preamble, tail


def split_transitory_region(text: str) -> Tuple[List[Dict[str, str]], str]:
    text = text.strip()
    if not text:
        return [], ""

    m_head = TRANSITORIOS_ROOT_PATTERN.search(text)
    if not m_head:
        m_head = TRANSITORIOS_ALT_PATTERN.search(text)

    if not m_head:
        return [], text

    heading_start = m_head.start()
    heading_end = m_head.end()
    heading_text = text[heading_start:heading_end].strip()

    after_heading = text[heading_end:].strip()

    matches = list(TRANSITORY_ITEM_PATTERN.finditer(after_heading))
    if not matches:
        preamble = (heading_text + "\n" + after_heading).strip()
        return [], preamble

    transitory_items: List[Dict[str, str]] = []

    preamble_end = matches[0].start()
    transitory_preamble = after_heading[:preamble_end].strip()

    for idx, m in enumerate(matches):
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(after_heading)
        chunk = after_heading[start:end].strip()

        newline_pos = chunk.find("\n")
        if newline_pos == -1:
            header_line = chunk
            body_text = ""
        else:
            header_line = chunk[:newline_pos]
            body_text = chunk[newline_pos + 1 :].strip()

        transitory_items.append(
            {
                "label": header_line.strip(),
                "text": body_text,
            }
        )

    full_preamble = (
        (heading_text + "\n" + transitory_preamble).strip()
        if transitory_preamble
        else heading_text
    )

    return transitory_items, full_preamble


def split_articles_and_transitory(
    plain_text: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], str, str]:
    articles, preamble, tail = split_articles_and_tail(plain_text)
    transitory_items, trans_preamble = split_transitory_region(tail)
    return articles, transitory_items, preamble, trans_preamble


# -----------------
# Loading normalized docs & sources
# -----------------


def find_empty_doc_ids(normalized_dir: Path) -> List[str]:
    ids: List[str] = []
    for path in sorted(normalized_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] Could not read {path}: {e}")
            continue

        articles = data.get("articles") or []
        if len(articles) == 0:
            ids.append(str(data.get("id") or path.stem))
    return ids


def load_sources(path: Path) -> List[SourceEntry]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries: List[SourceEntry] = []
    for row in raw:
        entries.append(
            SourceEntry(
                id=row["id"],
                title=row.get("title", ""),
                type=row.get("type", ""),
                source=row.get("source", ""),
                jurisdiction=row.get("jurisdiction", ""),
                url=row["url"],
                publication_date=row.get("publication_date"),
                status=row.get("status"),
            )
        )
    return entries


def write_missing_sources(
    sources: List[SourceEntry], missing_ids: List[str], out_path: Path
) -> None:
    id_set = set(missing_ids)
    filtered = [
        {
            "id": s.id,
            "title": s.title,
            "type": s.type,
            "source": s.source,
            "jurisdiction": s.jurisdiction,
            "url": s.url,
            "publication_date": s.publication_date,
            "status": s.status,
        }
        for s in sources
        if s.id in id_set
    ]
    out_path.write_text(
        json.dumps(filtered, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] Saved {len(filtered)} entries to {out_path}")


# -----------------
# Fetch with logging
# -----------------


def fetch_pdf(url: str, *, max_retries: int = 3, timeout: int = 20) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    last_exc: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            print(f"    [HTTP] GET {url} (attempt {attempt})")
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            last_exc = exc
            print(f"    [HTTP-WARN] attempt {attempt} failed: {exc}")
            if attempt < max_retries:
                time.sleep(2**attempt)

    raise RuntimeError(
        f"Failed to fetch {url} after {max_retries} attempts"
    ) from last_exc


# -----------------
# Debug routine for a single entry
# -----------------


def debug_entry(entry: SourceEntry) -> None:
    print("=" * 80)
    print(f"ID:   {entry.id}")
    print(f"Type: {entry.type}")
    print(f"Title: {entry.title}")
    print(f"URL:  {entry.url}")
    print("-" * 80)

    try:
        pdf_bytes = fetch_pdf(entry.url)
    except Exception as e:
        print(f"[ERROR] Could not fetch PDF: {e}")
        return

    text = extract_plain_text_from_pdf(pdf_bytes)
    print(f"[INFO] Text length: {len(text)} characters")

    lines = text.splitlines()
    print(f"[INFO] Line count: {len(lines)}")

    # --- LOG: first N lines of text ---
    N = 40  # <-- bump this up/down if needed
    print("\n[SNIPPET] First lines of text:")
    for i, line in enumerate(lines[:N], start=1):
        print(f"{i:03d}: {line}")
    print("-" * 80)

    # Article positions
    positions = find_article_positions_sequential(text)
    print(f"[INFO] Found {len(positions)} 'Artículo N' positions")

    # Show first few article contexts
    MAX_ART_CONTEXT = 5
    for idx, (num, pos) in enumerate(positions[:MAX_ART_CONTEXT]):
        ctx = text[pos : pos + 300].replace("\n", " ")
        print(f"  [ART {num}] at index {pos}: {ctx}")

    if not positions:
        # Maybe it uses PRIMERO/SEGUNDO pattern without 'Artículo'
        print(
            "\n[CHECK] Looking for 'PRIMERO/SEGUNDO/TERCERO' lines without 'ARTÍCULO':"
        )
        for i, line in enumerate(lines[:200], start=1):
            up = line.upper()
            if (
                ("PRIMERO" in up or "SEGUNDO" in up or "TERCERO" in up)
                and "ARTICULO" not in up
                and "ARTÍCULO" not in up
            ):
                print(f"  line {i:03d}: {line}")

    # Transitorios
    trans_pos = find_transitorios_heading(text)
    if trans_pos is not None:
        trans_ctx = text[trans_pos : trans_pos + 200].replace("\n", " ")
        print(f"\n[INFO] TRANSITORIOS heading at index {trans_pos}: {trans_ctx}")
    else:
        print("\n[INFO] No TRANSITORIOS heading detected.")

    # Run full splitter to see what it *would* produce
    articles, transitory_items, preamble, trans_preamble = (
        split_articles_and_transitory(text)
    )
    print("\n[SUMMARY] Splitter results:")
    print(f"  Articles:   {len(articles)}")
    print(f"  Transitory: {len(transitory_items)}")
    print(f"  Preamble length: {len(preamble)} chars")
    print(f"  Transitory preamble length: {len(trans_preamble)} chars")

    if articles:
        a0 = articles[0]
        print("\n  [FIRST ARTICLE SAMPLE]")
        print(f"    number: {a0['number']}")
        print(f"    text (first 300): {a0['text'][:300].replace(chr(10), ' ')}")

    if transitory_items:
        t0 = transitory_items[0]
        print("\n  [FIRST TRANSITORY SAMPLE]")
        print(f"    label: {t0['label']}")
        print(f"    text (first 300): {t0['text'][:300].replace(chr(10), ' ')}")

    print("=" * 80)
    print()


# -----------------
# Main orchestration
# -----------------


def main() -> None:
    base_dir = Path("data")
    normalized_dir = base_dir / "normalized" / "cdmx"
    sources_path = DEFAULT_CDMX_LAW_SOURCE
    missing_out = DEFAULT_MISSING_CDMX

    if not normalized_dir.exists():
        raise SystemExit(f"Normalized dir not found: {normalized_dir}")
    if not sources_path.exists():
        raise SystemExit(f"Sources JSON not found: {sources_path}")

    print(f"[INFO] Scanning normalized docs in {normalized_dir}")
    empty_ids = find_empty_doc_ids(normalized_dir)
    print(f"[INFO] Found {len(empty_ids)} empty-doc IDs")

    print(f"[INFO] Loading sources from {sources_path}")
    sources = load_sources(sources_path)

    print("[INFO] Writing missing_cdmx.json")
    write_missing_sources(sources, empty_ids, missing_out)

    # Build dict for quick lookup
    src_by_id: Dict[str, SourceEntry] = {s.id: s for s in sources}
    print("\n[INFO] Debugging empty docs one by one...\n")

    for doc_id in empty_ids:
        entry = src_by_id.get(doc_id)
        if not entry:
            print(f"[WARN] No source entry found for id={doc_id}, skipping.")
            continue
        debug_entry(entry)


if __name__ == "__main__":
    main()
