"""
MongoDB client singleton for the Legal Knowledge Recommendation Engine.

Connection is configured via environment variables:
  MONGO_URI  — default: mongodb://localhost:27017/?directConnection=true
  MONGO_DB   — default: legal_knowledge_assistant

For local development: docker compose up -d  (starts mongodb/mongodb-atlas-local)
For production: set MONGO_URI to your Atlas connection string.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database

logger = logging.getLogger(__name__)

_MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb://localhost:27017/?directConnection=true",
)
_DB_NAME = os.environ.get("MONGO_DB", "legal_knowledge_assistant")

_client: Optional[MongoClient] = None


def get_client() -> MongoClient:
    """Return (and lazily create) the shared MongoClient."""
    global _client
    if _client is None:
        _client = MongoClient(_MONGO_URI, serverSelectionTimeoutMS=5000)
        logger.info("MongoDB client connected: uri=%s db=%s", _MONGO_URI, _DB_NAME)
    return _client


def get_db() -> Database:
    """Return the application database."""
    return get_client()[_DB_NAME]


def close() -> None:
    """Close the shared client (call on app shutdown)."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB client closed.")


def ping() -> bool:
    """Return True if MongoDB is reachable."""
    try:
        get_client().admin.command("ping")
        return True
    except Exception as exc:
        logger.warning("MongoDB ping failed: %s", exc)
        return False
