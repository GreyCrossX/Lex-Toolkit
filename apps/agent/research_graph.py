from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Annotated, Any, Callable, Dict, List, Optional, Type, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field

from .llm import get_llm
from .tools import get_tools, pgvector_inspector_tool


logger = logging.getLogger(__name__)


# ---------- Status helpers ----------


class ResearchStatus:
    INTAKE = "intake"
    QUALIFIED = "qualified"
    CLASSIFIED = "classified"
    FACTS_STRUCTURED = "facts_structured"
    PLAN_BUILT = "plan_built"
    ANSWERED = "answered"
    ERROR = "error"


# ---------- Typed state ----------


class ClientIntake(TypedDict, total=False):
    source_type: str
    source_ref: Optional[str]
    raw_text: str
    language: str
    attachments: List[str]


class MatterQualification(TypedDict, total=False):
    is_legal_matter: bool
    confidence: float
    recommended_path: str
    rationale: str


class AreaOfLaw(TypedDict, total=False):
    primary: str
    secondary: List[str]
    confidence: float
    rationale: str


class ResearchIssue(TypedDict, total=False):
    id: str
    question: str
    priority: str
    area: str
    status: str


class ResearchStep(TypedDict, total=False):
    id: str
    issue_id: str
    layer: str
    description: str
    status: str
    query_ids: List[str]
    top_k: Optional[int]


class QueryResult(TypedDict, total=False):
    doc_id: str
    title: str
    citation: str
    snippet: str
    score: float
    norm_layer: str


class QueryRun(TypedDict, total=False):
    id: str
    issue_id: str
    layer: str
    query: str
    filters: Dict[str, str]
    top_k: int
    results: List[QueryResult]


class ResearchBriefing(TypedDict, total=False):
    overview: str
    legal_characterization: str
    recommended_strategy: str
    issue_answers: List[Dict[str, str]]
    open_questions: List[str]


class ResearchState(TypedDict, total=False):
    messages: Annotated[List, add_messages]

    firm_id: Optional[str]
    user_id: Optional[str]
    trace_id: Optional[str]
    max_search_steps: Optional[int]
    search_runs: int

    intake: ClientIntake
    qualification: MatterQualification

    jurisdiction_hypotheses: List[Dict]
    chosen_jurisdictions: List[str]
    area_of_law: AreaOfLaw

    parties: List[Dict]
    facts: Dict

    issues: List[ResearchIssue]
    research_plan: List[ResearchStep]
    queries: List[QueryRun]

    briefing: ResearchBriefing

    status: str
    error: Optional[str]


# ---------- Structured output models ----------


class QualificationModel(BaseModel):
    is_legal_matter: bool
    confidence: float = Field(..., ge=0, le=1)
    recommended_path: str
    rationale: str
    model_config = ConfigDict(extra="allow")


class JurisdictionHypothesisModel(BaseModel):
    level: str
    label: Optional[str] = None
    confidence: float = Field(..., ge=0, le=1)
    basis: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class AreaOfLawModel(BaseModel):
    primary: str
    secondary: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    rationale: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class JurisdictionAreaModel(BaseModel):
    jurisdiction_hypotheses: List[JurisdictionHypothesisModel]
    chosen_jurisdictions: List[str]
    area_of_law: AreaOfLawModel
    model_config = ConfigDict(extra="allow")


class PartyModel(BaseModel):
    id: str
    role: str
    name: str
    model_config = ConfigDict(extra="allow")


class FactItemModel(BaseModel):
    id: str
    text: str
    relevance: str = "relevant"
    relevance_reason: Optional[str] = None
    date: Optional[str] = None
    parties: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    model_config = ConfigDict(extra="allow")


class FactsModel(BaseModel):
    relevant_facts: List[FactItemModel]
    irrelevant_facts: List[FactItemModel] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow")


class FactExtractionModel(BaseModel):
    parties: List[PartyModel]
    facts: FactsModel
    model_config = ConfigDict(extra="allow")


