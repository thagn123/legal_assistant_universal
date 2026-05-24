"""
Phase 14 validation: document viewer, download, evidence upload, and checklist progress.

These tests keep the new UI-facing endpoints deterministic and isolated from
MongoDB by injecting lightweight fakes into app.state.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


class FakeVectorStorage:
    def __init__(self) -> None:
        self.chunks_by_doc: dict[str, list[dict]] = {}
        self.progress: dict[tuple[str, str], list[str]] = {}

    def get_chunks_by_document(self, doc_id: str, user_id: str | None = None) -> list[dict]:
        return self.chunks_by_doc.get(doc_id, [])

    def get_checklist_progress(self, user_id: str, checklist_id: str) -> list[str]:
        return self.progress.get((user_id, checklist_id), [])

    def save_checklist_progress(self, user_id: str, checklist_id: str, checked_items: list[str]) -> None:
        self.progress[(user_id, checklist_id)] = list(checked_items)


class FakeSessionStore:
    def __init__(self) -> None:
        self.appended: list[tuple[str, dict]] = []

    def append_evidence(self, session_id: str, evidence: dict) -> None:
        self.appended.append((session_id, evidence))


@pytest.fixture
def client():
    app = create_app(
        db_path=":memory:",
        use_real_pipeline=False,
        use_mongodb=False,
    )
    app.state.vector_storage = FakeVectorStorage()
    app.state.session_store = FakeSessionStore()
    return TestClient(app)


def test_document_content_returns_extracted_chunks(client: TestClient):
    storage = client.app.state.storage
    doc = storage.create_document("user_14", "law.txt")
    client.app.state.vector_storage.chunks_by_doc[doc.doc_id] = [
        {"content": "Article 1. Scope.", "law_type": "contract", "position": 1},
        {"content": "Article 2. Term.", "law_type": "contract", "position": 2},
    ]

    resp = client.get(
        f"/documents/{doc.doc_id}/content",
        headers={"X-User-ID": "user_14"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chunk_count"] == 2
    assert body["law_type"] == "contract"
    assert "Article 1. Scope." in body["extracted_text"]
    assert "Article 2. Term." in body["extracted_text"]


def test_document_content_cross_tenant_returns_404(client: TestClient):
    storage = client.app.state.storage
    doc = storage.create_document("owner", "private.txt")

    resp = client.get(
        f"/documents/{doc.doc_id}/content",
        headers={"X-User-ID": "other_user"},
    )

    assert resp.status_code == 404


def test_global_document_content_is_visible_to_user(client: TestClient):
    storage = client.app.state.storage
    doc = storage.create_global_document("global-law.txt")
    client.app.state.vector_storage.chunks_by_doc[doc.doc_id] = [
        {"content": "Global legal guidance.", "law_type": "general", "position": 1},
    ]

    resp = client.get(
        f"/documents/{doc.doc_id}/content",
        headers={"X-User-ID": "any_user"},
    )

    assert resp.status_code == 200
    assert "Global legal guidance." in resp.json()["extracted_text"]


def test_download_document_serves_original_file(client: TestClient, tmp_path: Path):
    storage = client.app.state.storage
    doc = storage.create_document("user_14", "original.txt")
    original = tmp_path / "original.txt"
    original.write_text("original bytes", encoding="utf-8")
    storage.save_file_path(doc.doc_id, str(original))

    resp = client.get(
        f"/documents/{doc.doc_id}/download",
        headers={"X-User-ID": "user_14"},
    )

    assert resp.status_code == 200
    assert resp.content == b"original bytes"


def test_upload_session_evidence_attaches_extracted_text(client: TestClient):
    resp = client.post(
        "/sessions/session_14/evidence",
        headers={"X-User-ID": "user_14"},
        files={"file": ("note.txt", b"Evidence text for this session.", "text/plain")},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "session_14"
    assert body["status"] == "attached"
    assert body["char_count"] == len("Evidence text for this session.")

    appended = client.app.state.session_store.appended
    assert appended
    assert appended[0][0] == "session_14"
    assert appended[0][1]["filename"] == "note.txt"


def test_upload_session_evidence_rejects_unsupported_type(client: TestClient):
    resp = client.post(
        "/sessions/session_14/evidence",
        headers={"X-User-ID": "user_14"},
        files={"file": ("image.png", b"not accepted", "image/png")},
    )

    assert resp.status_code == 400


def test_checklist_progress_round_trip(client: TestClient):
    headers = {"X-User-ID": "user_14"}
    payload = {"checked_items": ["cl_1:0:0", "cl_1:1:2"]}

    save = client.post("/recommendations/checklists/cl_1/progress", json=payload, headers=headers)
    assert save.status_code == 200
    assert save.json()["checked_items"] == payload["checked_items"]

    get = client.get("/recommendations/checklists/cl_1/progress", headers=headers)
    assert get.status_code == 200
    assert get.json()["checked_items"] == payload["checked_items"]


def test_checklist_progress_uses_sqlite_when_vector_storage_unavailable():
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as local_client:
        headers = {"X-User-ID": "sqlite_user"}
        payload = {"checked_items": ["local_cl:0:0"]}

        save = local_client.post(
            "/recommendations/checklists/local_cl/progress",
            json=payload,
            headers=headers,
        )
        assert save.status_code == 200

        get = local_client.get(
            "/recommendations/checklists/local_cl/progress",
            headers=headers,
        )
        assert get.status_code == 200
        assert get.json()["checked_items"] == payload["checked_items"]
