"""
FastAPI application factory for Phase 10 Product Runtime.

Usage:
    from src.api.app import create_app

    # For tests (in-memory):
    app = create_app(db_path=":memory:", bundle_provider=my_provider)

    # For production:
    app = create_app(db_path="./data/lka.db")

    # Run with uvicorn:
    # uvicorn src.api.app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from fastapi import FastAPI

from src.api.routes import router
from src.config import PipelineConfig
from src.runtime.audit import AuditLayer
from src.runtime.auth import AuthLayer
from src.runtime.index_store import DocumentIndexStore
from src.runtime.job_runner import JobRunner, ProcessorFn
from src.runtime.processor import build_document_processor
from src.runtime.storage import StorageLayer


def create_app(
    db_path: str | Path = ":memory:",
    processor: Optional[ProcessorFn] = None,
    bundle_provider: Optional[Callable] = None,
    use_real_pipeline: bool = True,
) -> FastAPI:
    """
    Build and configure the FastAPI application.

    Args:
        db_path:            SQLite database path. Use ':memory:' for tests.
        processor:          Job processor function. If None and use_real_pipeline=True,
                            the real 8-stage pipeline processor is used automatically.
        bundle_provider:    Evidence bundle factory injected for tests.
                            Overrides the IndexStore when set.
                            Signature: (user_id: str, document_ids: list) -> list[EvidenceBundle]
        use_real_pipeline:  Wire real pipeline processor + IndexStore (default True).
                            Set False in tests that supply bundle_provider.
    """
    # Ensure the data directory exists for file-based DBs
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="Legal Knowledge Assistant API",
        description="Evidence-grounded legal document intelligence.",
        version="1.0.0",
    )

    storage = StorageLayer(db_path)
    app.state.storage = storage
    app.state.auth = AuthLayer(storage)
    app.state.audit = AuditLayer(storage)

    # Wire processor: explicit > real pipeline > stub (handled inside JobRunner)
    if processor is None and use_real_pipeline and bundle_provider is None:
        processor = build_document_processor(storage, PipelineConfig())

    app.state.runner = JobRunner(storage, processor=processor, workers=1)

    # bundle_provider overrides IndexStore (used in tests)
    if bundle_provider is not None:
        app.state.bundle_provider = bundle_provider
    elif use_real_pipeline:
        app.state.index_store = DocumentIndexStore()

    app.include_router(router)
    return app


# Default app instance for `uvicorn src.api.app:app`
# Uses a file-based SQLite DB so state survives restarts.
app = create_app(db_path="./data/lka.db")
