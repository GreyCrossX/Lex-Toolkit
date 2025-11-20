#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass, asdict, field
from itertools import pairwise
from io import BytesIO
from pathlib import Path
from statistics import median
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
import pdfplumber

from services.data_pipeline.paths import DEFAULT_CDMX_LAW_SOURCE


# --------------
# Data Models
# --------------

@dataclass
class LegalArt:
    number: str
    heading: Optional[str]
    text: str


@dataclass
class LegalTransient:
    # e.g. "Artículo 1o.-", "ARTICULO PRIMERO.-", "TRANSITORIO PRIMERO.-"
    label: str
    text: str


@dataclass
class LegalDoc:
    id: str
    title: str
    type: str
    source: str
    jurisdiction: str
    source_url: str
    publication_date: Optional[str] = None
    status: Optional[str] = None
    plain_text: Optional[str] = None
    articles: Optional[List[LegalArt]] = None
    transitory: Optional[List[LegalTransient]] = None
    metadata: Dict[str, str] = field(default_factory=dict)


# -----------
# Config
# -----------

def load_law_sources(path: str | Path) -> List[Dict[str, str]]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Law sources file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

# Root heading for the code's own transitory block.
TRANSITORIOS_ROOT_PATTERN = re.compile(
    r"(?mi)^\s*art[ií]culos\s+transitorios\s*[:\-.]?\s*$"
)
TRANSITORIOS_ALT_PATTERN = re.compile(
    r"(?mi)^\s*transitorios\s*[:\-.]?\s*$"
)

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

# ---- Relaxed article header detection (method 2) ----

ORDINAL_WORDS_MAP = {
    "primero": 1, "primera": 1,
    "segundo": 2, "segunda": 2,
    "tercero": 3, "tercera": 3,
    "cuarto": 4, "cuarta": 4,
    "quinto": 5, "quinta": 5,
    "sexto": 6, "sexta": 6,
    "septimo": 7, "séptimo": 7, "septima": 7, "séptima": 7,
    "octavo": 8, "octava": 8,
    "noveno": 9, "novena": 9,
    "decimo": 10, "décimo": 10, "decima": 10, "décima": 10,
}

ORDINAL_WORDS_PATTERN = (
    "primero|primera|segundo|segunda|tercero|tercera|cuarto|cuarta|quinto|quinta|"
    "sexto|sexta|s[eé]ptimo|s[eé]ptima|octavo|octava|noveno|novena|"
    "d[eé]cimo|d[eé]cima"
)

# Matches:
#   ARTICULO 1
#   Artículo1.
#   Artículo. 1.-
#   ARTICULO PRIMERO.-
ARTICLE_HEADER_PATTERN = re.compile(
    rf"(?mi)^\s*art[ií]culo(?:\s*[\.:,-])?\s*"
    rf"((\d+)(?:o|º)?|{ORDINAL_WORDS_PATTERN})\b"
)


# -----------------
# HTTP Fetch
# -----------------

def fetch_content(url: str, *, max_retries: int = 3, timeout: int = 20) -> Tuple[str | bytes, str]:
    """
    Fetch URL with basic retry logic and return (content, kind),
    where kind is 'html' or 'pdf'.
    """
    headers = {"User-Agent": USER_AGENT}
    last_exc: Exception | None = None

    host = url.lower()
    # Only ordenjuridico sometimes has cert issues; everything else stays verified.
    verify = "ordenjuridico.gob.mx" not in host

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, verify=verify)
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "").lower()
            if "pdf" in content_type or url.lower().endswith(".pdf"):
                return resp.content, "pdf"
            else:
                return resp.text, "html"
        except Exception as exc:
            last_exc = exc
            print(f"[WARNING] Fetch attempt {attempt} failed for {url}: {exc}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts") from last_exc


# -----------------
# HTML / PDF -> plain text
# -----------------

