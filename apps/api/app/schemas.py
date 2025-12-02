from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, conlist, model_validator


class SearchRequest(BaseModel):
    query: Optional[str] = None
    embedding: Optional[conlist(float, min_length=1)] = None  # type: ignore[type-arg]
    limit: int = Field(default=5, ge=1, le=100)
    doc_ids: Optional[List[str]] = None
    jurisdictions: Optional[List[str]] = None
    sections: Optional[List[str]] = None
    # Optional maximum distance filter (L2) if the caller wants to prune results.
    max_distance: Optional[float] = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def ensure_query_or_embedding(self) -> "SearchRequest":
        if self.query is None and self.embedding is None:
            raise ValueError("Provide either query text or embedding.")
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