class IssueModel(BaseModel):
    id: str
    question: str
    priority: str
    area: str
    status: str
    model_config = ConfigDict(extra="allow")


class IssuesModel(BaseModel):
    issues: List[IssueModel]
    model_config = ConfigDict(extra="allow")


class ResearchStepModel(BaseModel):
    id: str
    issue_id: str
    layer: str
    description: str
    status: str
    query_ids: List[str] = Field(default_factory=list)
    top_k: Optional[int] = None
    model_config = ConfigDict(extra="allow")


class ResearchPlanModel(BaseModel):
    research_plan: List[ResearchStepModel]
    model_config = ConfigDict(extra="allow")


class IssueAnswerModel(BaseModel):
    issue_id: Optional[str] = None
    answer: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = None
    model_config = ConfigDict(extra="allow")


class BriefingModel(BaseModel):
    overview: str
    legal_characterization: str
    recommended_strategy: str
    issue_answers: List[IssueAnswerModel]
    open_questions: List[str]
    model_config = ConfigDict(extra="allow")


# ---------- Helpers ----------


def _structured_call(
    prompt: ChatPromptTemplate,
    model_cls: Type[BaseModel],
    fmt: Dict[str, Any],
    fallback: Callable[[Exception], Any] | Any,
    *,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
):
    with trace_span("structured_call", model=model_cls.__name__):
        try:
            llm = get_llm(
                temperature=temperature, max_tokens=max_tokens
            ).with_structured_output(model_cls)
            resp = llm.invoke(prompt.format_prompt(**fmt).to_messages())
            if isinstance(resp, BaseModel):
                payload = resp.model_dump()
            elif isinstance(resp, dict):
                payload = resp
            else:
                payload = getattr(resp, "dict", lambda: {"result": resp})()
            return payload
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.warning("Structured call failed for %s: %s", model_cls.__name__, exc)
            return fallback(exc) if callable(fallback) else fallback


def _build_query_text(step: ResearchStep, state: ResearchState) -> str:
    issues = state.get("issues", []) or []
    issue = next((i for i in issues if i.get("id") == step.get("issue_id")), None)
    facts = state.get("facts", {})
    relevant = (
        facts.get("relevant_facts")
        or facts.get("facts", {}).get("relevant_facts")
        or []
    )
    fact_bits = "; ".join((f.get("text") or "")[:160] for f in relevant[:3])
    base = (
        issue.get("question") if issue else step.get("description") or "consulta legal"
    )
    return f"{base} | capa: {step.get('layer')} | hechos: {fact_bits}".strip()


# Shared toolset for the research agent.
RESEARCH_TOOLS = get_tools(["pgvector_inspector", "web_browser"])
QUALIFICATION_FEWSHOTS = [
    (
        "human",
        "El cliente describe: 'Me despidieron sin causa justificada y no me pagaron finiquito. Trabajo en CDMX.'",
    ),
    (
        "ai",
        '{"is_legal_matter": true, "confidence": 0.88, "recommended_path": "legal_action", "rationale": "Conflicto laboral con posible indemnización."}',
    ),
]
JURISDICTION_FEWSHOTS = [
    (
        "human",
        "El cliente describe: 'Demanda por despido injustificado en un despacho en CDMX, patrón privado.'",
    ),
    (
        "ai",
        '{"jurisdiction_hypotheses":[{"level":"local","label":"cdmx","confidence":0.82}],"chosen_jurisdictions":["cdmx"],"area_of_law":{"primary":"laboral","secondary":[],"confidence":0.84,"rationale":"Despido en CDMX con patrón privado"}}',
    ),
]

DEFAULT_MAX_SEARCH_STEPS = 4

trace_id_var: ContextVar[Optional[str]] = ContextVar("research_trace_id", default=None)


def _ensure_trace_id(state: ResearchState) -> str:
    existing = trace_id_var.get()
    if existing:
        return existing
    provided = state.get("trace_id")
    if provided:
        trace_id_var.set(provided)
        return provided
    new_id = uuid.uuid4().hex
    trace_id_var.set(new_id)
    return new_id


