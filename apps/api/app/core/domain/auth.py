from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RefreshToken:
    token_id: str
    user_id: str
    secret_hash: str
    revoked: bool
    replaced_by: Optional[str]
    parent_id: Optional[str]
    reused: bool
    revoked_reason: Optional[str]
    last_used_at: Optional[datetime]
    expires_at: datetime
    created_at: datetime
