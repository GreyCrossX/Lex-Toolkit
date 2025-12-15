from __future__ import annotations

import uuid
import math
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


class ReviewFindingModel(BaseModel):
    section: Optional[str] = None
    location: Optional[str] = None
    issue: str
    severity: str


class ReviewIssueModel(BaseModel):
    category: str
    description: str
    severity: str
    section: Optional[str] = None
    location: Optional[str] = None


class ReviewSuggestionModel(BaseModel):
    section: Optional[str] = None
    location: Optional[str] = None
    suggestion: str
    rationale: Optional[str] = None


class ReviewQAModel(BaseModel):
    qa_notes: List[str] = []
    residual_risks: List[str] = []


class ReviewSummaryModel(BaseModel):
    summary: str
    key_improvements: List[str] = []


class ReviewState(TypedDict, total=False):
    messages: Annotated[List, add_messages]
    trace_id: Optional[str]
    firm_id: Optional[str]
    user_id: Optional[str]

    doc_type: str
    objective: Optional[str]
    audience: Optional[str]
    guidelines: Optional[str]
    jurisdiction: Optional[str]
    constraints: List[str]
    text: Optional[str]
    sections: List[Dict[str, str]]
    research_trace_id: Optional[str]
    research_summary: Optional[str]

    intake: Dict[str, Any]
    qualification: Dict[str, Any]
    conflict_check: Dict[str, Any]
    structural_findings: List[Dict[str, Any]]
    issues: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    qa_notes: List[str]
    residual_risks: List[str]
    summary: Dict[str, Any]
    status: str
    error: Optional[str]


def ingest_review_request(state: ReviewState) -> ReviewState:
    intake = {
        "doc_type": state.get("doc_type"),
        "objective": state.get("objective"),
        "audience": state.get("audience"),
        "guidelines": state.get("guidelines"),
        "jurisdiction": state.get("jurisdiction"),
        "constraints": state.get("constraints", []),
        "text": state.get("text"),
        "sections": state.get("sections", []),
        "research_trace_id": state.get("research_trace_id"),
        "research_summary": state.get("research_summary"),
    }
    return {"intake": intake, "status": ResearchStatus.INTAKE}


def structural_review(state: ReviewState) -> ReviewState:
    text = state.get("text") or ""
    sections = state.get("sections") or []
    guidelines = state.get("guidelines") or ""
    constraints = state.get("constraints", [])
    doc_type = state.get("doc_type", "documento")
    objective = state.get("objective", "")
    audience = state.get("audience", "")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Eres un revisor legal senior. Evalúa estructura y secciones para un {doc_type} dirigido a {audience}. "
                "Usa guías/restricciones y objetivo: {objective}. "
                "Devuelve JSON findings[{section?, location?, issue, severity=high|medium|low}]. Usa TODO si falta información.",
            ),
            (
                "user",
                "Secciones: {sections}\nTexto:\n{text}\nGuías: {guidelines}\nRestricciones: {constraints}",
            ),
        ]
    )
    llm = get_llm(temperature=0.0)
    data = llm.with_structured_output(List[ReviewFindingModel]).invoke(
        prompt.format(
            sections=sections,
            text=text[:4000],
            guidelines=guidelines,
            constraints=constraints,
            doc_type=doc_type,
            objective=objective,
            audience=audience,
        )
    )
    findings = [f.dict() for f in data] if data else []
    return {"structural_findings": findings, "status": ResearchStatus.QUALIFIED}


def detailed_review(state: ReviewState) -> ReviewState:
    text = state.get("text") or ""
    sections = state.get("sections") or []
    guidelines = state.get("guidelines") or ""
    constraints = state.get("constraints", [])
    jurisdiction = state.get("jurisdiction") or ""
    objective = state.get("objective", "")
    doc_type = state.get("doc_type", "documento")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Haz revisión detallada para un {doc_type}. Objetivo: {objective}. "
                "Categoriza issues en: legal_accuracy, clarity_style, consistency_refs_defs, formatting. "
                "Devuelve JSON issues[{category, description, severity=high|medium|low, section?, location?}]. No inventes; usa TODO si falta info.",
            ),
            (
                "user",
                "Secciones: {sections}\nTexto:\n{text}\nGuías: {guidelines}\nRestricciones: {constraints}\nJurisdicción: {jurisdiction}",
            ),
        ]
    )
    llm = get_llm(temperature=0.0)
    data = llm.with_structured_output(List[ReviewIssueModel]).invoke(
        prompt.format(
            sections=sections,
            text=text[:4000],
            guidelines=guidelines,
            constraints=constraints,
            jurisdiction=jurisdiction,
            doc_type=doc_type,
            objective=objective,
        )
    )
    issues = [i.dict() for i in data] if data else []
    return {"issues": issues}