@contextmanager
def trace_span(name: str, **attrs):
    trace_id = _ensure_trace_id(attrs.get("state", {}) if "state" in attrs else {})
    start = time.time()
    base = {"trace_id": trace_id, "span": name}
    base.update({k: v for k, v in attrs.items() if k != "state"})
    logger.info("trace.start", extra=base)
    try:
        yield base
        duration = round((time.time() - start) * 1000, 2)
        logger.info("trace.end", extra={**base, "duration_ms": duration})
    except Exception as exc:  # pragma: no cover - tracing safety
        logger.exception("trace.error", extra={**base, "error": str(exc)})
        raise


def trace_node(
    name: str,
) -> Callable[
    [Callable[[ResearchState], ResearchState]], Callable[[ResearchState], ResearchState]
]:
    def decorator(fn: Callable[[ResearchState], ResearchState]):
        def wrapped(state: ResearchState) -> ResearchState:
            _ensure_trace_id(state)
            with trace_span(
                f"node.{name}",
                node=name,
                status=state.get("status"),
                issues=len(state.get("issues", []) or []),
                queries=len(state.get("queries", []) or []),
            ):
                try:
                    result = fn(state)
                    return result
                except Exception as exc:  # pragma: no cover - runtime safety
                    logger.exception("node.error", extra={"node": name})
                    return {"status": ResearchStatus.ERROR, "error": str(exc)}

        return wrapped

    return decorator


# ---------- Nodes ----------


def normalize_intake(state: ResearchState) -> ResearchState:
    text = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            text = msg.content
            break
    return {
        "intake": {
            "source_type": "chat",
            "raw_text": text,
            "language": "es",
        },
        "status": ResearchStatus.INTAKE,
    }


def classify_matter(state: ResearchState) -> ResearchState:
    intake = state.get("intake", {})
    text = intake.get("raw_text", "")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Eres un abogado mexicano senior. Evalúa si el asunto descrito es jurídico. "
                "Responde en JSON con: is_legal_matter (bool), confidence (0-1), "
                "recommended_path (no_legal_action|extrajudicial_resolution|legal_action|mixed), rationale (string).",
            ),
            *QUALIFICATION_FEWSHOTS,
            ("user", "{text}"),
        ]
    )
    def fallback(exc: Exception) -> Dict[str, Any]:
        return QualificationModel(
            is_legal_matter=True,
            confidence=0.5,
            recommended_path="legal_action",
            rationale=f"fallback: {exc}",
        ).dict()
    data = _structured_call(
        prompt,
        QualificationModel,
        {"text": text},
        fallback,
        temperature=0.0,
        max_tokens=200,
    )
    return {
        "qualification": data,
        "status": ResearchStatus.QUALIFIED,
        "messages": [
            AIMessage(
                content=f"Clasificación preliminar: {data.get('recommended_path', 'legal_action')} (confianza {data.get('confidence', 0):.2f})."
            )
        ],
    }


def jurisdiction_and_area_classifier(state: ResearchState) -> ResearchState:
    intake = state.get("intake", {})
    text = intake.get("raw_text", "")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Eres un abogado mexicano. Sugiere jurisdicciones y área de derecho. "
                "Recuerda que en México existen competencias federales, locales (estatales/CDMX) y municipales, a veces concurrentes. "
                "Devuelve JSON con: jurisdiction_hypotheses [{level,label,confidence,basis}], chosen_jurisdictions [strings], "
                "area_of_law {primary,secondary,confidence,rationale}.",
            ),
            *JURISDICTION_FEWSHOTS,
            ("user", "{text}"),
        ]
    )
    def fallback(exc: Exception) -> Dict[str, Any]:
        return JurisdictionAreaModel(
            jurisdiction_hypotheses=[
                JurisdictionHypothesisModel(
                    level="federal", label="federal - MX", confidence=0.5, basis=str(exc)
                )
            ],
            chosen_jurisdictions=["federal"],
            area_of_law=AreaOfLawModel(
                primary="desconocido", secondary=[], confidence=0.5, rationale="fallback"
            ),
        ).dict()
    data = _structured_call(
        prompt,
        JurisdictionAreaModel,
        {"text": text},
        fallback,
        temperature=0.0,
        max_tokens=300,
    )
    return {**data, "status": ResearchStatus.CLASSIFIED}


