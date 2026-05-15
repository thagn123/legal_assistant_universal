"""
Phase 10 validation: API endpoints.

Uses FastAPI TestClient (in-process HTTP) — no network, no LLM, deterministic.
A bundle_provider is injected into app.state so queries and actions return
real EvidenceBundle objects backed by Chunk fixtures.

Pass criteria covered:
  1. Jobs are resumable and auditable:  upload → job queued; actions → audit_id returned.
  2. Users can query only their own document spaces: cross-tenant 404 on all read endpoints.
  3. Every answer links back to stored evidence: action response carries audit_id + citations.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.graphrag.evidence_bundle import SUPPORTED, EvidenceBundle
from src.schemas.chunk import Chunk


# ---------------------------------------------------------------------------
# Bundle fixture helpers
# ---------------------------------------------------------------------------


def _chunk(chunk_id: str, content: str, citation: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id="doc_fixture",
        chunk_type="text",
        content=content,
        confidence=0.92,
        degraded=False,
        degraded_reasons=[],
        citations=[citation],
        structure_path=["Article 1"],
        hierarchy_path="Article 1",
    )


def _bundle(query_id: str, chunks: list[Chunk]) -> EvidenceBundle:
    return EvidenceBundle(
        query_id=query_id,
        seed_chunk_ids=[c.chunk_id for c in chunks],
        expanded_node_ids=[],
        evidence_chunks=chunks,
        support_status=SUPPORTED,
        confidence=0.92,
        citations=[c.citations[0] for c in chunks if c.citations],
        warnings=[],
    )


def _bundle_provider(user_id: str, document_ids: list[str]) -> list[EvidenceBundle]:
    chunk = _chunk(
        "c_api",
        "Article 1. Parties. The parties agree to the following terms.",
        "Test Contract, Art 1",
    )
    return [_bundle("q_api", [chunk])]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    return create_app(db_path=":memory:", bundle_provider=_bundle_provider)


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def user_a(client):
    client.app.state.auth.create_user("key_user_a")
    return "key_user_a"


@pytest.fixture
def user_b(client):
    client.app.state.auth.create_user("key_user_b")
    return "key_user_b"


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


class TestUploadEndpoint:

    def test_upload_creates_document_and_job(self, client, user_a):
        resp = client.post(
            "/documents/upload",
            json={"filename": "contract.pdf"},
            headers={"X-API-Key": user_a},
        )
        assert resp.status_code == 202
        body = resp.json()
        assert "doc_id" in body
        assert "job_id" in body
        assert body["status"] == "queued"

    def test_upload_missing_api_key_returns_422(self, client):
        resp = client.post("/documents/upload", json={"filename": "x.pdf"})
        assert resp.status_code == 422

    def test_upload_invalid_api_key_returns_401(self, client):
        resp = client.post(
            "/documents/upload",
            json={"filename": "x.pdf"},
            headers={"X-API-Key": "wrong_key"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


class TestJobEndpoints:

    def test_get_job_returns_status(self, client, user_a):
        up = client.post(
            "/documents/upload",
            json={"filename": "doc.pdf"},
            headers={"X-API-Key": user_a},
        ).json()
        resp = client.get(f"/jobs/{up['job_id']}", headers={"X-API-Key": user_a})
        assert resp.status_code == 200
        assert resp.json()["job_id"] == up["job_id"]
        assert resp.json()["status"] in ("queued", "running", "complete", "failed")

    def test_cross_tenant_job_returns_404(self, client, user_a, user_b):
        up = client.post(
            "/documents/upload",
            json={"filename": "a.pdf"},
            headers={"X-API-Key": user_a},
        ).json()
        resp = client.get(f"/jobs/{up['job_id']}", headers={"X-API-Key": user_b})
        assert resp.status_code == 404

    def test_list_jobs_filtered_to_caller(self, client, user_a, user_b):
        client.post("/documents/upload", json={"filename": "a.pdf"}, headers={"X-API-Key": user_a})
        client.post("/documents/upload", json={"filename": "b.pdf"}, headers={"X-API-Key": user_b})

        doc_ids_a = {j["doc_id"] for j in client.get("/jobs", headers={"X-API-Key": user_a}).json()}
        doc_ids_b = {j["doc_id"] for j in client.get("/jobs", headers={"X-API-Key": user_b}).json()}
        assert not doc_ids_a.intersection(doc_ids_b)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


class TestDocumentEndpoints:

    def test_list_documents_returns_uploaded(self, client, user_a):
        client.post("/documents/upload", json={"filename": "report.pdf"}, headers={"X-API-Key": user_a})
        docs = client.get("/documents", headers={"X-API-Key": user_a}).json()
        assert any(d["filename"] == "report.pdf" for d in docs)

    def test_get_document_returns_correct_record(self, client, user_a):
        doc_id = client.post(
            "/documents/upload",
            json={"filename": "law.pdf"},
            headers={"X-API-Key": user_a},
        ).json()["doc_id"]
        resp = client.get(f"/documents/{doc_id}", headers={"X-API-Key": user_a})
        assert resp.status_code == 200
        assert resp.json()["doc_id"] == doc_id

    def test_cross_tenant_document_returns_404(self, client, user_a, user_b):
        doc_id = client.post(
            "/documents/upload",
            json={"filename": "secret.pdf"},
            headers={"X-API-Key": user_a},
        ).json()["doc_id"]
        resp = client.get(f"/documents/{doc_id}", headers={"X-API-Key": user_b})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


class TestQueryEndpoint:

    def test_query_returns_answer_with_citations(self, client, user_a):
        resp = client.post(
            "/queries",
            json={"query": "What does Article 1 say?", "query_id": "q_test_1"},
            headers={"X-API-Key": user_a},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["query_id"] == "q_test_1"
        assert "answer" in body
        assert len(body["citations"]) > 0

    def test_query_from_supported_bundle_is_not_refusal(self, client, user_a):
        resp = client.post(
            "/queries",
            json={"query": "What do the parties agree to?"},
            headers={"X-API-Key": user_a},
        )
        assert resp.json()["is_refusal"] is False

    def test_query_missing_key_returns_422(self, client):
        resp = client.post("/queries", json={"query": "test"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Actions (Pass criteria 1 and 3)
# ---------------------------------------------------------------------------


class TestActionEndpoint:

    def test_action_returns_audit_id(self, client, user_a):
        """Every action result links back to an audit record (criterion 3)."""
        resp = client.post(
            "/actions",
            json={
                "action_type": "legal_summarization",
                "query": "Summarize the contract.",
                "request_id": "req_sum_1",
            },
            headers={"X-API-Key": user_a},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["audit_id"]  # non-empty string

    def test_action_response_includes_citations(self, client, user_a):
        resp = client.post(
            "/actions",
            json={"action_type": "legal_summarization", "query": "Summarize parties clause."},
            headers={"X-API-Key": user_a},
        )
        assert len(resp.json()["citations"]) > 0

    def test_action_audit_trail_retrievable(self, client, user_a):
        """Audit trail is accessible and contains the logged request (criterion 1)."""
        client.post(
            "/actions",
            json={
                "action_type": "legal_summarization",
                "query": "Summarize.",
                "request_id": "req_audit_check",
            },
            headers={"X-API-Key": user_a},
        )
        trail = client.get("/audit", headers={"X-API-Key": user_a}).json()
        assert any(r["request_id"] == "req_audit_check" for r in trail)

    def test_invalid_action_type_returns_400(self, client, user_a):
        resp = client.post(
            "/actions",
            json={"action_type": "not_a_real_action", "query": "Do something."},
            headers={"X-API-Key": user_a},
        )
        assert resp.status_code == 400

    def test_action_missing_key_returns_422(self, client):
        resp = client.post(
            "/actions",
            json={"action_type": "legal_summarization", "query": "x"},
        )
        assert resp.status_code == 422

    def test_cross_tenant_audit_isolation(self, client, user_a, user_b):
        """User B cannot see User A's audit records (criterion 2)."""
        client.post(
            "/actions",
            json={
                "action_type": "legal_summarization",
                "query": "A's query",
                "request_id": "req_a_only",
            },
            headers={"X-API-Key": user_a},
        )
        trail_b = client.get("/audit", headers={"X-API-Key": user_b}).json()
        assert not any(r["request_id"] == "req_a_only" for r in trail_b)

    def test_action_output_hash_verifiable(self, client, user_a):
        """output_hash in audit matches SHA-256 of the action output."""
        import hashlib

        action_resp = client.post(
            "/actions",
            json={
                "action_type": "legal_summarization",
                "query": "Summarize parties.",
                "request_id": "req_hash_check",
            },
            headers={"X-API-Key": user_a},
        ).json()
        output_text = action_resp["output"]

        trail = client.get("/audit", headers={"X-API-Key": user_a}).json()
        record = next(r for r in trail if r["request_id"] == "req_hash_check")
        expected_hash = hashlib.sha256(output_text.encode("utf-8")).hexdigest()
        assert record["output_hash"] == expected_hash