def prioritize_issues(state: ReviewState) -> ReviewState:
    issues = state.get("issues", [])
    if not issues:
        return {"issues": []}

    severity_weight = {"high": 0, "medium": 1, "low": 2}
    critical_categories = {"legal_accuracy", "consistency_refs_defs"}

    def _score(issue: Dict[str, Any]) -> float:
        severity = (issue.get("severity") or "medium").lower()
        category = (issue.get("category") or "").lower()
        base = severity_weight.get(severity, 1) * 10
        category_bonus = 0 if category in critical_categories else 3
        return base + category_bonus

    ranked_pairs = sorted(
        enumerate(issues), key=lambda pair: (_score(pair[1]), pair[0])
    )
    top_cut = max(1, math.ceil(len(ranked_pairs) * 0.2))
    mid_cut = max(top_cut, math.ceil(len(ranked_pairs) * 0.6))

    prioritized: List[Dict[str, Any]] = []
    for idx, (_, issue) in enumerate(ranked_pairs):
        severity = (issue.get("severity") or "medium").lower()
        if idx < top_cut:
            priority = "p0"
        elif idx < mid_cut:
            priority = "p1" if severity == "high" else "p2"
        else:
            priority = "p3" if severity == "low" else "p2"
        prioritized.append({**issue, "priority": priority})

    return {"issues": prioritized}


def revision_suggestions(state: ReviewState) -> ReviewState:
    issues = state.get("issues", [])
    guidelines = state.get("guidelines") or ""
    constraints = state.get("constraints", [])
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Genera sugerencias estilo redline para cada issue respetando guías/restricciones. Usa TODO cuando falten datos. "
                "Devuelve suggestions[{section?, location?, suggestion, rationale?}].",
            ),
            (
                "user",
                "Issues: {issues}\nGuías: {guidelines}\nRestricciones: {constraints}",
            ),
        ]
    )
    llm = get_llm(temperature=0.2)
    data = llm.with_structured_output(List[ReviewSuggestionModel]).invoke(
        prompt.format(issues=issues, guidelines=guidelines, constraints=constraints)
    )
    suggestions = [s.dict() for s in data] if data else []
    return {"suggestions": suggestions}


def qa_pass(state: ReviewState) -> ReviewState:
    suggestions = state.get("suggestions", [])
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Haz QA final. Devuelve JSON qa_notes[], residual_risks[]. Señala cualquier pendiente.",
            ),
            ("user", "Sugerencias: {suggestions}"),
        ]
    )
    llm = get_llm(temperature=0.0)
    data = llm.with_structured_output(ReviewQAModel).invoke(
        prompt.format(suggestions=suggestions)
    )
    return {
        "qa_notes": data.qa_notes if data else [],
        "residual_risks": data.residual_risks if data else [],
        "status": ResearchStatus.ANSWERED,
    }


def summarize_review(state: ReviewState) -> ReviewState:
    findings = state.get("structural_findings", [])
    issues = state.get("issues", [])
    suggestions = state.get("suggestions", [])
    qa_notes = state.get("qa_notes", [])
    residual_risks = state.get("residual_risks", [])
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Resume la crítica. Devuelve JSON summary (texto breve) y key_improvements[].",
            ),
            (
                "user",
                "Hallazgos: {findings}\nIssues: {issues}\nSugerencias: {suggestions}\nQA: {qa_notes}\nRiesgos residuales: {residual_risks}",
            ),
        ]
    )
    llm = get_llm(temperature=0.2)
    data = llm.with_structured_output(ReviewSummaryModel).invoke(
        prompt.format(
            findings=findings,
            issues=issues,
            suggestions=suggestions,
            qa_notes=qa_notes,
            residual_risks=residual_risks,
        )
    )
    return {"summary": data.dict() if data else {}, "status": ResearchStatus.ANSWERED}


def build_review_graph() -> StateGraph:
    builder = StateGraph(ReviewState)
    builder.add_node("ingest", trace_node("ingest")(ingest_review_request))
    builder.add_node(
        "normalize_intake", trace_node("normalize_intake")(normalize_intake)
    )
    builder.add_node("classify_matter", trace_node("classify_matter")(classify_matter))
    builder.add_node("fact_extractor", trace_node("fact_extractor")(fact_extractor))
    builder.add_node("conflict_check", trace_node("conflict_check")(conflict_check))
    builder.add_node(
        "structural_review", trace_node("structural_review")(structural_review)
    )
    builder.add_node("detailed_review", trace_node("detailed_review")(detailed_review))
    builder.add_node(
        "prioritize_issues", trace_node("prioritize_issues")(prioritize_issues)
    )
    builder.add_node(
        "revision_suggestions", trace_node("revision_suggestions")(revision_suggestions)
    )
    builder.add_node("qa_pass", trace_node("qa_pass")(qa_pass))
    builder.add_node(
        "summarize_review", trace_node("summarize_review")(summarize_review)
    )

    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "normalize_intake")
    builder.add_edge("normalize_intake", "classify_matter")
    builder.add_edge("classify_matter", "fact_extractor")
    builder.add_edge("fact_extractor", "conflict_check")
    builder.add_edge("conflict_check", "structural_review")
    builder.add_edge("structural_review", "detailed_review")
    builder.add_edge("detailed_review", "prioritize_issues")
    builder.add_edge("prioritize_issues", "revision_suggestions")
    builder.add_edge("revision_suggestions", "qa_pass")
    builder.add_edge("qa_pass", "summarize_review")
    builder.add_edge("summarize_review", END)
    return builder


def run_review(
    payload: Dict[str, Any],
    *,
    firm_id: Optional[str] = None,
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> ReviewState:
    graph = build_review_graph().compile()
    initial_state: ReviewState = {
        **payload,
        "trace_id": trace_id or uuid.uuid4().hex,
        "firm_id": firm_id,
        "user_id": user_id,
        "messages": [HumanMessage(content=payload.get("text", "") or "")],
    }
    return graph.invoke(initial_state)
