from __future__ import annotations

import uuid
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel

from .llm import get_llm
from .research_graph import (
    ResearchStatus,
    classify_matter,
    conflict_check,
    fact_extractor,
    normalize_intake,
    trace_node,
)


class DraftSectionModel(BaseModel):
    title: str
    content: str


class DraftPlanModel(BaseModel):
    sections: List[DraftSectionModel]
    open_questions: List[str] = []


class DraftReviewModel(BaseModel):
    assumptions: List[str] = []
    risks: List[str] = []
    open_questions: List[str] = []


class DraftState(TypedDict, total=False):
    messages: Annotated[List, add_messages]
    trace_id: Optional[str]
    firm_id: Optional[str]
    user_id: Optional[str]

    # Intake
    doc_type: str
    objective: Optional[str]
    audience: Optional[str]
    tone: Optional[str]
    language: Optional[str]
    context: Optional[str]
    facts: List[str]
    requirements: List[Dict[str, str]]
    constraints: List[str]
    research_trace_id: Optional[str]
    research_summary: Optional[str]

    # Derived
    intake: Dict[str, Any]
    qualification: Dict[str, Any]
    parties: List[Dict[str, Any]]
    conflict_check: Dict[str, Any]
    plan: List[Dict[str, str]]
    draft_sections: List[Dict[str, str]]
    draft: str
    review: Dict[str, Any]
    status: str
    error: Optional[str]


def ingest_draft_request(state: DraftState) -> DraftState:
    """Seed state with intake fields provided by API."""
    intake = {
        "doc_type": state.get("doc_type"),
        "objective": state.get("objective"),
        "audience": state.get("audience"),
        "tone": state.get("tone"),
        "language": state.get("language", "es"),
        "context": state.get("context"),
        "facts": state.get("facts", []),
        "requirements": state.get("requirements", []),
        "constraints": state.get("constraints", []),
        "research_trace_id": state.get("research_trace_id"),
        "research_summary": state.get("research_summary"),
    }
    return {
        "intake": intake,
        "status": ResearchStatus.INTAKE,
    }


def template_selector(state: DraftState) -> DraftState:
    doc_type = state.get("doc_type", "documento")
    constraints = state.get("constraints", [])
    reqs = state.get("requirements", [])
    facts = state.get("facts", [])
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Eres un abogado que diseña la estructura de un documento {doc_type}. "
                "Devuelve JSON con sections [{title, content}] donde content es un borrador breve (1-2 oraciones). "
                "Incluye preguntas abiertas si faltan datos clave.",
            ),
            ("user", "Doc_type: {doc_type}\nRequisitos: {reqs}\nRestricciones: {constraints}\nHechos: {facts}"),
        ]
    )
    llm = get_llm(temperature=0.0)
    data = llm.with_structured_output(DraftPlanModel).invoke(
        prompt.format(doc_type=doc_type, reqs=reqs, constraints=constraints, facts=facts)
    )
    sections = [s.dict() for s in data.sections] if data and getattr(data, "sections", None) else []
    return {
        "plan": sections,
        "status": ResearchStatus.PLAN_BUILT,
        "draft_sections": sections,
        "open_questions": data.open_questions if data else [],
    }


def draft_builder(state: DraftState) -> DraftState:
    sections = state.get("draft_sections") or state.get("plan") or []
    tone = state.get("tone", "formal")
    audience = state.get("audience", "cliente")
    research_summary = state.get("research_summary")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Redacta cada sección para el público {audience} con tono {tone}. "
                "Si faltan datos, escribe 'TODO: …' en la sección en lugar de inventar.",
            ),
            ("user", "Secciones: {sections}\nResumen de investigación (opcional): {research_summary}"),
        ]
    )
    llm = get_llm(temperature=0.2)
    content = llm.invoke(
        prompt.format(
            audience=audience,
            tone=tone,
            sections=sections,
            research_summary=research_summary or "N/A",
        )
    )
    text = content.content if hasattr(content, "content") else str(content)
    # Simple splitter: keep provided titles, update content with LLM output fallback.
    draft_sections: List[Dict[str, str]] = []
    for idx, sec in enumerate(sections):
        draft_sections.append({"title": sec.get("title", f"Sección {idx+1}"), "content": sec.get("content", "")})
    return {
        "draft": text,
        "draft_sections": draft_sections,
        "status": ResearchStatus.ANSWERED,
    }


def draft_reviewer(state: DraftState) -> DraftState:
    sections = state.get("draft_sections", [])
    requirements = state.get("requirements", [])
    constraints = state.get("constraints", [])
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Revisa el borrador. Devuelve JSON con: assumptions[], risks[], open_questions[]. "
                "Marca riesgo si falta una cláusula requerida o no se respeta una restricción.",
            ),
            ("user", "Secciones: {sections}\nRequisitos: {requirements}\nRestricciones: {constraints}"),
        ]
    )
    llm = get_llm(temperature=0.0)
    data = llm.with_structured_output(DraftReviewModel).invoke(
        prompt.format(sections=sections, requirements=requirements, constraints=constraints)
    )
    return {"review": data.dict() if data else {}, "status": ResearchStatus.ANSWERED}


def build_drafting_graph() -> StateGraph:
    builder = StateGraph(DraftState)
    builder.add_node("ingest", trace_node("ingest")(ingest_draft_request))
    builder.add_node("normalize_intake", trace_node("normalize_intake")(normalize_intake))
    builder.add_node("classify_matter", trace_node("classify_matter")(classify_matter))
    builder.add_node("fact_extractor", trace_node("fact_extractor")(fact_extractor))
    builder.add_node("conflict_check", trace_node("conflict_check")(conflict_check))
    builder.add_node("template_selector", trace_node("template_selector")(template_selector))
    builder.add_node("draft_builder", trace_node("draft_builder")(draft_builder))
    builder.add_node("draft_reviewer", trace_node("draft_reviewer")(draft_reviewer))

    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "normalize_intake")
    builder.add_edge("normalize_intake", "classify_matter")
    builder.add_edge("classify_matter", "fact_extractor")
    builder.add_edge("fact_extractor", "conflict_check")
    builder.add_edge("conflict_check", "template_selector")
    builder.add_edge("template_selector", "draft_builder")
    builder.add_edge("draft_builder", "draft_reviewer")
    builder.add_edge("draft_reviewer", END)
    return builder


def run_draft(
    payload: Dict[str, Any],
    *,
    firm_id: Optional[str] = None,
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> DraftState:
    graph = build_drafting_graph().compile()
    initial_state: DraftState = {
        **payload,
        "trace_id": trace_id or uuid.uuid4().hex,
        "firm_id": firm_id,
        "user_id": user_id,
        "messages": [HumanMessage(content=payload.get("context", "") or "")],
    }
    return graph.invoke(initial_state)
