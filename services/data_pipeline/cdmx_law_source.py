#!/usr/bin/env python
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from services.data_pipeline.paths import DEFAULT_CDMX_LAW_SOURCE

# -----------------
# Config
# -----------------

BASE_ROOT = "https://data.consejeria.cdmx.gob.mx"

# We also include "historico" now; its type will be refined from the title.
CATEGORY_PATHS: Dict[str, str] = {
    "constitucion": "CONSTITUCION",
    "leyes": "LEY",
    "reglamentos": "REGLAMENTO",
    "codigos": "CODIGO",
    "historico": "LEY",  # default, overridden by title when possible
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

OUT_PATH = DEFAULT_CDMX_LAW_SOURCE


@dataclass
class LawSource:
    id: str
    title: str
    type: str
    source: str
    jurisdiction: str
    url: str
    publication_date: Optional[str] = None
    status: Optional[str] = None  # "vigente" / "abrogada"


# -----------------
# HTTP
# -----------------


def fetch_url(url: str, *, max_retries: int = 3, timeout: int = 20) -> str:
    headers = {"User-Agent": USER_AGENT}
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            last_exc = exc
            print(f"[WARNING] Fetch attempt {attempt} failed for {url}: {exc}")
            if attempt < max_retries:
                time.sleep(2**attempt)

    raise RuntimeError(
        f"Failed to fetch {url} after {max_retries} attempts"
    ) from last_exc


# -----------------
# Date helpers
# -----------------

MONTHS_ES = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "SETIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}


def parse_spanish_date(text: str) -> Optional[str]:
    """
    Parse a date like:
      'EL 27 DE AGOSTO DEL 2025'
      '27 DE AGOSTO DE 2025'
    into '2025-08-27'.
    """
    import re

    text_up = text.upper()
    # Optional "EL", then "DE <MONTH> DE/DEL <YEAR>"
    m = re.search(
        r"(?:EL\s+)?(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚÑ]+)\s+(?:DE|DEL)\s+(\d{4})",
        text_up,
    )
    if not m:
        return None

    day = int(m.group(1))
    month_name = m.group(2)
    year = int(m.group(3))

    normalized_month = (
        month_name.replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
        .replace("Ü", "U")
    )
    month = MONTHS_ES.get(normalized_month)
    if not month:
        return None

    try:
        dt = datetime(year, month, day)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def extract_dates_from_meta(meta_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Use line-based logic to extract:
      - publication_date from lines containing 'PUBLICAD'
      - last_reform from lines containing 'ÚLTIMA REFORMA' / 'ULTIMA REFORMA'
        or 'TEXTO ABROGADO' / 'TEXTO REFORMADO'.
    """
    publication_date: Optional[str] = None
    last_reform: Optional[str] = None

    lines = [ln.strip() for ln in meta_text.splitlines() if ln.strip()]
    for line in lines:
        up = line.upper()

        if "PUBLICAD" in up and publication_date is None:
            d = parse_spanish_date(line)
            if d:
                publication_date = d

        if (
            ("ÚLTIMA REFORMA" in up)
            or ("ULTIMA REFORMA" in up)
            or ("TEXTO ABROGADO" in up)
            or ("TEXTO REFORMADO" in up)
        ):
            d = parse_spanish_date(line)
            if d:
                last_reform = d

    # Fallback: if we still have nothing, scan all dates in the block
    if not publication_date or not last_reform:
        import re

        text_up = meta_text.upper()
        all_dates: List[str] = []
        for m in re.finditer(
            r"(?:EL\s+)?(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚÑ]+)\s+(?:DE|DEL)\s+(\d{4})",
            text_up,
        ):
            date_str = f"{m.group(1)} DE {m.group(2)} DE {m.group(3)}"
            iso = parse_spanish_date(date_str)
            if iso:
                all_dates.append(iso)

        all_dates = sorted(set(all_dates))
        if all_dates:
            if not publication_date:
                publication_date = all_dates[0]
            if not last_reform and len(all_dates) > 1:
                last_reform = all_dates[-1]

    return publication_date, last_reform


# -----------------
# Misc helpers
# -----------------


def slug_from_url(url: str) -> str:
    path = urlparse(url).path
    basename = os.path.basename(path)
    stem, _ext = os.path.splitext(basename)
    return stem or basename


def infer_status_from_url(pdf_url: str) -> str:
    """
    Only "vigente" or "abrogada", using URL:
      - if path contains '/historico/', treat as 'abrogada'
      - otherwise 'vigente'
    """
    path = urlparse(pdf_url).path.lower()
    if "/historico/" in path:
        return "abrogada"
    return "vigente"


def guess_type_from_title(title: str, default_type: str) -> str:
    """
    Refine type from title (for historico etc.).
    """
    up = title.strip().upper()
    if up.startswith("REGLAMENTO"):
        return "REGLAMENTO"
    if up.startswith("CÓDIGO") or up.startswith("CODIGO"):
        return "CODIGO"
    if "CONSTITUCIÓN" in up or "CONSTITUCION" in up:
        return "CONSTITUCION"
    return default_type


# -----------------
# Page parsing
# -----------------


def parse_constitucion_page(
    soup: BeautifulSoup, page_url: str, default_type: str
) -> List[LawSource]:
    """
    Parse the special constitución layout:
      div.item-page > div.art-article > table ...
    """
    laws: List[LawSource] = []

    article = soup.select_one("div.item-page div.art-article")
    if not article:
        return laws

    # One main table holds meta and links
    table = article.find("table")
    if not table:
        return laws

    tds = table.find_all("td")
    if not tds:
        return laws

    first_td = tds[0]
    # All <p> inside first td: some are PUBLICADA, some ULTIMA REFORMA, one is the name
    ps = first_td.find_all("p")
    meta_lines: List[str] = []
    title_candidate: Optional[str] = None

    for p in ps:
        txt = p.get_text(" ", strip=True)
        if not txt:
            continue
        up = txt.upper()
        if (
            "PUBLICAD" in up
            or "ÚLTIMA REFORMA" in up
            or "ULTIMA REFORMA" in up
            or "TEXTO ABROGADO" in up
            or "TEXTO REFORMADO" in up
        ):
            meta_lines.append(txt)
        else:
            # treat as title candidate; keep the longest
            if title_candidate is None or len(txt) > len(title_candidate):
                title_candidate = txt

    if not title_candidate:
        # fallback: use any text in article
        raw = article.get_text(" ", strip=True)
        title_candidate = raw[:120] if raw else "Constitución de la CDMX"

    # Find PDF link in the table
    pdf_link = None
    for a in table.find_all("a", href=True):
        if a["href"].lower().endswith(".pdf"):
            pdf_link = a
            break
    if not pdf_link:
        return laws

    pdf_url = urljoin(page_url, pdf_link["href"])
    law_id = slug_from_url(pdf_url)

    meta_text = "\n".join(meta_lines)
    publication_date, last_reform = extract_dates_from_meta(meta_text)

    doc_type = guess_type_from_title(title_candidate, default_type)
    status = infer_status_from_url(pdf_url)

    laws.append(
        LawSource(
            id=law_id,
            title=title_candidate,
            type=doc_type,
            source="GOCDMX",
            jurisdiction="CDMX",
            url=pdf_url,
            publication_date=publication_date,
            status=status,
        )
    )

    return laws


def parse_slider_layout(
    soup: BeautifulSoup, page_url: str, default_type: str
) -> List[LawSource]:
    """
    Parse the nn_sliders layout (leyes, reglamentos, codigos, historico).
    """
    laws: List[LawSource] = []

    slider_containers = soup.select("div.nn_sliders_container")
    if not slider_containers:
        return laws

    print(f"[INFO] {page_url} -> {len(slider_containers)} slider containers")

    for container in slider_containers:
        # Title: from slider header
        header_span = container.select_one(
            "div.nn_sliders_slider span span"
        ) or container.select_one("div.nn_sliders_slider span a span")
        title = header_span.get_text(" ", strip=True) if header_span else None

        if not title:
            h2 = container.select_one("h2.nn_sliders_title")
            if h2:
                title = h2.get_text(" ", strip=True)

        if not title:
            continue

        # PDF link inside the container
        pdf_link = None
        for a in container.find_all("a", href=True):
            if a["href"].lower().endswith(".pdf"):
                pdf_link = a
                break
        if not pdf_link:
            # some entries may only have DOCX; skip for now
            continue

        pdf_url = urljoin(page_url, pdf_link["href"])
        law_id = slug_from_url(pdf_url)

        # Meta: all <p> inside container
        meta_text = "\n".join(
            p.get_text(" ", strip=True) for p in container.find_all("p")
        )

        publication_date, last_reform = extract_dates_from_meta(meta_text)
        doc_type = guess_type_from_title(title, default_type)
        status = infer_status_from_url(pdf_url)

        laws.append(
            LawSource(
                id=law_id,
                title=title,
                type=doc_type,
                source="GOCDMX",
                jurisdiction="CDMX",
                url=pdf_url,
                publication_date=publication_date,
                status=status,
            )
        )

    return laws


def parse_law_page(
    html: str, page_url: str, slug: str, default_type: str
) -> Tuple[List[LawSource], Optional[str]]:
    """
    Parse one category page:
      - 'constitucion': special table layout
      - others: nn_sliders layout (leyes, reglamentos, codigos, historico)
      - keeps pagination via 'Siguiente' link
    """
    soup = BeautifulSoup(html, "html.parser")
    laws: List[LawSource] = []

    if slug == "constitucion":
        laws.extend(parse_constitucion_page(soup, page_url, default_type))
    else:
        # sliders for leyes / reglamentos / codigos / historico
        slider_laws = parse_slider_layout(soup, page_url, default_type)
        laws.extend(slider_laws)

    # Pagination: look for 'Siguiente'
    next_url: Optional[str] = None
    for a in soup.find_all("a", href=True):
        label = a.get_text(" ", strip=True).upper()
        if "SIGUIENTE" in label:
            next_url = urljoin(page_url, a["href"])
            break

    return laws, next_url


# -----------------
# Save / main
# -----------------


def save_law_sources(laws: List[LawSource], path: Path) -> None:
    data: List[Dict[str, object]] = [
        {
            "id": law.id,
            "title": law.title,
            "type": law.type,
            "source": law.source,
            "jurisdiction": law.jurisdiction,
            "url": law.url,
            "publication_date": law.publication_date,
            "status": law.status,
        }
        for law in laws
    ]

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] Saved {len(laws)} CDMX laws to {path}")


def main() -> None:
    all_laws: List[LawSource] = []
    seen_urls: set[str] = set()

    for slug, default_type in CATEGORY_PATHS.items():
        base_url = f"{BASE_ROOT}/index.php/leyes/{slug}"
        page_url: Optional[str] = base_url
        page_no = 1

        while page_url:
            print(f"[INFO] [{slug}] Fetching page {page_no}: {page_url}")
            html = fetch_url(page_url)
            laws, next_url = parse_law_page(html, page_url, slug, default_type)

            for law in laws:
                if law.url in seen_urls:
                    continue
                seen_urls.add(law.url)
                all_laws.append(law)

            page_url = next_url
            page_no += 1
            time.sleep(0.5)

    # Deterministic order: by type then title
    all_laws.sort(key=lambda x: (x.type, x.title.lower()))

    print(f"[INFO] Total unique CDMX laws collected: {len(all_laws)}")
    for law in all_laws[:10]:
        print(
            f"  {law.id} | {law.type} | {law.title} | "
            f"{law.url} | pub={law.publication_date} | status={law.status}"
        )

    save_law_sources(all_laws, OUT_PATH)


if __name__ == "__main__":
    main()
