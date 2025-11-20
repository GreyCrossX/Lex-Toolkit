#!/usr/bin/env python
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from services.data_pipeline.paths import DEFAULT_LAW_SOURCES

# -----------------
# Config
# -----------------

INDEX_URL = "https://www.ordenjuridico.gob.mx/leyes.php"
BASE_URL = "https://www.ordenjuridico.gob.mx"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

OUT_PATH = DEFAULT_LAW_SOURCES


@dataclass
class LawSource:
    id: str
    title: str
    type: str
    source: str
    jurisdiction: str
    url: str
    publication_date: Optional[str] = None
    status: Optional[str] = None  # we'll store "last reform date" here (ISO) if present


# -----------------
# Helpers
# -----------------

def fetch_url(url: str, *, max_retries: int = 3, timeout: int = 20) -> str:
    headers = {"User-Agent": USER_AGENT}
    last_exc: Exception | None = None

    host = url.lower()
    # Same trick as in your other script: skip cert validation for this host if needed
    verify = "ordenjuridico.gob.mx" not in host

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, verify=verify)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            last_exc = exc
            print(f"[WARNING] Index fetch attempt {attempt} failed: {exc}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Failed to fetch index {url} after {max_retries} attempts") from last_exc


def normalize_date(raw: str) -> Optional[str]:
    """
    Convert dates like '25-05-1972' to '1972-05-25'.
    If empty / '-', return None.
    If format is unexpected, return raw as-is.
    """
    raw = raw.strip()
    if not raw or raw == "-":
        return None
    try:
        dt = datetime.strptime(raw, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        # Keep the original if it's in some weird format
        return raw


def extract_doc_slug(doc_id: str) -> Optional[str]:
    """
    From '.././Documentos/Federal/wo17179.doc' → 'wo17179'
    """
    if not doc_id:
        return None
    rel = doc_id.replace(".././", "").lstrip("/")
    basename = os.path.basename(rel)
    stem, _ext = os.path.splitext(basename)
    return stem or None


def build_html_url_from_doc_id(doc_id: str) -> Optional[str]:
    """
    Transform something like:
      '.././Documentos/Federal/wo17179.doc'
    into:
      'https://www.ordenjuridico.gob.mx/Documentos/Federal/html/wo17179.html'
    """
    if not doc_id:
        return None

    # Strip the leading '.././' and leading slashes
    rel = doc_id.replace(".././", "").lstrip("/")

    # Extract basename 'wo17179.doc' and stem 'wo17179'
    basename = os.path.basename(rel)
    stem, _ext = os.path.splitext(basename)
    if not stem:
        return None

    html_rel = f"Documentos/Federal/html/{stem}.html"
    return urljoin(BASE_URL + "/", html_rel)


def guess_type_from_title(title: str) -> str:
    """
    Default to 'LEY', override to 'REGLAMENTO' when title starts with 'Reglamento'.
    """
    t = title.strip().upper()
    if t.startswith("REGLAMENTO"):
        return "REGLAMENTO"
    # Default
    return "LEY"


def parse_index_for_laws(html: str) -> List[LawSource]:
    """
    Parse the leyes.php index using the actual <tr> structure:

    <tr>
      <td width="20" align="center">298</td>
      <td width="250">
         <a href="#" class="basic" id=".././Documentos/Federal/wo17179.doc">
            Ley sobre Elaboración y Venta de Café Tostado
         </a>
      </td>
      <td width="90" align="center">25-05-1972</td>
      <td width="90" align="center">10-12-2004</td>
    </tr>
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    print(f"[INFO] Found {len(rows)} <tr> rows in index")

    laws: List[LawSource] = []
    seen_urls = set()
    type_counts: Dict[str, int] = {}

    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        # Column 1 is just a running number in the table; we don't use it as ID anymore.
        idx_text = tds[0].get_text(strip=True)
        try:
            int(idx_text)
        except (TypeError, ValueError):
            # Header row or something else, skip
            continue

        # 2) Title + doc id (second column)
        link = tds[1].find("a", class_="basic")
        if not link:
            continue

        doc_id_raw = link.get("id") or ""
        if not doc_id_raw or isinstance(doc_id_raw, list):
            continue
        doc_id: str = str(doc_id_raw)
        slug = extract_doc_slug(doc_id)
        if not slug:
            continue

        html_url = build_html_url_from_doc_id(doc_id)
        if not html_url:
            continue

        # Avoid duplicates
        if html_url in seen_urls:
            continue
        seen_urls.add(html_url)

        title = link.get_text(" ", strip=True)
        doc_type = guess_type_from_title(title)

        # 3) Publication date (third column)
        pub_raw = tds[2].get_text(strip=True)
        publication_date = normalize_date(pub_raw)

        # 4) Last reform date (fourth column) → put into `status` for now
        reform_raw = tds[3].get_text(strip=True)
        last_reform = normalize_date(reform_raw)

        laws.append(
            LawSource(
                id=slug,  # <- use slug from URL, e.g. 'wo17186'
                title=title,
                type=doc_type,
                source="DOF",
                jurisdiction="FEDERAL",
                url=html_url,
                publication_date=publication_date,
                status=last_reform,
            )
        )

        # Count by type
        type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

    # Sort deterministically, e.g. by title
    laws.sort(key=lambda x: x.title.lower())

    print(f"[INFO] Identified {len(laws)} law rows")
    print("[INFO] Type breakdown:")
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}")

    return laws


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
    print(f"[OK] Saved {len(laws)} laws to {path}")


def main() -> None:
    print(f"[INFO] Fetching index {INDEX_URL}")
    html = fetch_url(INDEX_URL)

    laws = parse_index_for_laws(html)

    print("[INFO] First 5 entries:")
    for law in laws[:5]:
        print(
            f"  {law.id} | {law.type} | {law.title} | "
            f"{law.url} | pub={law.publication_date} | last_ref={law.status}"
        )

    save_law_sources(laws, OUT_PATH)


if __name__ == "__main__":
    main()