def fact_extractor(state: ResearchState) -> ResearchState:
    intake = state.get("intake", {})
    text = intake.get("raw_text", "")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Extrae partes y hechos relevantes e irrelevantes. Devuelve JSON con: parties [{id, role, name}], "
                "facts {relevant_facts:[{id,text,relevance_reason,date?,parties?,tags?}], irrelevant_facts:[...]}.",
            ),
            ("user", "{text}"),
        ]
    )

    def _fallback(exc: Exception) -> Dict[str, Any]:
        return FactExtractionModel(
            parties=[PartyModel(id="P1", role="client", name="Cliente")],
            facts=FactsModel(
                relevant_facts=[
                    FactItemModel(
                        id="F1",
                        text="Hecho principal (fallback)",
                        relevance="relevant",
                        relevance_reason=f"Fallback: {exc}",
                    )
                ],
                irrelevant_facts=[],
            ),
        ).dict()

    data = _structured_call(
        prompt,
        FactExtractionModel,
        {"text": text},
        _fallback,
        temperature=0.0,
        max_tokens=500,
    )
    return {
        "parties": data.get("parties", []),
        "facts": data.get("facts", {}),
        "status": ResearchStatus.FACTS_STRUCTURED,
    }


def issue_generator(state: ResearchState) -> ResearchState:
    facts = state.get("facts", {})
    area = state.get("area_of_law", {}).get("primary", "desconocido")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                'Genera 1-4 cuestiones jurídicas priorizadas en español. Devuelve JSON issues [{id,question,priority (high|medium|low),area,status=\\"pending\\"}].',
            ),
            ("user", "Área: {area}\nHechos: {facts}"),
        ]
    )

    def _fallback(exc: Exception) -> Dict[str, Any]:
        return IssuesModel(
            issues=[
                IssueModel(
                    id="I1",
                    question="¿El acto es legal conforme a la ley aplicable?",
                    priority="high",
                    area=area,
                    status="pending",
                )
            ]
        ).dict()

    data = _structured_call(
        prompt,
        IssuesModel,
        {"area": area, "facts": str(facts)},
        _fallback,
        temperature=0.0,
        max_tokens=300,
    )
    issues = data.get("issues", []) if isinstance(data, dict) else []
    return {"issues": issues}


def research_plan_builder(state: ResearchState) -> ResearchState:
    issues = state.get("issues", [])
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Para cada issue genera pasos de investigación respetando jerarquía MX: constitution, treaties (human rights), laws/codes, reglamentos, "
                'NOMs/administrative norms, jurisprudence, doctrine/custom. Devuelve research_plan [{id,issue_id,layer,description,status=\\"pending\\",query_ids:[],top_k?}].',
            ),
            ("user", "{issues}"),
        ]
    )

    def _fallback(exc: Exception) -> Dict[str, Any]:
        plan: List[ResearchStep] = []
        for issue in issues:
            plan.append(
                {
                    "id": f"{issue.get('id', 'I')}-law",
                    "issue_id": issue.get("id"),
                    "layer": "law",
                    "description": "Revisar leyes/códigos aplicables (fallback).",
                    "status": "pending",
                    "query_ids": [],
                    "top_k": 5,
                }
            )
        return {"research_plan": plan}

    data = _structured_call(
        prompt,
        ResearchPlanModel,
        {"issues": str(issues)},
        _fallback,
        temperature=0.0,
        max_tokens=600,
    )
    plan = data.get("research_plan", []) if isinstance(data, dict) else []
    if not plan:
        plan = _fallback(Exception("empty plan"))["research_plan"]
    return {"research_plan": plan, "status": ResearchStatus.PLAN_BUILT}


