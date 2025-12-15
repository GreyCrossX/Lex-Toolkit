from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


class SearchRequest(BaseModel):
    query: Optional[str] = None
    embedding: Optional[List[float]] = Field(default=None)
    limit: int = Field(default=5, ge=1, le=100)
    doc_ids: Optional[List[str]] = None
    jurisdictions: Optional[List[str]] = None
    sections: Optional[List[str]] = None
    # Optional maximum distance filter (L2) if the caller wants to prune results.
    max_distance: Optional[float] = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def ensure_query_or_embedding(self) -> "SearchRequest":
        query_val = (self.query or "").strip()
        if self.embedding is not None and len(self.embedding) == 0:
            raise ValueError("Embedding no puede estar vacío.")
        if not query_val and self.embedding is None:
            raise ValueError("Provide either query text or embedding.")
        if query_val:
            self.query = query_val
        return self


class SearchResult(BaseModel):
    chunk_id: str
    doc_id: str
    section: Optional[str]
    jurisdiction: Optional[str]
    metadata: Dict[str, Any] = {}
    content: Optional[str]
    distance: float


class SearchResponse(BaseModel):
    results: List[SearchResult]


class QARequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=10)
    doc_ids: Optional[List[str]] = None
    jurisdictions: Optional[List[str]] = None
    sections: Optional[List[str]] = None
    max_distance: Optional[float] = Field(default=None, ge=0.0)
    max_tokens: int = Field(default=400, ge=64, le=800)


class QACitation(BaseModel):
    chunk_id: str
    doc_id: str
    section: Optional[str]
    jurisdiction: Optional[str]
    metadata: Dict[str, Any] = {}
    content: Optional[str]
    distance: float


class QAResponse(BaseModel):
    answer: str
    citations: List[QACitation]


class SummaryCitation(BaseModel):
    chunk_id: str
    doc_id: str
    section: Optional[str]
    jurisdiction: Optional[str]
    metadata: Dict[str, Any] = {}
    content: Optional[str]
    distance: Optional[float] = None


class SummaryResponse(BaseModel):
    summary: str
    citations: List[SummaryCitation]
    model: Optional[str] = None
    chunks_used: Optional[int] = None


class SummaryRequest(BaseModel):
    text: Optional[str] = None
    doc_ids: Optional[List[str]] = None
    top_k: int = Field(default=5, ge=1, le=20)
    max_tokens: int = Field(default=400, ge=64, le=800)
    stream: bool = False

    @model_validator(mode="after")
    def ensure_text_or_doc_ids(self) -> "SummaryRequest":
        text_val = (self.text or "").strip()
        doc_ids_val = self.doc_ids or []
        if not text_val and len(doc_ids_val) == 0:
            raise ValueError("Provide either text or doc_ids.")
        if text_val:
            self.text = text_val
        if doc_ids_val:
            self.doc_ids = [d.strip() for d in doc_ids_val if d and d.strip()]
            if len(self.doc_ids or []) == 0:
                raise ValueError("doc_ids cannot be empty if provided.")
        return self


class MultiSummaryRequest(BaseModel):
    texts: Optional[List[str]] = None
    doc_ids: Optional[List[str]] = None
    top_k: int = Field(default=5, ge=1, le=20)
    max_tokens: int = Field(default=400, ge=64, le=800)
    stream: bool = False

    @model_validator(mode="after")
    def ensure_inputs(self) -> "MultiSummaryRequest":
        texts_val = [t.strip() for t in (self.texts or []) if t and t.strip()]
        doc_ids_val = [d.strip() for d in (self.doc_ids or []) if d and d.strip()]
        if len(texts_val) == 0 and len(doc_ids_val) == 0:
            raise ValueError("Provide at least one text or doc_id.")
        if len(texts_val) > 0:
            self.texts = texts_val
        if len(doc_ids_val) > 0:
            self.doc_ids = doc_ids_val
        return self


class SummaryStreamEvent(BaseModel):
    type: Literal["summary_chunk", "citation", "done", "error"]
    data: Optional[Union[str, SummaryCitation, Dict[str, Any]]] = None


class UploadStatus(str, Enum):
    queued = "queued"
    uploading = "uploading"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class UploadResponse(BaseModel):
    job_id: str
    status: UploadStatus
    message: Optional[str] = None
    doc_type: Optional[str] = "statute"


