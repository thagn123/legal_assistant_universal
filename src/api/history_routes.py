"""
Analysis history routes — Phase 17.

Persists saved analysis results to SQLite so history survives browser clears
and is available across devices (same user_id).

Endpoints:
    POST   /history           — save one analysis item
    GET    /history           — list items (optional ?type=&limit=&offset=)
    DELETE /history/{item_id} — delete one item
    DELETE /history           — clear all items for this user
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.deps import require_user
from src.runtime.storage import StorageLayer

logger = logging.getLogger(__name__)

history_router = APIRouter(prefix="/history", tags=["history"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class HistoryItemIn(BaseModel):
    id: str = Field(..., description="Client-generated unique ID")
    type: str
    title: str = Field(..., max_length=200)
    domain: Optional[str] = None
    summary: str = Field(default="", max_length=500)
    data: Any = None
    savedAt: str = Field(..., description="ISO-8601 timestamp from client")


class HistoryItemOut(BaseModel):
    id: str
    type: str
    title: str
    domain: Optional[str]
    summary: str
    data: Any
    savedAt: str


class HistoryListOut(BaseModel):
    items: List[HistoryItemOut]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_storage(user_id: str = Depends(require_user)) -> tuple[str, StorageLayer]:
    from fastapi import Request
    return user_id


def _storage_from_request(request: Any) -> StorageLayer:
    return request.app.state.storage


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


from fastapi import Request


@history_router.post("", response_model=HistoryItemOut, status_code=201)
def save_history_item(
    body: HistoryItemIn,
    request: Request,
    user_id: str = Depends(require_user),
) -> HistoryItemOut:
    """Persist one analysis result to backend history."""
    storage: StorageLayer = request.app.state.storage
    try:
        data_json = json.dumps(body.data) if body.data is not None else "{}"
    except (TypeError, ValueError):
        data_json = "{}"

    storage.save_analysis_history(
        user_id=user_id,
        item_id=body.id,
        type_=body.type,
        title=body.title,
        domain=body.domain,
        summary=body.summary,
        data_json=data_json,
        saved_at=body.savedAt,
    )
    return HistoryItemOut(
        id=body.id,
        type=body.type,
        title=body.title,
        domain=body.domain,
        summary=body.summary,
        data=body.data,
        savedAt=body.savedAt,
    )


@history_router.get("", response_model=HistoryListOut)
def list_history(
    request: Request,
    user_id: str = Depends(require_user),
    type: Optional[str] = Query(None, description="Filter by analysis type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> HistoryListOut:
    """List saved analysis items, newest first."""
    storage: StorageLayer = request.app.state.storage
    items = storage.list_analysis_history(
        user_id=user_id,
        type_filter=type,
        limit=limit,
        offset=offset,
    )
    return HistoryListOut(
        items=[
            HistoryItemOut(
                id=it["id"],
                type=it["type"],
                title=it["title"],
                domain=it.get("domain"),
                summary=it.get("summary", ""),
                data=it.get("data"),
                savedAt=it["savedAt"],
            )
            for it in items
        ],
        total=len(items),
    )


@history_router.delete("/{item_id}", status_code=200)
def delete_history_item(
    item_id: str,
    request: Request,
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """Delete a single saved analysis item."""
    storage: StorageLayer = request.app.state.storage
    deleted = storage.delete_analysis_history_item(user_id=user_id, item_id=item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"deleted": True, "id": item_id}


@history_router.delete("", status_code=200)
def clear_history(
    request: Request,
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """Delete all analysis history for this user."""
    storage: StorageLayer = request.app.state.storage
    count = storage.clear_analysis_history(user_id=user_id)
    return {"cleared": True, "count": count}