def run_next_search_step(state: ResearchState) -> ResearchState:
    plan = state.get("research_plan", []) or []
    queries = state.get("queries", []) or []
    pending_idx = next(
        (i for i, s in enumerate(plan) if s.get("status") == "pending"), None
    )
    if pending_idx is None:
        return {}

    step = plan[pending_idx]
    search_runs = state.get("search_runs", 0) + 1
    qid = f"Q-{len(queries) + 1}"
    chosen_jurisdictions = state.get("chosen_jurisdictions", [])
    firm_id = state.get("firm_id")
    query_text = _build_query_text(step, state)
    top_k = step.get("top_k") or 5

    results: List[Dict[str, Any]] = []
    try:
        with trace_span(
            "tool.pgvector_inspector",
            query_preview=query_text[:120],
            top_k=top_k,
            jurisdictions=",".join(chosen_jurisdictions)
            if chosen_jurisdictions
            else "",
            firm_id=firm_id,
        ):
            tool_payload = pgvector_inspector_tool.invoke(
                {
                    "query": query_text,
                    "top_k": top_k,
                    "jurisdictions": chosen_jurisdictions or None,
                    "firm_id": firm_id,
                }
            )
            tool_rows = (
                tool_payload.get("results", [])
                if isinstance(tool_payload, dict)
                else []
            )
            for row in tool_rows:
                metadata = row.get("metadata") or {}
                results.append(
                    {
                        "doc_id": row.get("doc_id"),
                        "title": metadata.get("title") or "",
                        "citation": metadata.get("citation")
                        or metadata.get("chunk_id")
                        or row.get("chunk_id", ""),
                        "snippet": (row.get("content") or "")[:400],
                        "score": float(row.get("distance", 0.0)),
                        "norm_layer": step.get("layer", ""),
                    }
                )
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.warning("pgvector_inspector error: %s", exc)
        results.append(
            {
                "doc_id": "DOC-1",
                "title": "Artículo relevante",
                "citation": "Art. X",
                "snippet": f"Fallback: {exc}",
                "score": 0.5,
                "norm_layer": step.get("layer", ""),
            }
        )

    if not results:
        results.append(
            {
                "doc_id": "DOC-1",
                "title": "Artículo relevante",
                "citation": "Art. X",
                "snippet": "Contenido placeholder...",
                "score": 0.5,
                "norm_layer": step.get("layer", ""),
            }
        )

    queries.append(
        {
            "id": qid,
            "issue_id": step.get("issue_id"),
            "layer": step.get("layer"),
            "query": query_text,
            "filters": {"jurisdiction": ",".join(chosen_jurisdictions)},
            "top_k": top_k,
            "results": results,
        }
    )
    plan[pending_idx]["status"] = "done"
    return {"research_plan": plan, "queries": queries, "search_runs": search_runs}


def synthesize_briefing(state: ResearchState) -> ResearchState:
    issues = state.get("issues", [])
    queries = state.get("queries", [])
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Redacta un briefing jurídico en español. Ordena citas por peso normativo (CPEUM/treaties > leyes/códigos > reglamentos > NOMs > jurisprudencia > doctrina/custom). "
                "Devuelve JSON briefing: {overview, legal_characterization, recommended_strategy, issue_answers:[{issue_id, answer, citations:[{doc_id,citation,snippet,norm_layer}]}], open_questions}.",
            ),
            ("user", "Issues: {issues}\nQueries: {queries}"),
        ]
    )

    def _fallback(exc: Exception) -> Dict[str, Any]:
        return BriefingModel(
            overview="Resumen breve del asunto (fallback).",
            legal_characterization="Caracterización legal fallback.",
            recommended_strategy="Estrategia preliminar fallback.",
            issue_answers=[
                IssueAnswerModel(issue_id=issue.get("id"), answer="Respuesta fallback.")
                for issue in issues
            ],
            open_questions=["Confirme fechas y partes clave."],
        ).dict()

    data = _structured_call(
        prompt,
        BriefingModel,
        {"issues": str(issues), "queries": str(queries)},
        _fallback,
        temperature=0.1,
        max_tokens=800,
    )
    return {"briefing": data, "status": ResearchStatus.ANSWERED}