class UploadStatusResponse(BaseModel):
    job_id: str
    filename: str
    status: UploadStatus
    progress: int = Field(default=0, ge=0, le=100)
    message: Optional[str] = None
    error: Optional[str] = None
    doc_ids: List[str] = Field(default_factory=list)
    doc_type: Optional[str] = "statute"


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "user"
    firm_id: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserPublic(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    role: Optional[str]
    firm_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class ResearchRunRequest(BaseModel):
    prompt: str = Field(..., min_length=4, max_length=4000)
    max_search_steps: Optional[int] = Field(default=None, ge=1, le=10)
    trace_id: Optional[str] = Field(default=None, min_length=8, max_length=64)


class ResearchIssue(BaseModel):
    id: str
    question: str
    priority: Optional[str] = None
    area: Optional[str] = None
    status: Optional[str] = None


class ResearchStep(BaseModel):
    id: str
    issue_id: Optional[str] = None
    layer: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    query_ids: List[str] = Field(default_factory=list)
    top_k: Optional[int] = None


class ResearchQueryResult(BaseModel):
    doc_id: Optional[str] = None
    title: Optional[str] = None
    citation: Optional[str] = None
    snippet: Optional[str] = None
    score: Optional[float] = None
    norm_layer: Optional[str] = None


class ResearchQuery(BaseModel):
    id: str
    issue_id: Optional[str] = None
    layer: Optional[str] = None
    query: Optional[str] = None
    filters: Dict[str, str] = Field(default_factory=dict)
    top_k: Optional[int] = None
    results: List[ResearchQueryResult] = Field(default_factory=list)


class ResearchBriefing(BaseModel):
    overview: Optional[str] = None
    legal_characterization: Optional[str] = None
    recommended_strategy: Optional[str] = None
    issue_answers: Optional[List[Dict[str, Any]]] = None
    open_questions: Optional[List[str]] = None


class ResearchRunResponse(BaseModel):
    trace_id: str
    status: str
    issues: List[ResearchIssue] = Field(default_factory=list)
    research_plan: List[ResearchStep] = Field(default_factory=list)
    queries: List[ResearchQuery] = Field(default_factory=list)
    briefing: Optional[ResearchBriefing] = None
    conflict_check: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None


# -------- Drafting --------


class DraftRequirement(BaseModel):
    label: str
    value: str


class DraftRequest(BaseModel):
    doc_type: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Tipo de documento: carta, contrato, demanda, memo.",
    )
    objective: Optional[str] = Field(
        default=None, max_length=4000, description="Propósito del documento."
    )
    audience: Optional[str] = Field(
        default=None, max_length=200, description="Destinatario principal."
    )
    tone: Optional[str] = Field(
        default=None, max_length=100, description="Tono deseado (formal, directo, etc)."
    )
    language: Optional[str] = Field(default="es", max_length=5)
    context: Optional[str] = Field(
        default=None, max_length=6000, description="Hechos clave o instrucciones."
    )
    facts: List[str] = Field(
        default_factory=list, description="Lista de hechos relevantes."
    )
    requirements: List[DraftRequirement] = Field(
        default_factory=list,
        description="Requisitos específicos o cláusulas obligatorias.",
    )
    research_trace_id: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=64,
        description="Trace previo de investigación.",
    )
    research_summary: Optional[str] = Field(
        default=None,
        max_length=4000,
        description="Resumen breve de investigación/estrategia.",
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="Límites: jurisdicción, extensión máxima, exclusiones.",
    )


class DraftSection(BaseModel):
    title: str
    content: str


class DraftResponse(BaseModel):
    trace_id: str
    status: str
    doc_type: str
    draft: str
    sections: List[DraftSection] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    errors: Optional[List[str]] = None


# -------- Review --------


class ReviewSection(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class ReviewFinding(BaseModel):
    section: Optional[str] = None
    location: Optional[str] = None
    issue: str
    severity: str


class ReviewIssue(BaseModel):
    category: str
    description: str
    severity: str
    section: Optional[str] = None
    location: Optional[str] = None
    priority: Optional[str] = None


class ReviewSuggestion(BaseModel):
    section: Optional[str] = None
    location: Optional[str] = None
    suggestion: str
    rationale: Optional[str] = None


class ReviewRequest(BaseModel):
    doc_type: str = Field(..., min_length=3, max_length=64)
    objective: Optional[str] = Field(default=None, max_length=4000)
    audience: Optional[str] = Field(default=None, max_length=400)
    guidelines: Optional[str] = Field(default=None, max_length=4000)
    jurisdiction: Optional[str] = Field(default=None, max_length=200)
    constraints: List[str] = Field(default_factory=list)
    text: Optional[str] = Field(default=None, max_length=12000)
    sections: List[ReviewSection] = Field(default_factory=list)
    research_trace_id: Optional[str] = Field(default=None, min_length=8, max_length=64)
    research_summary: Optional[str] = Field(default=None, max_length=4000)


class ReviewResponse(BaseModel):
    trace_id: str
    status: str
    doc_type: str
    structural_findings: List[ReviewFinding] = Field(default_factory=list)
    issues: List[ReviewIssue] = Field(default_factory=list)
    suggestions: List[ReviewSuggestion] = Field(default_factory=list)
    qa_notes: List[str] = Field(default_factory=list)
    residual_risks: List[str] = Field(default_factory=list)
    summary: Optional[Dict[str, Any]] = None
    conflict_check: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None


# DB-facing schemas for type safety when returning raw records.
class UserRecord(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    role: Optional[str] = "user"
    firm_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IngestionJobRecord(BaseModel):
    job_id: str
    filename: str
    content_type: Optional[str] = None
    doc_type: Optional[str] = "statute"
    status: str
    progress: int
    message: Optional[str] = None
    error: Optional[str] = None
    doc_ids: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LegalChunkRecord(BaseModel):
    chunk_id: str
    doc_id: str
    section: Optional[str] = None
    jurisdiction: Optional[str] = None
    tokenizer_model: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    content: Optional[str] = None
    embedding: Optional[List[float]] = None
