"""
Admin API routes — requires X-Admin-Key header.

Endpoints:
    POST   /admin/documents/upload        — upload 1+ files (multipart)
    GET    /admin/documents               — list all documents
    GET    /admin/documents/{doc_id}      — get single document
    DELETE /admin/documents/{doc_id}      — delete document + chunks
    POST   /admin/documents/{doc_id}/reprocess — re-queue processing job
    GET    /admin/jobs                    — list all jobs
    GET    /admin/stats                   — collection + job counts
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query, status
from pydantic import BaseModel

from src.api.deps import get_runner, get_storage, require_admin
from src.runtime.job_runner import JobRunner
from src.runtime.storage import StorageLayer

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin", tags=["admin"])

_ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".html", ".htm",
    ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp",
}


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class AdminDocResponse(BaseModel):
    doc_id: str
    filename: str
    status: str
    created_at: str
    is_global: bool
    metadata: dict


class AdminJobResponse(BaseModel):
    job_id: str
    doc_id: str
    user_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    checkpoint: Optional[dict] = None


class AdminUploadResult(BaseModel):
    uploaded: List[AdminDocResponse]
    errors: List[dict]


class AdminStatsResponse(BaseModel):
    documents_total: int
    documents_global: int
    jobs_total: int
    jobs_by_status: dict
    mongodb: dict


class AdminSeedResponse(BaseModel):
    templates: int
    official_forms: int = 0
    risks: int
    checklists: int
    legal_cases: int = 0
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc_resp(doc) -> AdminDocResponse:
    return AdminDocResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        status=doc.status,
        created_at=doc.created_at,
        is_global=doc.is_global,
        metadata=doc.metadata,
    )


def _job_resp(job) -> AdminJobResponse:
    return AdminJobResponse(
        job_id=job.job_id,
        doc_id=job.doc_id,
        user_id=job.user_id,
        status=job.status,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error=job.error,
        checkpoint=job.checkpoint,
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@admin_router.post(
    "/documents/upload",
    response_model=AdminUploadResult,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_admin)],
)
async def admin_upload_documents(
    request: Request,
    files: List[UploadFile] = File(...),
) -> AdminUploadResult:
    """Upload one or more legal documents as global (visible to all users)."""
    storage: StorageLayer = get_storage(request)
    runner: JobRunner = get_runner(request)

    uploaded: List[AdminDocResponse] = []
    errors: List[dict] = []

    for upload in files:
        filename = upload.filename or "unnamed"
        ext = Path(filename).suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            errors.append({"filename": filename, "error": f"Unsupported file type: {ext}"})
            continue

        try:
            doc = storage.create_global_document(filename)
            upload_dir = Path("data/uploads") / doc.doc_id
            upload_dir.mkdir(parents=True, exist_ok=True)
            dest = upload_dir / filename
            content = await upload.read()
            dest.write_bytes(content)
            storage.save_file_path(doc.doc_id, str(dest.resolve()))

            # user_id="admin" causes the processor to mark chunks as is_global=True
            job = runner.submit("admin", doc.doc_id)

            logger.info("admin upload: queued doc_id=%s filename=%s job_id=%s", doc.doc_id, filename, job.job_id)
            uploaded.append(_doc_resp(doc))
        except Exception as exc:
            logger.error("admin upload error for %s: %s", filename, exc)
            errors.append({"filename": filename, "error": str(exc)})

    return AdminUploadResult(uploaded=uploaded, errors=errors)


# ---------------------------------------------------------------------------
# Document management
# ---------------------------------------------------------------------------


@admin_router.get(
    "/documents",
    response_model=List[AdminDocResponse],
    dependencies=[Depends(require_admin)],
)
def admin_list_documents(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
) -> List[AdminDocResponse]:
    """List all documents across all users."""
    storage: StorageLayer = get_storage(request)
    docs = storage.get_all_documents(limit=limit, offset=offset, status_filter=status_filter)
    return [_doc_resp(d) for d in docs]


@admin_router.get(
    "/documents/{doc_id}",
    response_model=AdminDocResponse,
    dependencies=[Depends(require_admin)],
)
def admin_get_document(doc_id: str, request: Request) -> AdminDocResponse:
    """Get a single document by ID (no user scope)."""
    storage: StorageLayer = get_storage(request)
    doc = storage.get_document_by_id(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return _doc_resp(doc)


@admin_router.delete(
    "/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def admin_delete_document(doc_id: str, request: Request) -> None:
    """Delete a document, its SQLite records, and its MongoDB chunks."""
    storage: StorageLayer = get_storage(request)

    # Remove MongoDB chunks (non-fatal if MongoDB unavailable)
    vs = getattr(request.app.state, "vector_storage", None)
    if vs is not None:
        deleted_chunks = vs.delete_chunks_by_doc(doc_id)
        logger.info("admin delete: removed %d MongoDB chunks for doc_id=%s", deleted_chunks, doc_id)

    # Remove uploaded files from disk
    upload_dir = Path("data/uploads") / doc_id
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)

    found = storage.delete_document(doc_id)
    if not found:
        raise HTTPException(status_code=404, detail="Document not found.")


@admin_router.post(
    "/documents/{doc_id}/reprocess",
    response_model=AdminJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_admin)],
)
def admin_reprocess_document(doc_id: str, request: Request) -> AdminJobResponse:
    """Re-queue a document for pipeline processing."""
    storage: StorageLayer = get_storage(request)
    runner: JobRunner = get_runner(request)

    doc = storage.get_document_by_id(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = storage.get_file_path(doc_id)
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=400, detail="Source file missing — cannot reprocess.")

    job = runner.submit(doc.user_id, doc_id)

    logger.info("admin reprocess: queued doc_id=%s job_id=%s", doc_id, job.job_id)
    return _job_resp(job)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@admin_router.get(
    "/jobs",
    response_model=List[AdminJobResponse],
    dependencies=[Depends(require_admin)],
)
def admin_list_jobs(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
) -> List[AdminJobResponse]:
    """List all processing jobs across all users."""
    storage: StorageLayer = get_storage(request)
    jobs = storage.list_all_jobs(limit=limit, offset=offset, status_filter=status_filter)
    return [_job_resp(j) for j in jobs]


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@admin_router.post(
    "/seed",
    response_model=AdminSeedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_admin)],
)
def admin_seed_data(request: Request) -> AdminSeedResponse:
    """Seed templates, risks, and checklists into MongoDB. Safe to re-run (idempotent)."""
    vs = getattr(request.app.state, "vector_storage", None)
    if vs is None:
        raise HTTPException(status_code=503, detail="MongoDB not connected — cannot seed.")
    try:
        from src.mongodb.seed_data import seed_all
        counts = seed_all(vs)
        return AdminSeedResponse(
            templates=counts.get("templates", 0),
            official_forms=counts.get("official_forms", 0),
            risks=counts.get("risks", 0),
            checklists=counts.get("checklists", 0),
            legal_cases=counts.get("legal_cases", 0),
            message="Seed completed successfully.",
        )
    except Exception as exc:
        logger.error("admin_seed_data failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@admin_router.get(
    "/stats",
    response_model=AdminStatsResponse,
    dependencies=[Depends(require_admin)],
)
def admin_stats(request: Request) -> AdminStatsResponse:
    """Return counts for admin dashboard."""
    storage: StorageLayer = get_storage(request)

    all_docs = storage.get_all_documents(limit=10000)
    global_docs = [d for d in all_docs if d.is_global]

    all_jobs = storage.list_all_jobs(limit=10000)
    jobs_by_status: dict = {}
    for job in all_jobs:
        jobs_by_status[job.status] = jobs_by_status.get(job.status, 0) + 1

    mongo_stats: dict = {}
    vs = getattr(request.app.state, "vector_storage", None)
    if vs is not None:
        mongo_stats = vs.get_stats()

    return AdminStatsResponse(
        documents_total=len(all_docs),
        documents_global=len(global_docs),
        jobs_total=len(all_jobs),
        jobs_by_status=jobs_by_status,
        mongodb=mongo_stats,
    )