def extract_plain_text(html: str) -> str:
    """Extract plain text from HTML, stripping scripts/styles."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    body = soup.find("body") or soup
    text = body.get_text(separator="\n")

    lines = (ln.strip() for ln in text.splitlines() if ln.strip())
    return "\n".join(lines)


SOFT_HYPHEN = "\u00ad"
PARAGRAPH_GAP_MIN = 8.0


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
    """
    Extract plain text from a PDF byte string using pdfplumber with
    explicit column/paragraph reconstruction.
    """
    with pdfplumber.open(BytesIO(data)) as pdf:
        page_texts = [
            page_text
            for page in pdf.pages
            if (page_text := _page_to_text(page))
        ]

    return "\n".join(page_texts).strip()


# -----------------
# Article detection
# -----------------

def find_article_positions_sequential(
    plain_text: str,
    max_articles: int = 10000,
) -> List[Tuple[int, int]]:
    """
    Method 1: strict sequential detection: 'Artículo 1', 'Artículo 2', ...
    """
    positions: List[Tuple[int, int]] = []
    start_pos = 0
    i = 1

    while i <= max_articles:
        pattern = re.compile(
            rf"(?mi)^\s*art[ií]culo\s+{i}(?:o|º)?\b"
        )
        m = pattern.search(plain_text, start_pos)
        if not m:
            break

        positions.append((i, m.start()))
        start_pos = m.end()
        i += 1

    return positions


def find_article_positions_relaxed(
    plain_text: str,
    max_articles: int = 10000,
) -> List[Tuple[int, int]]:
    """
    Method 2: relaxed detection using ARTICLE_HEADER_PATTERN.

    Handles:
      - ARTICULO 1
      - Artículo1.
      - Artículo. 1.-
      - ARTICULO PRIMERO.-
    """
    positions: List[Tuple[int, int]] = []

    for m in ARTICLE_HEADER_PATTERN.finditer(plain_text):
        token = (m.group(1) or "").strip()
        num: Optional[int] = None

        # Numeric case: "1" or "1o"/"1º"
        m_num = re.match(r"^(\d+)", token)
        if m_num:
            try:
                num = int(m_num.group(1))
            except ValueError:
                num = None
        else:
            # Ordinal word case
            num = ORDINAL_WORDS_MAP.get(token.lower())

        if not num:
            continue
        if num > max_articles:
            continue

        positions.append((num, m.start()))

    positions.sort(key=lambda tup: tup[1])
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
) -> Tuple[List[LegalArt], str, str, Optional[str]]:
    """
    Try method 1 (sequential numeric articles).
    If it fails, try method 2 (relaxed regex).
    If both fail, mark as ocr_pending_no_articles.
    Returns:
        articles, preamble, tail, parse_issue
    """
    parse_issue: Optional[str] = None

    # Method 1
    positions = find_article_positions_sequential(plain_text)
    method_used = "sequential"

    # If no luck, try relaxed method 2
    if not positions:
        positions = find_article_positions_relaxed(plain_text)
        method_used = "relaxed" if positions else "none"

    if not positions:
        # No article headers found at all
        preamble = plain_text.strip()
        tail = ""
        if plain_text.strip():
            parse_issue = "ocr_pending_no_articles"
        else:
            # empty text will be tagged more specifically in build_document
            parse_issue = "ocr_pending_no_articles"
        return [], preamble, tail, parse_issue

    # We found some articles, so not OCR-pending
    articles: List[LegalArt] = []

    first_start = positions[0][1]
    preamble = plain_text[:first_start].strip()

    spans: List[Tuple[int, int, int]] = []
    for idx, (num, start) in enumerate(positions):
        end = positions[idx + 1][1] if idx + 1 < len(positions) else len(plain_text)
        spans.append((num, start, end))

    _, last_article_start, last_end = spans[-1]

    search_start = max(0, last_article_start - 100)
    trans_root_start = find_transitorios_heading(plain_text, search_start)

    for num, start, end in spans:
        if trans_root_start is not None and start < trans_root_start < end:
            end = trans_root_start

        chunk = plain_text[start:end].strip()
        body_text = chunk

        m_article = ARTICLE_INLINE_PATTERN.match(chunk)
        if m_article:
            header_line = (m_article.group(1) or "").strip() or None  # noqa: F841
            body_text = (m_article.group(2) or "").strip()

        articles.append(
            LegalArt(
                number=str(num),
                heading=None,
                text=body_text or chunk,
            )
        )

    if trans_root_start is not None:
        tail = plain_text[trans_root_start:].strip()
    else:
        tail = plain_text[last_end:].strip()

    # You could log method_used if you want to debug:
    # print(f"[DEBUG] Article detection method used: {method_used}")

    return articles, preamble, tail, parse_issue


# -----------------
# Transitory parsing
# -----------------

def split_transitory_region(text: str) -> Tuple[List[LegalTransient], str]:
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

    transitory_items: List[LegalTransient] = []

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
            body_text = chunk[newline_pos + 1:].strip()

        transitory_items.append(
            LegalTransient(
                label=header_line.strip(),
                text=body_text,
            )
        )

    full_preamble = (heading_text + "\n" + transitory_preamble).strip() if transitory_preamble else heading_text

    return transitory_items, full_preamble


def split_articles_and_transitory(
    plain_text: str,
) -> Tuple[List[LegalArt], List[LegalTransient], str, str, Optional[str]]:
    """
    High-level splitter:
        1) Articles + tail
        2) Transitory region from tail
    Returns:
        articles, transitory_items, preamble, transitory_preamble, parse_issue
    """
    articles, preamble, tail, parse_issue = split_articles_and_tail(plain_text)
    transitory_items, trans_preamble = split_transitory_region(tail)
    return articles, transitory_items, preamble, trans_preamble, parse_issue


# -----------------
# Document pipeline
# -----------------

def build_document(entry: Dict[str, str], plain_text: str) -> LegalDoc:
    """
    Convert a LAW_SOURCES entry + plain_text into a LegalDoc with structured articles/transitories.
    Also sets metadata['parse_issue'] when:
      - empty PDF text, or
      - text but no article headers detected (OCR-pending / weird structure).
    """
    articles, transitory_items, preamble, trans_preamble, parse_issue = split_articles_and_transitory(
        plain_text
    )

    # Refine parse_issue for truly empty text
    if not plain_text.strip():
        parse_issue = "ocr_pending_empty_pdf"

    metadata: Dict[str, str] = {
        "original_title": entry.get("title", ""),
        "source": entry.get("source", ""),
        "num_articles": str(len(articles)),
        "num_transitory": str(len(transitory_items)),
    }
    if preamble:
        metadata["preamble"] = preamble
    if trans_preamble:
        metadata["transitory_preamble"] = trans_preamble
    if parse_issue:
        metadata["parse_issue"] = parse_issue

    return LegalDoc(
        id=entry["id"],
        title=entry["title"],
        type=entry.get("type", "LEY"),
        source=entry.get("source", "DOF"),
        jurisdiction=entry.get("jurisdiction", "FEDERAL"),
        source_url=entry["url"],
        publication_date=entry.get("publication_date"),
        status=entry.get("status"),
        plain_text=plain_text,
        articles=articles,
        transitory=transitory_items,
        metadata=metadata,
    )


def save_document(doc: LegalDoc, out_dir: Path) -> None:
    """
    Save:
      - raw text:   {out_dir}/normalized/cdmx/{id}.txt
      - JSON meta:  {out_dir}/normalized/cdmx/{id}.json
    """
    norm_dir = out_dir / "normalized" / "cdmx"
    norm_dir.mkdir(parents=True, exist_ok=True)

    base_path = norm_dir / doc.id

    if doc.plain_text:
        (base_path.with_suffix(".txt")).write_text(doc.plain_text, encoding="utf-8")

    (base_path.with_suffix(".json")).write_text(
        json.dumps(asdict(doc), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[OK] Saved document {doc.id} -> {base_path}.json / .txt")
    print(f"     Articles: {len(doc.articles or [])}, Transitory: {len(doc.transitory or [])}")


def save_raw_html(entry: Dict[str, str], html: str, out_dir: Path) -> None:
    """Keep a raw HTML copy for debugging/parsing improvements."""
    raw_dir = out_dir / "raw" / "cdmx"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / (entry["id"] + ".html")

    path.write_text(html, encoding="utf-8")

    print(f"[OK] Saved raw HTML for {entry['id']} -> {path}")


def save_raw_pdf(entry: Dict[str, str], data: bytes, out_dir: Path) -> None:
    """Keep a raw PDF copy for debugging/parsing improvements."""
    raw_dir = out_dir / "raw" / "cdmx"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / (entry["id"] + ".pdf")

    path.write_bytes(data)

    print(f"[OK] Saved raw PDF for {entry['id']} -> {path}")


# -----------------
# CLI
# -----------------

def run(out_dir: Path, sources_path: Path, max_docs: Optional[int] = None) -> None:
    """Main processing loop."""
    law_sources = load_law_sources(sources_path)

    count = 0
    ocr_pending_docs: List[Dict[str, str]] = []

    for entry in law_sources:
        if max_docs is not None and count >= max_docs:
            break

        url = entry["url"]
        print(f"[INFO] Fetching {entry['id']} from {url}")

        try:
            content, kind = fetch_content(url)

            if kind == "html":
                html = content  # type: ignore[assignment]
                save_raw_html(entry, html, out_dir)
                text = extract_plain_text(html)
            else:
                pdf_bytes = content  # type: ignore[assignment]
                save_raw_pdf(entry, pdf_bytes, out_dir)
                text = extract_plain_text_from_pdf(pdf_bytes)

            doc = build_document(entry, text)
            save_document(doc, out_dir)

            parse_issue = doc.metadata.get("parse_issue")
            if parse_issue and parse_issue.startswith("ocr_pending"):
                ocr_pending_docs.append(
                    {
                        "id": doc.id,
                        "title": doc.title,
                        "type": doc.type,
                        "url": doc.source_url,
                        "parse_issue": parse_issue,
                    }
                )

            count += 1
        except Exception as e:
            print(f"[ERROR] Failed to process {entry['id']}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Dump OCR-pending docs for later OCR / manual fix
    if ocr_pending_docs:
        ocr_path = out_dir / "ocr_pending_cdmx.json"
        ocr_path.write_text(
            json.dumps(ocr_pending_docs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[INFO] Saved {len(ocr_pending_docs)} OCR-pending docs to {ocr_path}")

    print(f"[DONE] Processed {count} document(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description="CDMX legal document scraper (GOCDMX PDFs)")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data"),
        help="Base output directory (default: ./data)",
    )
    parser.add_argument(
        "--sources",
        type=Path,
        default=DEFAULT_CDMX_LAW_SOURCE,
        help=f"Path to law sources JSON (default: {DEFAULT_CDMX_LAW_SOURCE})",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=None,
        help="Optional limit for number of documents to process",
    )

    args = parser.parse_args()
    run(out_dir=args.out_dir, sources_path=args.sources, max_docs=args.max_docs)


if __name__ == "__main__":
    main()
