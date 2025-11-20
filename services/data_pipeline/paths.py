from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PACKAGE_ROOT / "config"

DEFAULT_CDMX_LAW_SOURCE = CONFIG_DIR / "cdmx_law_source.json"
DEFAULT_LAW_SOURCES = CONFIG_DIR / "law_sources.json"
DEFAULT_MISSING_CDMX = CONFIG_DIR / "missing_cdmx.json"
DEFAULT_MISSING_LAWS = CONFIG_DIR / "missing_laws.json"
