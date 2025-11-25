from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, conlist


class SearchRequest(BaseModel):
    embedding: conlist(float, min_length=1)  # type: ignore[type-arg]
    limit: int = Field(default=5, ge=1, le=100)
    doc_ids: Optional[List[str]] = None
    jurisdictions: Optional[List[str]] = None
    sections: Optional[List[str]] = None
    # Optional maximum distance filter (L2) if the caller wants to prune results.
    max_distance: Optional[float] = Field(default=None, ge=0.0)


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
