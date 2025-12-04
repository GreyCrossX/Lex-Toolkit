from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, conlist, model_validator


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
