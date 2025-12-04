from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class IngestionJob:
    job_id: str
    filename: str
    content_type: str
    doc_type: str
    status: str
    progress: int
    message: str
    error: Optional[str]
    doc_ids: List[str]
    created_at: datetime
    updated_at: datetime
