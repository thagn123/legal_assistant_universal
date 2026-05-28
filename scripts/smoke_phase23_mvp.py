"""
Phase 23 MVP Smoke Test.

Validates end-to-end flow for the three demo personas:
  1. Set user demo_user_family
  2. Analyze query (ly hôn, nuôi con)
  3. Read next-best-actions
  4. Search similar cases (official + community)
  5. Mark a recommendation useful
  6. Repeat next-best-actions (behavior should shift)
  7. Switch to demo_user_employee
  8. Run same query
  9. Assert ranking differs between personas

Usage:
    # Local direct mode (no server):
    python scripts/smoke_phase23_mvp.py

    # Against deployed server:
    LEXAI_DEPLOYED_BASE_URL=http://localhost:8001 python scripts/smoke_phase23_mvp.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = os.environ.get("LEXAI_DEPLOYED_BASE_URL", "").rstrip("/")
FAMILY_USER = "demo_user_family"
EMPLOYEE_USER = "demo_user_employee"
QUERY = "Tôi muốn ly hôn, có hai con và muốn biết tài sản chung sẽ được chia như thế nào."


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _req(method: str, path: str, body: dict | None, user_id: str) -> dict:
    url = BASE_URL + path
    payload = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-User-ID": user_id,
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        print(f"  HTTP {e.code} for {method} {path}: {body_bytes[:300]}")
        raise


# ---------------------------------------------------------------------------
# Direct-mode helpers (no server)
# ---------------------------------------------------------------------------

def _direct_similar_cases(situation: str, user_id: str) -> dict:
    from src.api.retrieval_routes import find_similar_cases, SimilarCaseRequest
    from src.runtime.storage import StorageLayer
    from pathlib import Path

    db_path = Path(__file__).parent.parent / "data" / "lka.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _store = StorageLayer(str(db_path))

    class FakeState:
        mongodb_enabled = False
        vector_storage = None
        storage = _store

    class FakeApp:
        state = FakeState()

    class FakeRequest:
        app = FakeApp()

    req = SimilarCaseRequest(situation=situation, include_community=True)
    result = find_similar_cases(req, FakeRequest(), user_id=user_id)
    return result.model_dump() if hasattr(result, "model_dump") else result.dict()


def _direct_nba(situation: str, user_id: str) -> list:
    from src.recommenders.next_best_action import NextBestActionRecommender, build_recommendation_context
    from src.runtime.storage import StorageLayer
    from src.api.recommendation_routes import _next_best_action_behavior_scores
    from pathlib import Path

    db_path = Path(__file__).parent.parent / "data" / "lka.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = StorageLayer(str(db_path))

    ctx = build_recommendation_context(
        situation=situation,
        domain="gia_dinh",
        position_score=0.55,
        domain_confidence=0.75,
        citations=["Luật HNGD 2014"],
        warnings=[],
        recommended_actions=["Thu thập hồ sơ"],
        risk_assessment={},
    )
    behavior_scores = _next_best_action_behavior_scores(store, user_id)
    results = NextBestActionRecommender().recommend(ctx, limit=6, behavior_scores=behavior_scores)
    return [{"action_id": r.action_id, "score": r.score, "reason": r.reason} for r in results]


def _direct_log_interaction(user_id: str, doc_id: str, action_type: str, context: dict) -> None:
    from src.runtime.storage import StorageLayer
    from pathlib import Path

    db_path = Path(__file__).parent.parent / "data" / "lka.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = StorageLayer(str(db_path))
    store.log_interaction(user_id=user_id, doc_id=doc_id, action_type=action_type, context=context)


# ---------------------------------------------------------------------------
# Smoke steps
# ---------------------------------------------------------------------------

PASS = "[OK]"
FAIL = "[FAIL]"
_failures: list[str] = []


def _assert(condition: bool, label: str, detail: str = "") -> None:
    if condition:
        print(f"  {PASS} {label}")
    else:
        print(f"  {FAIL} {label}{' — ' + detail if detail else ''}")
        _failures.append(label)


def step_similar_cases(user_id: str) -> dict:
    print(f"\n[Step] similar-cases for {user_id}")
    if BASE_URL:
        result = _req("POST", "/retrieval/similar-cases",
                      {"situation": QUERY, "include_community": True}, user_id)
    else:
        result = _direct_similar_cases(QUERY, user_id)

    _assert(isinstance(result.get("similar_cases"), list), "similar_cases is list")
    _assert(isinstance(result.get("community_cases"), list), "community_cases is list")
    _assert("official_cases" in result, "official_cases field present")
    _assert("cross_language_used" in result, "cross_language_used field present")
    _assert("fallback_used" in result, "fallback_used field present")
    print(f"    similar_cases={len(result.get('similar_cases', []))}, "
          f"community={len(result.get('community_cases', []))}")
    return result


def step_nba(user_id: str, label: str = "") -> list:
    print(f"\n[Step] next-best-actions for {user_id} {label}")
    if BASE_URL:
        result = _req("POST", "/recommendations/next-best-actions", {
            "situation": QUERY,
            "domain": "gia_dinh",
            "position_score": 0.55,
            "domain_confidence": 0.75,
            "citations": ["Luật HNGD 2014"],
            "warnings": [],
        }, user_id)
    else:
        result = _direct_nba(QUERY, user_id)

    _assert(isinstance(result, list), "result is list")
    _assert(len(result) >= 1, f"at least 1 action returned (got {len(result)})")
    if result:
        print(f"    top action: {result[0].get('action_id', '?')} score={result[0].get('score', '?')}")
    return result


def step_log_useful(user_id: str, action_id: str) -> None:
    print(f"\n[Step] log useful for {user_id} / {action_id}")
    if BASE_URL:
        _req("POST", "/interactions/log", {
            "doc_id": action_id,
            "action_type": "recommendation_useful",
            "context": {"action_id": action_id, "module": action_id},
        }, user_id)
        print(f"  {PASS} logged via API")
    else:
        _direct_log_interaction(
            user_id=user_id,
            doc_id=action_id,
            action_type="recommendation_useful",
            context={"action_id": action_id, "module": action_id},
        )
        print(f"  {PASS} logged via direct import")


def step_cross_language(user_id: str) -> None:
    print(f"\n[Step] cross-language query for {user_id}")
    en_query = "divorce and child custody dispute in Vietnam"
    if BASE_URL:
        result = _req("POST", "/retrieval/similar-cases",
                      {"situation": en_query, "include_community": False}, user_id)
    else:
        result = _direct_similar_cases(en_query, user_id)

    _assert(result.get("query_language") == "en", "query_language detected as 'en'")
    _assert(result.get("cross_language_used") is True, "cross_language_used=True")
    _assert(len(result.get("expanded_aliases", [])) > 0, "expanded aliases non-empty")
    print(f"    aliases: {result.get('expanded_aliases', [])[:3]}")


def step_compare_personas() -> None:
    print(f"\n[Step] compare ranking between family vs employee persona")
    family_nba = step_nba(FAMILY_USER, "(compare)")
    employee_nba = step_nba(EMPLOYEE_USER, "(compare)")

    if not family_nba or not employee_nba:
        _assert(False, "both personas returned non-empty NBA lists")
        return

    family_top = family_nba[0].get("action_id", "")
    employee_top = employee_nba[0].get("action_id", "")

    family_ids = [r.get("action_id") for r in family_nba]
    employee_ids = [r.get("action_id") for r in employee_nba]

    # Scores may differ even if order is the same
    family_scores = {r.get("action_id"): r.get("score", 0) for r in family_nba}
    employee_scores = {r.get("action_id"): r.get("score", 0) for r in employee_nba}

    scores_differ = any(
        abs(family_scores.get(aid, 0) - employee_scores.get(aid, 0)) > 0.001
        for aid in set(family_scores) & set(employee_scores)
    )
    order_differs = family_ids != employee_ids

    _assert(
        scores_differ or order_differs,
        "personalized ranking differs between family and employee personas",
        f"family_top={family_top}, employee_top={employee_top}",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("Phase 23 MVP Smoke Test")
    print(f"Mode: {'HTTP API at ' + BASE_URL if BASE_URL else 'direct import (no server)'}")
    print("=" * 60)

    # 1. similar-cases for family
    step_similar_cases(FAMILY_USER)

    # 2. NBA for family
    nba_before = step_nba(FAMILY_USER, "(before feedback)")
    top_action = nba_before[0].get("action_id", "evidence_gap") if nba_before else "evidence_gap"

    # 3. Log useful
    step_log_useful(FAMILY_USER, top_action)

    # 4. NBA after useful signal — score of top action may shift
    nba_after = step_nba(FAMILY_USER, "(after feedback)")
    if nba_before and nba_after:
        before_top_score = nba_before[0].get("score", 0)
        after_top_score = nba_after[0].get("score", 0)
        print(f"    score shift: {before_top_score:.3f} -> {after_top_score:.3f}")

    # 5. Cross-language
    step_cross_language(FAMILY_USER)

    # 6. Compare personas
    step_compare_personas()

    # 7. Privacy anonymizer
    print(f"\n[Step] privacy anonymizer")
    from src.privacy.anonymizer import anonymize_legal_situation
    result = anonymize_legal_situation(
        "Ông Nguyễn Văn An muốn ly hôn, số điện thoại 0912345678.",
        domain="gia_dinh",
    )
    _assert("0912345678" not in result["safe_summary"], "phone redacted")
    _assert("Nguyễn Văn An" not in result["safe_summary"], "name redacted")
    _assert(len(result["safe_summary"]) >= 10, "non-empty safe_summary")

    # 8. Community pattern storage
    print(f"\n[Step] community case pattern storage")
    from src.runtime.storage import StorageLayer
    s = StorageLayer(":memory:")
    inserted = s.save_community_case_pattern(
        pattern_id="smoke_ccp_001",
        summary="Người dùng muốn ly hôn và tranh chấp nuôi con.",
        legal_domain="gia_dinh",
        user_goal=["divorce", "child_custody"],
        resolution_summary="Chuẩn bị hồ sơ ly hôn.",
        recommended_steps=["Lấy giấy khai sinh"],
        citations=["Luật HNGD 2014"],
        tags=["ly_hon", "nuoi_con"],
    )
    _assert(inserted is True, "first insert returns True")
    s.increment_community_case_signal("smoke_ccp_001", "useful")
    results = s.search_community_case_patterns("ly hôn nuôi con", limit=5)
    _assert(len(results) >= 1, "community pattern searchable after insert")
    _assert(results[0]["popularity"]["useful"] >= 1, "useful signal recorded")

    # Summary
    print("\n" + "=" * 60)
    if _failures:
        print(f"RESULT: FAILED — {len(_failures)} assertion(s) failed:")
        for f in _failures:
            print(f"  {FAIL} {f}")
        return 1
    print(f"RESULT: PASSED — all assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
