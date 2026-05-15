"""
API route handlers for Phase 10 Product Runtime.

Routes:
    POST /documents/upload   — upload a document and queue a processing job
    GET  /documents          — list the caller's documents
    GET  /documents/{doc_id} — get a single document (tenant-scoped)
    GET  /jobs               — list the caller's jobs
    GET  /jobs/{job_id}      — get a single job (tenant-scoped)
    POST /queries            — run a knowledge query over the document space
    POST /actions            — execute a legal action workflow (audited)
    GET  /audit              — retrieve the caller's audit trail
"""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.actions.action_engine import ActionEngine
from src.actions.action_schema import ActionRequest as EngineActionRequest
from src.api.deps import get_audit, get_runner, get_storage, require_user
from src.api.models import (
    ActionRequest,
    ActionResponse,
    DocumentResponse,
    EvidenceRefOut,
    JobResponse,
    QueryRequest,
    QueryResponse,
    UploadRequest,
    UploadResponse,
)
from src.graphrag.evidence_bundle import EvidenceBundle, empty_bundle
from src.graphrag.reasoning import ReasoningEngine
from src.runtime.audit import AuditLayer
from src.runtime.job_runner import JobRunner
from src.runtime.storage import StorageLayer

router = APIRouter()

_action_engine = ActionEngine()
_reasoning_engine = ReasoningEngine()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc_response(doc) -> DocumentResponse:
    return DocumentResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        status=doc.status,
        created_at=doc.created_at,
        metadata=doc.metadata,
    )


def _job_response(job) -> JobResponse:
    return JobResponse(
        job_id=job.job_id,
        doc_id=job.doc_id,
        status=job.status,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error=job.error,
        checkpoint=job.checkpoint,
    )


def _get_bundles(
    request: Request,
    user_id: str,
    document_ids: List[str],
) -> List[EvidenceBundle]:
    """
    Build evidence bundles for a query or action.

    If app.state.bundle_provider is set (injected in tests), delegate to it.
    Otherwise returns a stub empty bundle — real pipeline integration
    (loading indexed chunks, running retrieval) is a post-Phase-10 concern.
    """
    provider = getattr(request.app.state, "bundle_provider", None)
    if provider is not None:
        return provider(user_id, document_ids)
    qid = "q_" + str(uuid.uuid4())[:8]
    return [empty_bundle(qid, "Document index not yet built for this document space.")]


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@router.post(
    "/documents/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def upload_document(
    body: UploadRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> UploadResponse:
    storage: StorageLayer = get_storage(request)
    runner: JobRunner = get_runner(request)
    doc = storage.create_document(user_id, body.filename, dict(body.metadata))
    job = runner.submit(user_id, doc.doc_id)
    return UploadResponse(doc_id=doc.doc_id, job_id=job.job_id)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@router.get("/documents", response_model=List[DocumentResponse])
def list_documents(
    request: Request,
    user_id: str = Depends(require_user),
) -> List[DocumentResponse]:
    storage: StorageLayer = get_storage(request)
    return [_doc_response(d) for d in storage.list_documents(user_id)]


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc_id: str,
    request: Request,
    user_id: str = Depends(require_user),
) -> DocumentResponse:
    storage: StorageLayer = get_storage(request)
    doc = storage.get_document(user_id, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return _doc_response(doc)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(
    request: Request,
    user_id: str = Depends(require_user),
) -> List[JobResponse]:
    storage: StorageLayer = get_storage(request)
    return [_job_response(j) for j in storage.list_jobs(user_id)]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    request: Request,
    user_id: str = Depends(require_user),
) -> JobResponse:
    storage: StorageLayer = get_storage(request)
    job = storage.get_job(user_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _job_response(job)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


@router.post("/queries", response_model=QueryResponse)
def run_query(
    body: QueryRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> QueryResponse:
    bundles = _get_bundles(request, user_id, body.document_ids)
    query_id = body.query_id or ("q_" + str(uuid.uuid4())[:8])
    primary = bundles[0] if bundles else empty_bundle(query_id, "No documents.")
    result = _reasoning_engine.reason(body.query, primary, query_id=query_id)

    return QueryResponse(
        query_id=result.query_id,
        query=result.query,
        intent=result.intent,
        support_status=result.support_status,
        confidence=result.confidence,
        answer=result.answer,
        citations=result.citations,
        evidence_excerpts=result.evidence_excerpts,
        is_refusal=result.is_refusal,
        warnings=result.warnings,
    )


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


@router.post("/actions", response_model=ActionResponse)
def run_action(
    body: ActionRequest,
    request: Request,
    user_id: str = Depends(require_user),
    audit: AuditLayer = Depends(get_audit),
) -> ActionResponse:
    request_id = body.request_id or ("req_" + str(uuid.uuid4())[:8])

    try:
        engine_req = EngineActionRequest(
            action_type=body.action_type,
            query=body.query,
            document_ids=body.document_ids,
            parameters=body.parameters,
            request_id=request_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    bundles = _get_bundles(request, user_id, body.document_ids)
    result = _action_engine.execute(engine_req, bundles)
    audit_record = audit.log_action_result(user_id, result)

    return ActionResponse(
        request_id=result.request_id,
        action_type=result.action_type,
        status=result.status,
        output=result.output,
        citations=result.citations,
        evidence_refs=[
            EvidenceRefOut(
                chunk_id=r.chunk_id,
                citation=r.citation,
                excerpt=r.excerpt,
                confidence=r.confidence,
                is_generated=r.is_generated,
            )
            for r in result.evidence_refs
        ],
        assumptions=result.assumptions,
        missing_evidence=result.missing_evidence,
        warnings=result.warnings,
        is_generated=result.is_generated,
        refusal_reason=result.refusal_reason,
        audit_id=audit_record.audit_id,
    )


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


@router.get("/audit")
def get_audit_trail(
    request: Request,
    user_id: str = Depends(require_user),
    audit: AuditLayer = Depends(get_audit),
):
    records = audit.get_trail(user_id)
    return [
        {
            "audit_id": r.audit_id,
            "request_id": r.request_id,
            "action_type": r.action_type,
            "status": r.status,
            "output_hash": r.output_hash,
            "created_at": r.created_at,
        }
        for r in records
    ]
