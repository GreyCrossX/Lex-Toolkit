import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import apps.agent.research_graph as rg  # noqa: E402


def test_build_query_text_uses_issue_and_facts():
    step = {
        "issue_id": "I1",
        "layer": "law",
        "description": "desc",
        "status": "pending",
        "query_ids": [],
    }
    state = {
        "issues": [
            {
                "id": "I1",
                "question": "¿El despido fue injustificado?",
                "priority": "high",
                "area": "labor",
                "status": "pending",
            }
        ],
        "facts": {"relevant_facts": [{"text": "Hecho clave"}]},
    }

    text = rg._build_query_text(step, state)

    assert "despido" in text.lower()
    assert "hecho" in text.lower()


def test_run_next_search_step_with_stub_tool(monkeypatch):
    class StubTool:
        def invoke(self, payload):  # noqa: D401
            return {
                "results": [
                    {
                        "chunk_id": "C1",
                        "doc_id": "DOC-1",
                        "content": "texto",
                        "distance": 0.1,
                        "metadata": {"title": "Titulo"},
                    }
                ]
            }

    monkeypatch.setattr(rg, "pgvector_inspector_tool", StubTool())

    state = {
        "issues": [
            {
                "id": "I1",
                "question": "Pregunta",
                "priority": "high",
                "area": "labor",
                "status": "pending",
            }
        ],
        "research_plan": [
            {
                "id": "R1",
                "issue_id": "I1",
                "layer": "law",
                "description": "desc",
                "status": "pending",
                "query_ids": [],
            }
        ],
        "queries": [],
        "facts": {"relevant_facts": [{"text": "hecho"}]},
        "chosen_jurisdictions": ["federal"],
    }

    new_state = rg.run_next_search_step(state)

    assert new_state["queries"], "Queries should be appended"
    assert new_state["queries"][0]["results"], "Tool results should propagate"


def test_should_continue_respects_max_steps():
    plan = [
        {
            "id": "R1",
            "issue_id": "I1",
            "layer": "law",
            "description": "desc",
            "status": "pending",
            "query_ids": [],
        },
        {
            "id": "R2",
            "issue_id": "I1",
            "layer": "jurisprudence",
            "description": "desc",
            "status": "pending",
            "query_ids": [],
        },
    ]
    state = {"research_plan": plan, "search_runs": 2, "max_search_steps": 2}
    assert rg._should_continue_search(state) == "synthesize_briefing"
