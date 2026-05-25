from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import create_app


def test_next_best_actions_endpoint_works_without_mongodb():
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)

    with TestClient(app) as client:
        resp = client.post(
            "/recommendations/next-best-actions",
            headers={"X-User-ID": "rec_user"},
            json={
                "situation": "Cong ty khong tra luong 3 thang va sap het thoi hieu khieu nai.",
                "domain": "lao_dong",
                "position_score": 42,
                "domain_confidence": 0.9,
                "citations": ["Bo luat Lao dong 2019"],
                "warnings": ["Can kiem tra thoi hieu."],
                "recommended_actions": ["Thu thap hop dong lao dong."],
                "risk_assessment": {"risks": ["Qua han khieu nai"], "risk_count": 1},
                "limit": 3,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    assert body[0]["score"] >= body[1]["score"]
    assert body[0]["priority"] in {"high", "medium"}
    assert all(item["action_url"].startswith("/") for item in body)


def test_next_best_actions_uses_feedback_signals_for_demo_personalization():
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)

    with TestClient(app) as client:
        for _ in range(3):
            feedback = client.post(
                "/interactions/log",
                headers={"X-User-ID": "feedback_user"},
                json={
                    "doc_id": "action_plan",
                    "action_type": "recommendation_useful",
                    "context": {"action_id": "action_plan", "module": "actions", "feedback": "useful"},
                },
            )
            assert feedback.status_code == 200

        resp = client.post(
            "/recommendations/next-best-actions",
            headers={"X-User-ID": "feedback_user"},
            json={
                "situation": "Toi can biet nen lam gi tiep theo trong vu viec dan su.",
                "domain": "dan_su",
                "position_score": 0.6,
                "domain_confidence": 0.9,
                "citations": ["Bo luat Dan su 2015"],
                "warnings": [],
                "recommended_actions": ["Lap ke hoach lam viec."],
                "risk_assessment": {},
                "limit": 4,
            },
        )

    assert resp.status_code == 200
    assert resp.json()[0]["action_id"] == "action_plan"


def test_next_best_actions_returns_goal_aware_metadata():
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)

    with TestClient(app) as client:
        resp = client.post(
            "/recommendations/next-best-actions",
            headers={"X-User-ID": "goal_user"},
            json={
                "situation": "Toi muon ly hon, nuoi con va giu tai san khi chia tai san chung.",
                "domain": "dan_su",
                "position_score": 0.45,
                "domain_confidence": 0.9,
                "citations": ["Luat Hon nhan va Gia dinh 2014"],
                "warnings": ["Can chung cu ve dieu kien nuoi con."],
                "recommended_actions": ["Chuan bi ho so ly hon."],
                "risk_assessment": {"risks": ["Tranh chap quyen nuoi con"], "risk_count": 1},
                "limit": 4,
            },
        )

    assert resp.status_code == 200
    first = resp.json()[0]
    assert "child_custody" in first["detected_goals"]
    assert first["user_position"] == "parent_seeking_custody"
    assert first["next_questions"]
    assert first["journey_steps"]
