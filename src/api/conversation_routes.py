"""
Conversation history routes.

Persists full chat sessions to SQLite so conversations survive browser clears
and can be used later as behavior/context signals.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.api.deps import require_user
from src.runtime.storage import StorageLayer

conversation_router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationTurn(BaseModel):
    role: str
    content: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    situation: Optional[str] = None


class ConversationIn(BaseModel):
    id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., max_length=200)
    domain: Optional[str] = None
    turns: List[ConversationTurn] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationOut(BaseModel):
    id: str
    title: str
    domain: Optional[str]
    turns: List[Dict[str, Any]]
    createdAt: Optional[str] = None
    lastActive: Optional[str] = None
    turnCount: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationListOut(BaseModel):
    items: List[ConversationOut]
    total: int


@conversation_router.post("", response_model=ConversationOut, status_code=201)
def save_conversation(
    body: ConversationIn,
    request: Request,
    user_id: str = Depends(require_user),
) -> ConversationOut:
    """Create or update a conversation session."""
    storage: StorageLayer = request.app.state.storage
    turns = [turn.model_dump(exclude_none=True) for turn in body.turns]
    storage.save_conversation_session(
        user_id=user_id,
        session_id=body.id,
        title=body.title,
        domain=body.domain,
        turns=turns,
        metadata=body.metadata,
    )
    saved = storage.get_conversation_session(user_id, body.id) or {}
    return _conversation_out(saved)


@conversation_router.get("", response_model=ConversationListOut)
def list_conversations(
    request: Request,
    user_id: str = Depends(require_user),
    limit: int = Query(50, ge=1, le=200),
) -> ConversationListOut:
    """List recent conversations for the current user."""
    storage: StorageLayer = request.app.state.storage
    items = storage.list_conversation_sessions(user_id, limit=limit)
    return ConversationListOut(items=[_conversation_out(item) for item in items], total=len(items))


@conversation_router.get("/{session_id}", response_model=ConversationOut)
def get_conversation(
    session_id: str,
    request: Request,
    user_id: str = Depends(require_user),
) -> ConversationOut:
    """Return a full conversation by id."""
    storage: StorageLayer = request.app.state.storage
    item = storage.get_conversation_session(user_id, session_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _conversation_out(item)


@conversation_router.delete("/{session_id}", status_code=200)
def delete_conversation(
    session_id: str,
    request: Request,
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """Delete one conversation."""
    storage: StorageLayer = request.app.state.storage
    deleted = storage.delete_conversation_session(user_id, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True, "id": session_id}


@conversation_router.delete("", status_code=200)
def clear_conversations(
    request: Request,
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """Delete all conversations for the current user."""
    storage: StorageLayer = request.app.state.storage
    count = storage.clear_conversation_sessions(user_id)
    return {"cleared": True, "count": count}


def _conversation_out(item: Dict[str, Any]) -> ConversationOut:
    turns = item.get("turns") or []
    return ConversationOut(
        id=item.get("id", ""),
        title=item.get("title", ""),
        domain=item.get("domain"),
        turns=turns if isinstance(turns, list) else [],
        createdAt=item.get("createdAt"),
        lastActive=item.get("lastActive"),
        turnCount=item.get("turnCount", len(turns) if isinstance(turns, list) else 0),
        metadata=item.get("metadata") or {},
    )
