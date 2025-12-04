from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    user_id: str
    email: str
    password_hash: str
    full_name: Optional[str]
    role: str
    firm_id: Optional[str]
