"""
Phase 18 validation: behavior recommendations + conversation persistence.

These tests keep the MVP path usable without MongoDB: UI gestures are stored
in SQLite, behavior recommendations can read them, and chat sessions survive
browser-local state.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import create_app


def _client() -> TestClient:
    return TestClient(create_app(db_path=":memory:", use_mongodb=False, use_real_pipeline=False))


def test_interaction_log_accepts_gestures_without_doc_id_and_builds_profile():
    client = _client()

    resp = client.post(
        "/interactions/log",
        json={
            "action_type": "situation_analysis",
            "context": {"law_type": "dat_dai", "session_id": "s1"},
        },
        headers={"X-User-ID": "user_behavior"},
    )

    assert resp.status_code == 200
    assert resp.json() == {"logged": True, "source": "sqlite"}

    profile = client.get(
        "/recommendations/behavior/profile",
        headers={"X-User-ID": "user_behavior"},
    ).json()
    assert profile["total_interactions"] == 1
    assert profile["top_law_type"] == "dat_dai"
    assert profile["action_frequencies"]["situation_analysis"] == 1


def test_behavior_recommendations_use_sqlite_history_when_mongodb_is_absent():
    client = _client()
    headers = {"X-User-ID": "user_recs"}

    client.post(
        "/interactions/log",
        json={"action_type": "situation_analysis", "context": {"law_type": "dat_dai"}},
        headers=headers,
    )
    client.post(
        "/interactions/log",
        json={"action_type": "recommendation_click", "context": {"law_type": "dat_dai"}},
        headers=headers,
    )

    proactive = client.get("/recommendations/behavior/proactive?limit=3", headers=headers)
    assert proactive.status_code == 200
    assert proactive.json()
    assert any(item["rec_type"] == "cross_domain" for item in proactive.json())

    next_action = client.post(
        "/recommendations/behavior/next-action",
        json={"last_action_type": "situation_analysis", "current_law_type": "dat_dai", "limit": 3},
        headers=headers,
    )
    assert next_action.status_code == 200
    assert any(item["rec_type"] == "sequential" for item in next_action.json())


def test_conversations_round_trip_and_stay_user_scoped():
    client = _client()

    created = client.post(
        "/conversations",
        json={
            "id": "chat_001",
            "title": "Tranh chấp đất đai",
            "domain": "dat_dai",
            "turns": [
                {"role": "user", "content": "Tôi cần tư vấn tranh chấp đất."},
                {"role": "assistant", "content": "Có thể phân tích theo Luật Đất đai."},
            ],
            "metadata": {"source": "analyze"},
        },
        headers={"X-User-ID": "user_chat_a"},
    )

    assert created.status_code == 201
    assert created.json()["id"] == "chat_001"
    assert created.json()["turnCount"] == 2

    listed = client.get("/conversations", headers={"X-User-ID": "user_chat_a"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["title"] == "Tranh chấp đất đai"

    fetched = client.get("/conversations/chat_001", headers={"X-User-ID": "user_chat_a"})
    assert fetched.status_code == 200
    assert fetched.json()["turns"][0]["role"] == "user"
    assert fetched.json()["metadata"]["source"] == "analyze"

    other_user = client.get("/conversations/chat_001", headers={"X-User-ID": "user_chat_b"})
    assert other_user.status_code == 404
