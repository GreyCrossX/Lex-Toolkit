"""
PDF text extraction utilities reused from the data pipeline.

We keep this lightweight and self-contained so the API/worker image
can parse uploads robustly without pulling the entire pipeline package.
"""

from __future__ import annotations

from io import BytesIO
from statistics import median
from typing import Dict, List, Optional

import pdfplumber

SOFT_HYPHEN = "\u00ad"
PARAGRAPH_GAP_MIN = 8.0


def _normalize_word_text(text: str) -> str:
    text = text.replace(SOFT_HYPHEN, "").strip()
    return " ".join(text.split())


def _finalize_line(words: List[Dict[str, float | str]]) -> Dict[str, float | str]:
    words_sorted = sorted(words, key=lambda w: float(w["x0"]))
    parts: List[str] = []
    for w in words_sorted:
        token = _normalize_word_text(str(w.get("text", "")))
        if token:
            parts.append(token)
    text = " ".join(parts)
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
            current_top = top if current_top is None else current_top
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
    gap_threshold = (
        max(PARAGRAPH_GAP_MIN, median(heights) * 1.35) if heights else PARAGRAPH_GAP_MIN
    )

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
    for left, right in zip(xs, xs[1:]):
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


def extract_plain_text_from_pdf(
    data: bytes,
    *,
    max_pages: Optional[int] = None,
) -> str:
    """
    Extract plain text from PDF bytes using pdfplumber with simple column handling.
    Limits to max_pages when provided to avoid long-running ingests.
    """
    with pdfplumber.open(BytesIO(data)) as pdf:
        pages = pdf.pages[:max_pages] if max_pages else pdf.pages
        page_texts = [page_text for page in pages if (page_text := _page_to_text(page))]

    return "\n".join(page_texts).strip()
