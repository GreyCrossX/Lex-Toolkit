from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, field_validator


USER_AGENT = "LexToolkitBot/0.1 (+https://example.com)"
MAX_BYTES_DEFAULT = 200_000
DEFAULT_TIMEOUT = 10.0
ENV_ALLOWLIST = os.environ.get("BROWSER_ALLOWED_DOMAINS")


class WebBrowserArgs(BaseModel):
    url: str = Field(..., description="URL to fetch (http/https)")
    allowed_domains: Optional[List[str]] = Field(None, description="Optional allowlist of hostnames")
    max_bytes: int = Field(MAX_BYTES_DEFAULT, ge=10_000, le=1_000_000, description="Max bytes to read")

    @field_validator("url")
    def _validate_scheme(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only http/https URLs are allowed")
        return v

    @field_validator("allowed_domains", mode="before")
    def _normalize_domains(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        return [d.lower() for d in v]


def _run_web_browser(url: str, allowed_domains: Optional[List[str]] = None, max_bytes: int = MAX_BYTES_DEFAULT) -> Dict[str, Any]:
    parsed = urlparse(url)
    env_allow = [d.strip().lower() for d in ENV_ALLOWLIST.split(",") if d.strip()] if ENV_ALLOWLIST else []
    allowlist = allowed_domains or env_allow
    if allowlist and parsed.hostname and parsed.hostname.lower() not in allowlist:
        return {"url": url, "status": "blocked", "reason": "Host not in allowlist", "links": [], "text": ""}

    headers = {"User-Agent": USER_AGENT}
    try:
        with httpx.Client(follow_redirects=True, headers=headers, timeout=DEFAULT_TIMEOUT) as client:
            resp = client.get(url)
            status = resp.status_code
            content = resp.content[:max_bytes]
    except Exception as exc:  # pragma: no cover - network safety
        return {"url": url, "status": "error", "reason": str(exc), "links": [], "text": ""}

    soup = BeautifulSoup(content, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    text = " ".join(soup.stripped_strings)
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href:
            continue
        links.append(urljoin(url, href))
        if len(links) >= 25:
            break

    return {
        "url": url,
        "status": status,
        "title": title,
        "text": text[:10000],
        "links": links,
    }


web_browser_tool = StructuredTool.from_function(
    name="web_browser",
    description="Fetch a web page (http/https), returning title, cleaned text, and up to 25 links.",
    func=_run_web_browser,
    args_schema=WebBrowserArgs,
)


__all__ = ["web_browser_tool", "WebBrowserArgs"]
