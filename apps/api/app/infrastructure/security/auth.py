import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from jose import JWTError, jwk, jwt
from passlib.context import CryptContext

from app.infrastructure.db import refresh_token_repository

JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_PRIVATE_KEY = os.environ.get("JWT_PRIVATE_KEY")
JWT_PRIVATE_KEY_ID = os.environ.get("JWT_PRIVATE_KEY_ID", "current")
JWT_PUBLIC_KEYS_RAW = os.environ.get("JWT_PUBLIC_KEYS")

JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM") or ("RS256" if JWT_PRIVATE_KEY else "HS256")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "legalscraper-api")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "lex-web")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "15"))
REFRESH_EXPIRE_DAYS = int(os.environ.get("JWT_REFRESH_EXPIRE_DAYS", "7"))
JWT_LEEWAY_SECONDS = int(os.environ.get("JWT_LEEWAY_SECONDS", "30"))

if JWT_PRIVATE_KEY:
    _PUBLIC_KEYS: Dict[str, str] = {}
    if JWT_PUBLIC_KEYS_RAW:
        try:
            parsed = json.loads(JWT_PUBLIC_KEYS_RAW)
            if not isinstance(parsed, dict):
                raise ValueError("JWT_PUBLIC_KEYS must be a JSON object mapping kid to public key PEM.")
            _PUBLIC_KEYS = {str(k): v for k, v in parsed.items()}
        except Exception as exc:  # pragma: no cover - parse guard
            raise RuntimeError(f"Failed to parse JWT_PUBLIC_KEYS: {exc}") from exc
else:
    _PUBLIC_KEYS = {}
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET env var is required for HS256 or provide JWT_PRIVATE_KEY for RS256.")
    if len(JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters for HS256.")

# Use pbkdf2_sha256 to sidestep bcrypt backend issues in slim images.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(
    user_id: str, email: str, role: str, expires_minutes: Optional[int] = None
) -> str:
    exp_minutes = expires_minutes or JWT_EXPIRE_MINUTES
    now = _utcnow()
    expire = now + timedelta(minutes=exp_minutes)
    to_encode = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": expire,
        "jti": secrets.token_hex(16),
        "token_type": "access",
    }
    headers = {}
    key = JWT_SECRET
    if JWT_ALGORITHM.startswith("RS"):
        if not JWT_PRIVATE_KEY:
            raise RuntimeError("JWT_PRIVATE_KEY is required for RS256 signing.")
        headers["kid"] = JWT_PRIVATE_KEY_ID
        key = JWT_PRIVATE_KEY
    return jwt.encode(to_encode, key, algorithm=JWT_ALGORITHM, headers=headers)


def decode_token(token: str, expected_type: str = "access") -> Optional[dict]:
    try:
        key = _resolve_decode_key(token)
        if key is None:
            return None
        payload = jwt.decode(
            token,
            key,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "sub", "jti", "token_type"]},
        )
        if payload.get("token_type") != expected_type:
            return None
        return payload
    except JWTError:
        return None


def _hash_refresh_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def create_refresh_token(
    user_id: str, parent_id: Optional[str] = None
) -> Tuple[str, str]:
    """
    Returns (refresh_token_plain, token_id).
    Plain token shape: <token_id>.<secret>
    """
    refresh_token_repository.ensure_table()
    token_id = secrets.token_hex(16)
    secret = secrets.token_urlsafe(32)
    token_plain = f"{token_id}.{secret}"
    expires_at = _utcnow() + timedelta(days=REFRESH_EXPIRE_DAYS)
    refresh_token_repository.create_token(
        token_id, user_id, _hash_refresh_secret(secret), expires_at, parent_id=parent_id
    )
    return token_plain, token_id


def verify_and_rotate_refresh_token(token_plain: str) -> Optional[dict]:
    """
    Validate a refresh token, rotate it, and return payload dict with user_id.
    """
    if "." not in token_plain:
        return None
    token_id, secret = token_plain.split(".", 1)
    record = refresh_token_repository.get_token(token_id)
    now = _utcnow()
    if record is None or record.expires_at <= now:
        return None

    # If token was already revoked, treat as reuse and revoke the whole chain.
    if record.revoked:
        refresh_token_repository.revoke_chain_from(
            record.token_id, reason="reuse-detected", mark_reused=True
        )
        return None

    if _hash_refresh_secret(secret) != record.secret_hash:
        refresh_token_repository.revoke_chain_from(
            record.token_id, reason="secret-mismatch", mark_reused=True
        )
        return None

    refresh_token_repository.touch_token(record.token_id)
    # Rotate: revoke current and create a new one.
    new_token_plain, new_token_id = create_refresh_token(
        record.user_id, parent_id=record.token_id
    )
    refresh_token_repository.revoke_token(
        record.token_id, replaced_by=new_token_id, reason="rotated", mark_reused=False
    )
    return {"user_id": record.user_id, "refresh_token": new_token_plain}


def revoke_refresh_token(token_plain: str) -> None:
    if "." not in token_plain:
        return
    token_id, _ = token_plain.split(".", 1)
    refresh_token_repository.revoke_token(token_id)


def _resolve_decode_key(token: str) -> Optional[str]:
    if JWT_ALGORITHM.startswith("RS"):
        try:
            header = jwt.get_unverified_header(token)
        except JWTError:
            return None
        kid = header.get("kid")
        if kid and kid in _PUBLIC_KEYS:
            return _PUBLIC_KEYS[kid]
        if JWT_PRIVATE_KEY and (kid is None or kid == JWT_PRIVATE_KEY_ID):
            return JWT_PRIVATE_KEY
        return None
    return JWT_SECRET


def get_public_jwks() -> List[dict]:
    """
    Return JWKS entries for configured public keys (RS256). Empty for HS256.
    """
    if not JWT_ALGORITHM.startswith("RS"):
        return []
    keys = []
    for kid, pub in _PUBLIC_KEYS.items():
        keys.append(_pem_to_jwk(pub, kid))
    # Also expose current signing key if not present in the map (helps dev/local).
    if JWT_PRIVATE_KEY and JWT_PRIVATE_KEY_ID not in _PUBLIC_KEYS:
        keys.append(_pem_to_jwk(JWT_PRIVATE_KEY, JWT_PRIVATE_KEY_ID))
    return keys


def _pem_to_jwk(pem: str, kid: str) -> dict:
    jwk_dict = jwk.construct(pem, algorithm="RS256").to_dict()
    jwk_dict.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return jwk_dict
