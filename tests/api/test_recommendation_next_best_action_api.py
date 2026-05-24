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
