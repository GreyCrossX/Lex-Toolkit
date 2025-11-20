#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict

from services.data_pipeline.paths import (
    DEFAULT_LAW_SOURCES,
    DEFAULT_MISSING_LAWS,
)

LAW_SOURCES_PATH = DEFAULT_LAW_SOURCES
OUT_DIR = Path("data")  # normalized data lives under repo_root/data

def main() -> None:
    if not LAW_SOURCES_PATH.exists():
        raise SystemExit(f"law_sources.json not found at {LAW_SOURCES_PATH}")

    with LAW_SOURCES_PATH.open("r", encoding="utf-8") as f:
        sources: List[Dict[str, str]] = json.load(f)

    norm_dir = OUT_DIR / "normalized" / "dof"

    missing: List[Dict[str, str]] = []
    for entry in sources:
        doc_id = entry["id"]
        json_path = norm_dir / f"{doc_id}.json"
        if not json_path.exists():
            missing.append(entry)

    print(f"[INFO] Total sources: {len(sources)}")
    print(f"[INFO] Normalized dir: {norm_dir}")
    print(f"[INFO] Missing documents: {len(missing)}")

    for e in missing:
        print(f"  - {e['id']} | {e['title']} | {e['url']}")

    # optionally save to a file for later inspection
    if missing:
        DEFAULT_MISSING_LAWS.write_text(
            json.dumps(missing, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[OK] Wrote missing list to {DEFAULT_MISSING_LAWS}")

if __name__ == "__main__":
    main()
