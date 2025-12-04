"""Shared tool registry for LangGraph / LangChain agents.

These tools are meant to be reusable across agents (research, drafting, etc.).
Add new tools in this package and expose them via TOOL_REGISTRY.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from langchain_core.tools import BaseTool

from .pgvector_inspector import pgvector_inspector_tool
from .web_browser import web_browser_tool

TOOL_REGISTRY: Dict[str, BaseTool] = {
    pgvector_inspector_tool.name: pgvector_inspector_tool,
    web_browser_tool.name: web_browser_tool,
}


def get_tools(names: Iterable[str] | None = None) -> List[BaseTool]:
    """Return tools by name (or all if names is None)."""
    if names is None:
        return list(TOOL_REGISTRY.values())
    tools: List[BaseTool] = []
    for name in names:
        tool = TOOL_REGISTRY.get(name)
        if tool is not None:
            tools.append(tool)
    return tools


__all__ = ["TOOL_REGISTRY", "get_tools", "pgvector_inspector_tool", "web_browser_tool"]
