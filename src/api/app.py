"""
FastAPI application factory for Phase 10/11 Product Runtime.

Usage:
    from src.api.app import create_app

    # For tests (in-memory, no MongoDB):
    app = create_app(db_path=":memory:", bundle_provider=my_provider)

    # For production:
    app = create_app(db_path="./data/lka.db")

    # Run with uvicorn:
    # uvicorn src.api.app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()  # reads .env from project root (no-op if absent)

from src.api.admin_routes import admin_router
from src.api.analysis_routes import analysis_router
from src.api.history_routes import history_router
from src.api.compliance_routes import compliance_router
from src.api.contract_coach_routes import coach_router
from src.api.guidance_routes import guidance_router
from src.api.journey_routes import journey_router
from src.api.recommendation_routes import agent_router, behavior_router, feed_router, intelligence_router, interact_router, rec_router
from src.api.retrieval_routes import retrieval_router
from src.api.routes import router
from src.config import PipelineConfig
from src.mongodb.client import ping as mongo_ping
from src.mongodb.mongo_storage import VectorStorage
from src.runtime.audit import AuditLayer
from src.runtime.auth import AuthLayer
from src.runtime.index_store import DocumentIndexStore
from src.runtime.job_runner import JobRunner, ProcessorFn
from src.runtime.processor import build_document_processor
from src.runtime.storage import StorageLayer

logger = logging.getLogger(__name__)


def create_app(
    db_path: str | Path = ":memory:",
    processor: Optional[ProcessorFn] = None,
    bundle_provider: Optional[Callable] = None,
    use_real_pipeline: bool = True,
    use_mongodb: bool = True,
) -> FastAPI:
    """
    Build and configure the FastAPI application.

    Args:
        db_path:            SQLite database path. Use ':memory:' for tests.
        processor:          Job processor function. If None and use_real_pipeline=True,
                            the real 8-stage pipeline processor is used automatically.
        bundle_provider:    Evidence bundle factory injected for tests.
                            Overrides the IndexStore when set.
        use_real_pipeline:  Wire real pipeline processor + IndexStore (default True).
                            Set False in tests that supply bundle_provider.
        use_mongodb:        Connect to MongoDB and enable recommendation engine (default True).
                            Set False in tests to skip MongoDB entirely.
    """
    # Ensure the data directory exists for file-based DBs
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="Legal Knowledge Assistant API",
        description=(
            "Evidence-grounded legal document intelligence + "
            "MongoDB-powered recommendation engine."
        ),
        version="2.0.0",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── SQLite storage (existing pipeline) ───────────────────────────────────
    storage = StorageLayer(db_path)
    app.state.storage = storage
    app.state.auth = AuthLayer(storage)
    app.state.audit = AuditLayer(storage)

    # ── Pipeline processor ────────────────────────────────────────────────────
    if processor is None and use_real_pipeline and bundle_provider is None:
        processor = build_document_processor(storage, PipelineConfig())

    app.state.runner = JobRunner(storage, processor=processor, workers=1)

    # ── Evidence bundle provider (existing query/action logic) ─────────────
    if bundle_provider is not None:
        app.state.bundle_provider = bundle_provider
    elif use_real_pipeline:
        app.state.index_store = DocumentIndexStore()

    # ── MongoDB + Vector Storage + Seed Data ──────────────────────────────────
    # Tests can inject a deterministic bundle_provider; in that mode MongoDB is
    # intentionally skipped so in-process API tests stay isolated and fast.
    should_use_mongodb = use_mongodb and bundle_provider is None
    if should_use_mongodb:
        if mongo_ping():
            logger.info("MongoDB connected — initialising VectorStorage.")
            vs = VectorStorage()
            vs.setup_indexes()
            app.state.vector_storage = vs

            from src.memory.session_store import SessionStore
            SessionStore().setup_indexes()

            # Seed data is pre-loaded; skip auto-seed at startup to avoid
            # SentenceTransformer model-load segfault on first import.
        else:
            logger.warning(
                "MongoDB is not reachable. "
                "Recommendation endpoints will return 503. "
                "Start MongoDB with: docker compose up -d"
            )

    # ── Health endpoint ───────────────────────────────────────────────────────
    @app.get("/health", tags=["system"])
    def health() -> dict:
        """Liveness probe — returns service status and MongoDB connectivity."""
        mongo_ok = mongo_ping()
        return {
            "status": "ok",
            "mongodb": "connected" if mongo_ok else "unavailable",
            "version": app.version,
        }

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(router)
    app.include_router(admin_router)
    app.include_router(rec_router)
    app.include_router(interact_router)
    app.include_router(agent_router)
    app.include_router(behavior_router)
    app.include_router(intelligence_router)
    app.include_router(analysis_router)
    app.include_router(guidance_router)
    app.include_router(retrieval_router)
    app.include_router(compliance_router)
    app.include_router(coach_router)
    app.include_router(journey_router)
    app.include_router(feed_router)
    app.include_router(history_router)

    return app


# Default app instance for `uvicorn src.api.app:app`
app = create_app(db_path="./data/lka.db")
