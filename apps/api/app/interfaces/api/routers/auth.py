import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.infrastructure.db import connection as db
from app.infrastructure.db import user_repository, refresh_token_repository
from app.infrastructure.security import auth as security
from app.infrastructure.security import rate_limit
from app.interfaces.api.schemas import TokenResponse, UserCreate, UserLogin, UserPublic

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger("auth")
REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    max_age = security.REFRESH_EXPIRE_DAYS * 24 * 60 * 60
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=max_age,
        path="/auth/refresh",
    )


def _set_csrf_cookie(response: Response, token: str) -> None:
    max_age = security.REFRESH_EXPIRE_DAYS * 24 * 60 * 60
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        secure=True,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/auth/refresh")


def _clear_csrf_cookie(response: Response) -> None:
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")


def _extract_refresh_token(
    request: Request, body_token: Optional[str]
) -> Optional[str]:
    return body_token or request.cookies.get(REFRESH_COOKIE_NAME)


def _enforce_rate_limit(
    request: Request, bucket: str, limit: int, window_seconds: int
) -> None:
    ip = request.client.host if request.client else "unknown"
    try:
        rate_limit.enforce(bucket, ip, limit, window_seconds)
    except rate_limit.RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas solicitudes, intenta luego.",
        )


def _require_csrf(request: Request, response: Response) -> None:
    header_token = request.headers.get("x-csrf-token")
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not header_token or not cookie_token or header_token != cookie_token:
        _clear_refresh_cookie(response)
        _clear_csrf_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CSRF token missing or invalid.",
        )


@router.post(
    "/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def register(payload: UserCreate, response: Response) -> TokenResponse:
    db.init_pool()
    existing = user_repository.get_user_by_email(payload.email)
    if existing:
        logger.warning(
            "Registration blocked: email already registered",
            extra={"email": payload.email},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo ya está registrado.",
        )

    try:
        user_id = user_repository.create_user(
            email=payload.email,
            password_hash=security.hash_password(payload.password),
            full_name=payload.full_name,
            role=payload.role or "user",
            firm_id=payload.firm_id,
        )
        logger.info(
            "User registered", extra={"user_id": user_id, "email": payload.email}
        )
    except Exception as exc:  # pragma: no cover - runtime protection
        logger.exception("Registration failed", extra={"email": payload.email})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo registrar el usuario.",
        ) from exc

    access_token = security.create_access_token(
        user_id=user_id, email=payload.email, role=payload.role or "user"
    )
    refresh_token, _ = security.create_refresh_token(user_id)
    _set_refresh_cookie(response, refresh_token)
    _set_csrf_cookie(response, secrets.token_urlsafe(24))
    return TokenResponse(
        access_token=access_token, refresh_token=None, token_type="bearer"
    )


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, response: Response, request: Request) -> TokenResponse:
    _enforce_rate_limit(request, bucket="login", limit=5, window_seconds=60)
    db.init_pool()
    user = user_repository.get_user_by_email(payload.email)
    if not user or not security.verify_password(payload.password, user.password_hash):
        logger.warning(
            "Login failed: invalid credentials", extra={"email": payload.email}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas."
        )

    access_token = security.create_access_token(
        user_id=user.user_id, email=user.email, role=user.role
    )
    refresh_token, _ = security.create_refresh_token(user.user_id)
    _set_refresh_cookie(response, refresh_token)
    _set_csrf_cookie(response, secrets.token_urlsafe(24))
    logger.info(
        "Login success",
        extra={
            "user_id": user.user_id,
            "email": user.email,
            "ip": request.client.host if request.client else "unknown",
        },
    )
    return TokenResponse(
        access_token=access_token, refresh_token=None, token_type="bearer"
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UserPublic:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido."
        )

    payload = security.decode_token(credentials.credentials, expected_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido."
        )

    user = user_repository.get_user_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado."
        )

    return UserPublic(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        firm_id=user.firm_id,
    )


@router.get("/auth/me", response_model=UserPublic)
def me(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current_user


@router.get("/auth/health")
def auth_health() -> dict:
    """
    Lightweight auth liveness check; no token required.
    """
    return {"status": "ok", "auth": "ok"}


@router.get("/auth/jwks")
def auth_jwks() -> dict:
    """
    Return public keys in JWKS format for RS256 verification.
    Only present when RS256 is configured; otherwise returns empty keys.
    """
    keys = security.get_public_jwks()
    return {"keys": keys}


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(
    response: Response,
    request: Request,
    refresh_token: Optional[str] = Body(default=None, embed=True),
) -> TokenResponse:
    _enforce_rate_limit(request, bucket="refresh", limit=30, window_seconds=300)
    _require_csrf(request, response)
    db.init_pool()
    refresh_token_repository.ensure_table()
    token_plain = _extract_refresh_token(request, refresh_token)
    if not token_plain:
        _clear_refresh_cookie(response)
        _clear_csrf_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token requerido."
        )

    result = security.verify_and_rotate_refresh_token(token_plain)
    if result is None:
        logger.warning("Refresh failed: invalid or expired token")
        _clear_refresh_cookie(response)
        _clear_csrf_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado.",
        )

    user = user_repository.get_user_by_id(result["user_id"])
    if not user:
        logger.warning(
            "Refresh failed: user not found", extra={"user_id": result["user_id"]}
        )
        _clear_refresh_cookie(response)
        _clear_csrf_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado."
        )

    access_token = security.create_access_token(
        user_id=user.user_id, email=user.email, role=user.role
    )
    _set_refresh_cookie(response, result["refresh_token"])
    _set_csrf_cookie(response, secrets.token_urlsafe(24))
    logger.info(
        "Refresh success",
        extra={
            "user_id": user.user_id,
            "email": user.email,
            "ip": request.client.host if request.client else "unknown",
        },
    )
    return TokenResponse(
        access_token=access_token, refresh_token=None, token_type="bearer"
    )


@router.post("/auth/logout")
def logout(
    response: Response,
    request: Request,
    refresh_token: Optional[str] = Body(default=None, embed=True),
) -> dict:
    db.init_pool()
    token_plain = _extract_refresh_token(request, refresh_token)
    if token_plain:
        security.revoke_refresh_token(token_plain)
        token_id = token_plain.split(".", 1)[0]
    else:
        token_id = None
    _clear_refresh_cookie(response)
    _clear_csrf_cookie(response)
    logger.info(
        "Logout",
        extra={
            "token_id": token_id,
            "ip": request.client.host if request.client else "unknown",
        },
    )
    return {"status": "ok"}
