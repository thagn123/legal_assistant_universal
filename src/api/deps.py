"""
FastAPI dependency providers for the API.

All stateful objects (storage, auth, audit, runner) are stored on app.state
and retrieved here so they are shared across requests.
"""

from __future__ import annotations

import os

from fastapi import Header, HTTPException, Request, status

from src.runtime.audit import AuditLayer
from src.runtime.auth import AuthLayer
from src.runtime.job_runner import JobRunner
from src.runtime.storage import StorageLayer

_ADMIN_KEY_ENV = "ADMIN_API_KEY"
_ADMIN_KEY_DEFAULT = "lexai-admin-secret"
_DEFAULT_USER_ID = "demo_user_001"
_DEMO_AUTH_ENV = "LEXAI_DEMO_AUTH"


def get_storage(request: Request) -> StorageLayer:
    return request.app.state.storage


def get_auth(request: Request) -> AuthLayer:
    return request.app.state.auth


def get_audit(request: Request) -> AuditLayer:
    return request.app.state.audit


def get_runner(request: Request) -> JobRunner:
    return request.app.state.runner


def _demo_auth_enabled() -> bool:
    value = os.environ.get(_DEMO_AUTH_ENV, "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def require_user(
    request: Request,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
) -> str:
    """Resolve the caller identity.

    API clients send X-API-Key; the key is verified and mapped to the stored
    tenant user_id. The browser demo may send a stable X-User-ID directly. If
    neither header is present, fall back to a demo user for low-risk flows such
    as metadata-only upload.
    """
    api_key = (x_api_key or "").strip()
    if api_key:
        user_id = get_auth(request).verify(api_key)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key.",
            )
        return user_id

    uid = (x_user_id or "").strip()
    if uid:
        return uid

    if _demo_auth_enabled():
        return _DEFAULT_USER_ID

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Missing X-API-Key or X-User-ID header.",
    )


def require_explicit_user(
    request: Request,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
) -> str:
    """Resolve identity, requiring the caller to send an auth/user header."""
    if not (x_api_key or x_user_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing X-API-Key or X-User-ID header.",
        )
    return require_user(request, x_api_key=x_api_key, x_user_id=x_user_id)


def require_admin(
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> None:
    """Validate the admin API key. Raises 403 if wrong or missing."""
    expected = os.environ.get(_ADMIN_KEY_ENV, _ADMIN_KEY_DEFAULT)
    if not x_admin_key or x_admin_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin key.",
        )
