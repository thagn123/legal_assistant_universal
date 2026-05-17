"""
FastAPI dependency providers for the Phase 10 API.

All stateful objects (storage, auth, audit, runner) are stored on
app.state and retrieved here so they are shared across requests.
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


def get_storage(request: Request) -> StorageLayer:
    return request.app.state.storage


def get_auth(request: Request) -> AuthLayer:
    return request.app.state.auth


def get_audit(request: Request) -> AuditLayer:
    return request.app.state.audit


def get_runner(request: Request) -> JobRunner:
    return request.app.state.runner


_DEFAULT_USER_ID = "demo_user_001"


def require_user(
    x_user_id: str = Header(_DEFAULT_USER_ID, alias="X-User-ID"),
) -> str:
    """Return the caller's user_id from the X-User-ID header.

    Phase 12 uses a simple demo identity — no password/token needed.
    Phase 13 will replace this with JWT auth.
    """
    uid = (x_user_id or "").strip()
    return uid if uid else _DEFAULT_USER_ID


def require_admin(
    x_admin_key: str = Header(None, alias="X-Admin-Key"),
) -> None:
    """Dependency that validates the admin API key. Raises 403 if wrong/missing."""
    expected = os.environ.get(_ADMIN_KEY_ENV, _ADMIN_KEY_DEFAULT)
    if not x_admin_key or x_admin_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin key.",
        )
