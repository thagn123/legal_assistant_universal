"""
Pydantic request/response models for the Phase 10 API.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


class UploadRequest(BaseModel):
    filename: str
    content_base64: str = ""
    metadata: Dict[str, str] = Field(default_factory=dict)


class UploadResponse(BaseModel):
    doc_id: str
    job_id: str
    status: str = "queued"


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    job_id: str
    doc_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    checkpoint: Optional[dict] = None


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    status: str
    created_at: str
    metadata: dict


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    query: str
    document_ids: List[str] = Field(default_factory=list)
    query_id: str = ""


class QueryResponse(BaseModel):
    query_id: str
    query: str
    intent: str
    support_status: str
    confidence: float
    answer: str
    citations: List[str]
    evidence_excerpts: List[str]
    is_refusal: bool
    warnings: List[str]


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------


class ActionRequest(BaseModel):
    action_type: str
    query: str
    document_ids: List[str] = Field(default_factory=list)
    parameters: Dict[str, str] = Field(default_factory=dict)
    request_id: str = ""


class EvidenceRefOut(BaseModel):
    chunk_id: str
    citation: str
    excerpt: str
    confidence: float
    is_generated: bool


class ActionResponse(BaseModel):
    request_id: str
    action_type: str
    status: str
    output: str
    citations: List[str]
    evidence_refs: List[EvidenceRefOut]
    assumptions: List[str]
    missing_evidence: List[str]
    warnings: List[str]
    is_generated: bool
    refusal_reason: str
    audit_id: str
