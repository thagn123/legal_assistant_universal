"""
Authentication and authorization layer for Phase 10.

Uses hashed API key validation against storage.
Tenant isolation: every user_id is derived from a unique API key.
"""

from __future__ import annotations

from typing import Optional

from src.runtime.storage import StorageLayer, UserRecord


class AuthLayer:
    """API key authentication with tenant isolation."""

    def __init__(self, storage: StorageLayer) -> None:
        self._storage = storage

    def create_user(self, api_key: str) -> UserRecord:
        """Register a new user with the given API key."""
        return self._storage.create_user(api_key)

    def verify(self, api_key: str) -> Optional[str]:
        """Return user_id if the key is valid, None otherwise."""
        record = self._storage.get_user_by_key(api_key)
        return record.user_id if record else None

    def require(self, api_key: str) -> str:
        """Return user_id or raise ValueError for an invalid/unknown key."""
        user_id = self.verify(api_key)
        if user_id is None:
            raise ValueError("Invalid or missing API key.")
        return user_id
