from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class LegalChunk:
    chunk_id: str
    doc_id: str
    section: Optional[str]
    jurisdiction: Optional[str]
    tokenizer_model: Optional[str]
    metadata: Dict[str, Any]
    content: Optional[str]
    embedding: Optional[List[float]] = None
