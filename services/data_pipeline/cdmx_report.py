#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any


@dataclass
class DocStats:
    id: str
    title: str
    type: str
    num_articles: int
    num_transitory: int


def load_docs(normalized_dir: Path) -> List[DocStats]:
    docs: List[DocStats] = []

    for path in sorted(normalized_dir.glob("*.json")):
        try:
            data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] Failed to load JSON {path}: {e}")
            continue

        doc_id = data.get("id") or path.stem
        title = data.get("title") or ""
        doc_type = data.get("type") or "UNKNOWN"

        articles = data.get("articles") or []
        transitory = data.get("transitory") or []

        num_articles = len(articles)
        num_transitory = len(transitory)

        docs.append(
            DocStats(
                id=str(doc_id),
                title=str(title),
                type=str(doc_type),
                num_articles=num_articles,
                num_transitory=num_transitory,
            )
        )

    return docs


def print_report(docs: List[DocStats]) -> None:
    if not docs:
        print("No documents found.")
        return

    # 1) Metadata: count by type
    by_type = Counter(d.type for d in docs)

    print("========================================")
    print("CDMX LEGAL DOCS REPORT")
    print("========================================\n")

    print("1) Documents by type")
    print("--------------------")
    for doc_type, count in sorted(by_type.items()):
        print(f"  {doc_type}: {count}")
    print()

    # 2) Empty docs (articles == 0)
    empty_docs = [d for d in docs if d.num_articles == 0]

    print("2) Empty docs (articles == 0)")
    print("-----------------------------")
    if not empty_docs:
        print("  None 🎉")
    else:
        for d in empty_docs:
            title_snippet = (d.title[:80] + "…") if len(d.title) > 80 else d.title
            print(f"  - id={d.id} | type={d.type} | title={title_snippet}")
    print()

    # 3) Per-document stats
    print("3) Per-document article/transitory counts")
    print("-----------------------------------------")
    print("id | type | #articles | #transitory")
    print("-----------------------------------------")
    for d in docs:
        print(f"{d.id} | {d.type} | {d.num_articles} | {d.num_transitory}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a simple report over normalized legal docs."
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("data"),
        help="Base data directory (default: ./data)",
    )
    parser.add_argument(
        "--subdir",
        type=str,
        default="cdmx",
        help="Subdirectory under normalized/ to inspect (default: cdmx)",
    )

    args = parser.parse_args()

    normalized_dir = args.base_dir / "normalized" / args.subdir
    if not normalized_dir.exists():
        raise SystemExit(f"Normalized directory not found: {normalized_dir}")

    print(f"[INFO] Loading docs from {normalized_dir}")
    docs = load_docs(normalized_dir)
    print(f"[INFO] Loaded {len(docs)} document(s)\n")

    print_report(docs)


if __name__ == "__main__":
    main()