# ---------- Graph ----------


def _should_continue_search(state: ResearchState) -> str:
    plan = state.get("research_plan", []) or []
    max_steps = state.get("max_search_steps") or DEFAULT_MAX_SEARCH_STEPS
    runs = state.get("search_runs", 0)
    if any(s.get("status") == "pending" for s in plan) and runs < max_steps:
        return "run_next_search_step"
    return "synthesize_briefing"


SYNTHETIC_EVAL_SCENARIOS = [
    {
        "prompt": "Cliente indica despido injustificado en CDMX sin pago de prestaciones.",
        "expect_jurisdiction": "cdmx",
        "expect_area_primary": "laboral",
    },
    {
        "prompt": "Socio pregunta si puede registrar marca en EE.UU. y México.",
        "expect_jurisdiction": "federal",
        "expect_area_primary": "propiedad intelectual",
    },
]


def get_synthetic_eval_scenarios() -> List[Dict[str, str]]:
    return SYNTHETIC_EVAL_SCENARIOS.copy()


def build_research_graph() -> StateGraph:
    builder = StateGraph(ResearchState)
    builder.add_node(
        "normalize_intake", trace_node("normalize_intake")(normalize_intake)
    )
    builder.add_node("classify_matter", trace_node("classify_matter")(classify_matter))
    builder.add_node(
        "jurisdiction_and_area_classifier",
        trace_node("jurisdiction_and_area_classifier")(
            jurisdiction_and_area_classifier
        ),
    )
    builder.add_node("fact_extractor", trace_node("fact_extractor")(fact_extractor))
    builder.add_node("issue_generator", trace_node("issue_generator")(issue_generator))
    builder.add_node(
        "research_plan_builder",
        trace_node("research_plan_builder")(research_plan_builder),
    )
    builder.add_node(
        "run_next_search_step", trace_node("run_next_search_step")(run_next_search_step)
    )
    builder.add_node(
        "synthesize_briefing", trace_node("synthesize_briefing")(synthesize_briefing)
    )

    builder.add_edge(START, "normalize_intake")
    builder.add_edge("normalize_intake", "classify_matter")
    builder.add_edge("classify_matter", "jurisdiction_and_area_classifier")
    builder.add_edge("jurisdiction_and_area_classifier", "fact_extractor")
    builder.add_edge("fact_extractor", "issue_generator")
    builder.add_edge("issue_generator", "research_plan_builder")

    builder.add_edge("research_plan_builder", "run_next_search_step")
    builder.add_conditional_edges(
        "run_next_search_step",
        _should_continue_search,
        {
            "run_next_search_step": "run_next_search_step",
            "synthesize_briefing": "synthesize_briefing",
        },
    )
    builder.add_edge("synthesize_briefing", END)
    return builder


def demo_research_run(prompt: str) -> ResearchState:
    graph = build_research_graph().compile()
    initial_state: ResearchState = {
        "messages": [HumanMessage(content=prompt)],
        "trace_id": uuid.uuid4().hex,
    }
    final_state = graph.invoke(initial_state)
    return final_state


def run_research(
    prompt: str,
    *,
    firm_id: Optional[str] = None,
    user_id: Optional[str] = None,
    max_search_steps: Optional[int] = None,
    trace_id: Optional[str] = None,
) -> ResearchState:
    """
    Convenience entrypoint to run the research graph with optional tenant/user and step cap.
    """
    graph = build_research_graph().compile()
    initial_state: ResearchState = {
        "messages": [HumanMessage(content=prompt)],
        "trace_id": trace_id or uuid.uuid4().hex,
        "firm_id": firm_id,
        "user_id": user_id,
    }
    if max_search_steps:
        initial_state["max_search_steps"] = max_search_steps
    return graph.invoke(initial_state)


def get_research_tools():
    """Return the tools commonly used by the research agent."""
    return RESEARCH_TOOLS
