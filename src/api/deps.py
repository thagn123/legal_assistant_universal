"""
FastAPI dependency providers for the Phase 10 API.

All stateful objects (storage, auth, audit, runner) are stored on
app.state and retrieved here so they are shared across requests.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request, status

from src.runtime.audit import AuditLayer
from src.runtime.auth import AuthLayer
from src.runtime.job_runner import JobRunner
from src.runtime.storage import StorageLayer


def get_storage(request: Request) -> StorageLayer:
    return request.app.state.storage


def get_auth(request: Request) -> AuthLayer:
    return request.app.state.auth


def get_audit(request: Request) -> AuditLayer:
    return request.app.state.audit


def get_runner(request: Request) -> JobRunner:
    return request.app.state.runner


def require_user(
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> str:
    """Dependency that validates the API key and returns the user_id."""
    auth: AuthLayer = get_auth(request)
    try:
        return auth.require(x_api_key)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
