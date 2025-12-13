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


def test_run_synthetic_eval_with_stub_runner():
    rg = importlib.import_module("apps.agent.research_graph")

    def runner(prompt: str):
        # Minimal stub: mark area/jurisdiction based on prompt keywords.
        area = "laboral" if "despido" in prompt.lower() else "civil"
        return {
            "area_of_law": {"primary": area},
            "chosen_jurisdictions": ["cdmx" if "cdmx" in prompt.lower() else "local"],
        }

    results = rg.run_synthetic_eval(runner, rg.get_synthetic_eval_scenarios())
    assert results, "synthetic eval should return results"
    # At least one should pass with our stub logic.
    assert any(r["passed"] for r in results)
