import importlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_workflow_map_contains_research_and_conflict():
    rg = importlib.import_module("apps.agent.research_graph")
    wf = rg.WORKFLOW_BY_TOOL["research"]
    assert "normalize_intake" in wf
    assert "conflict_check" in wf
    assert wf.index("conflict_check") > wf.index("fact_extractor")
    assert wf[-1] == "synthesize_briefing"


def test_get_workflow_nodes_for_tool_default():
    rg = importlib.import_module("apps.agent.research_graph")
    nodes = rg.get_workflow_nodes_for_tool("summary")
    assert "normalize_intake" in nodes
    assert nodes[-1] == "synthesize_briefing"
