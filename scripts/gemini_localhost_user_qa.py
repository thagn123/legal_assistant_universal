#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 24 — Gemini Localhost User Simulation QA Runner.

Simulates a real user interacting with LexAI across 8 scenarios in both
Vietnamese and English, then sends results to Gemini Flash for scoring.

Usage:
    # Live mode (backend + optional frontend must be running):
    python scripts/gemini_localhost_user_qa.py

    # Dry-run (uses rich simulated data, no server needed):
    python scripts/gemini_localhost_user_qa.py --dry-run

    # Override backend URL:
    LEXAI_BACKEND_URL=http://my-server:8001 python scripts/gemini_localhost_user_qa.py

Environment variables (set in .env or shell):
    GEMINI_API_KEY          — required
    GEMINI_MODEL            — optional, default gemini-1.5-flash
    LEXAI_BACKEND_URL       — default http://localhost:8001
    LEXAI_FRONTEND_URL      — default http://localhost:3000
    LEXAI_QA_OUTPUT_DIR     — default reports/
    LEXAI_QA_DRY_RUN        — set to 1 for dry-run

Output files:
    reports/gemini_localhost_qa_YYYY-MM-DD.md
    reports/gemini_localhost_qa_YYYY-MM-DD.json
    docs/07-implementation/phase24-gemini-qa-fix-plan.md  (if MVP incomplete)
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

# --- Project root on sys.path ---
sys.path.insert(0, str(Path(__file__).parent.parent))

# --- UTF-8 output on Windows ---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional

from src.qa.gemini_evaluator import GeminiQAEvaluator

# ── Config ────────────────────────────────────────────────────────────────────
BACKEND_URL = os.getenv("LEXAI_BACKEND_URL", "http://localhost:8001").rstrip("/")
FRONTEND_URL = os.getenv("LEXAI_FRONTEND_URL", "http://localhost:3000").rstrip("/")
OUTPUT_DIR = Path(os.getenv("LEXAI_QA_OUTPUT_DIR", "reports"))
IS_DRY_RUN = "--dry-run" in sys.argv or os.getenv("LEXAI_QA_DRY_RUN", "0") == "1"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── HTTP helper ───────────────────────────────────────────────────────────────
def _call_api(method: str, path: str, body: dict | None, user_id: str) -> Tuple[int, dict, float]:
    url = BACKEND_URL + path
    payload = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "X-User-ID": user_id},
        method=method,
    )
    start = time.time()
    status_code = 200
    resp_data: dict = {}
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            status_code = resp.status
            resp_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        status_code = e.code
        try:
            resp_data = json.loads(e.read().decode("utf-8"))
        except Exception:
            resp_data = {"error": "Could not parse error response"}
    except Exception as exc:
        status_code = 503
        resp_data = {"error": f"Connection error: {exc}"}
    return status_code, resp_data, time.time() - start


# ── Liveness probe ────────────────────────────────────────────────────────────
def check_services() -> Tuple[bool, bool]:
    backend_up = False
    try:
        with urllib.request.urlopen(f"{BACKEND_URL}/health", timeout=4) as r:
            backend_up = r.status == 200
    except Exception:
        pass
    frontend_up = False
    try:
        with urllib.request.urlopen(FRONTEND_URL, timeout=4) as r:
            frontend_up = r.status in (200, 301, 302, 404)
    except Exception:
        pass
    return backend_up, frontend_up


# ── Dry-run simulated responses ───────────────────────────────────────────────
_DRY_RUN_DATA: Dict[str, dict] = {
    "basic_vi_family_analysis": {
        "situation_summary": "Nguoi dung muon ly hon don phuong, gianh quyen truc tiep nuoi 2 con.",
        "legal_position_strength": "Manh",
        "position_score": 0.85,
        "relevant_laws": [
            {"law_reference": "Luat Hon nhan va gia dinh 2014, Dieu 81", "relevance_score": 0.97},
            {"law_reference": "Luat Hon nhan va gia dinh 2014, Dieu 59", "relevance_score": 0.92},
        ],
        "recommended_actions": [
            "Thu thap ho so chung minh thu nhap on dinh",
            "Nop don ly hon don phuong kem ban sao giay khai sinh cua con",
        ],
        "citations": ["Luat HNGD 2014, Dieu 81", "Luat HNGD 2014, Dieu 59"],
        "is_grounded": True,
        "fallback_used": False,
    },
    "recommendation_click_and_retention": {
        "similar_cases": [{"case_id": "case_001", "title": "Tranh chap ly hon nuoi con", "similarity_score": 0.92}],
        "official_cases": [{"case_id": "case_001", "similarity_score": 0.92}],
        "community_cases": [{"pattern_id": "ccp_001", "summary": "Me don than gianh quyen nuoi con thanh cong."}],
        "query_language": "vi",
        "cross_language_used": False,
        "fallback_used": False,
    },
    "same_query_different_persona": [
        {
            "action_id": "template_rent_contract",
            "score": 0.94,
            "behavior_score": 0.05,
            "personalization_explanation": "Ca nhan hoa theo ho so SME",
            "ranking_signals": {"base_score": 0.89, "behavior_boost": 0.05, "final_score": 0.94},
        }
    ],
    "feedback_loop_nba": [
        {
            "action_id": "evidence_gap",
            "score": 0.97,
            "behavior_score": 0.12,
            "personalization_explanation": "Uu tien tang 12% dua tren phan hoi huu ich",
            "ranking_signals": {"base_score": 0.85, "behavior_boost": 0.12, "final_score": 0.97},
        }
    ],
    "community_similar_cases": {
        "official_cases": [{"case_id": "case_labor_005", "title": "Sa thai trai luat", "similarity_score": 0.93}],
        "community_cases": [{"pattern_id": "ccp_labor_005", "summary": "Nguoi lao dong bi sa thai trai luat."}],
        "query_language": "vi",
        "cross_language_used": False,
        "fallback_used": False,
    },
    "cross_language_query": {
        "official_cases": [{"case_id": "case_en_001", "title": "Unilateral termination without notice"}],
        "community_cases": [],
        "query_language": "en",
        "cross_language_used": True,
        "expanded_aliases": ["cham dut hop dong lao dong don phuong", "sa thai khong bao truoc"],
        "fallback_used": False,
    },
    "dashboard_behavior_audit": {
        "profile": {"primary_domain": "gia_dinh", "interactions_count": 12},
        "digest": {
            "summary": "Ban dang tap trung tra cuu luat hon nhan gia dinh.",
            "recommendation_focus": "Chuan bi bang chung ve dieu kien tai chinh.",
        },
    },
    "error_and_fallback_experience": {
        "status": "ok",
        "message": "Cau hoi qua ngan. Vui long cung cap them thong tin chi tiet.",
        "fallback_used": True,
        "is_friendly": True,
    },
}


# ── Scenario runner ───────────────────────────────────────────────────────────
def run_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    sid = scenario.get("id", "")
    api_path = scenario.get("api_path", "/intelligence/analyze")
    persona = scenario.get("persona", "demo_user_family")
    user_input = scenario.get("input", "")

    print(f"\n[Scenario] {scenario.get('title')} ({sid})")
    print(f"  Persona: {persona} | API: {api_path}")

    method = "POST"
    body: dict | None = None

    if api_path == "/intelligence/analyze":
        body = {"situation": user_input, "user_role": "nguyen_don"}
    elif api_path == "/retrieval/similar-cases":
        body = {"situation": user_input, "include_community": True, "persist_anonymized": True}
    elif api_path == "/recommendations/next-best-actions":
        domain = "gia_dinh" if "family" in persona else ("doanh_nghiep" if "sme" in persona else "lao_dong")
        body = {
            "situation": user_input,
            "domain": domain,
            "position_score": 0.55,
            "domain_confidence": 0.75,
            "citations": [],
        }
    elif api_path == "/recommendations/behavior/digest":
        method = "GET"
        body = None

    if IS_DRY_RUN:
        print("  [dry-run] Using simulated data")
        time.sleep(0.1)
        status_code = 200
        duration = 0.1
        resp_data = _DRY_RUN_DATA.get(sid, {"status": "ok", "fallback": True})
    else:
        status_code, resp_data, duration = _call_api(method, api_path, body, persona)

    print(f"  Status: {status_code} | Time: {duration:.2f}s")

    assertions_results = []
    resp_str = json.dumps(resp_data, ensure_ascii=False)
    for assertion in scenario.get("required_assertions", []):
        passed = assertion.lower() in resp_str.lower()
        assertions_results.append({"assertion": assertion, "passed": passed})

    passed = sum(1 for a in assertions_results if a["passed"])
    total = len(assertions_results)
    print(f"  Assertions: {passed}/{total} passed")

    return {
        "status_code": status_code,
        "duration_seconds": duration,
        "response_data": resp_data,
        "assertions": assertions_results,
        "browser_mode": "api_fallback",
    }


# ── Report writers ────────────────────────────────────────────────────────────
def write_reports(
    scenarios: List[Dict[str, Any]],
    results: Dict[str, Dict[str, Any]],
    evaluations: Dict[str, Dict[str, Any]],
    evaluator_model: str,
) -> Tuple[str, str]:
    today = datetime.date.today().strftime("%Y-%m-%d")

    score_keys = [
        "ux_clarity", "legal_relevance", "evidence_citation_usefulness",
        "recommendation_quality", "personalization", "context_retention",
        "error_resilience", "mvp_completeness",
    ]
    total_scores = {k: 0 for k in score_keys}
    count = len(evaluations)
    for ev in evaluations.values():
        for k in score_keys:
            total_scores[k] += ev.get("scores", {}).get(k, 0)
    avg_scores = {k: round(v / count, 1) if count > 0 else 0 for k, v in total_scores.items()}
    overall_score = round(sum(avg_scores.values()) / len(avg_scores) * 10, 1) if avg_scores else 0

    critical_blockers = 0
    major_issues = 0
    minor_issues = 0
    all_issues: List[dict] = []
    for ev in evaluations.values():
        for issue in ev.get("issues", []):
            sev = issue.get("severity", "minor")
            all_issues.append(issue)
            if sev == "blocker":
                critical_blockers += 1
            elif sev == "major":
                major_issues += 1
            else:
                minor_issues += 1

    if critical_blockers == 0 and major_issues == 0 and overall_score >= 70:
        mvp_ready = "PASS"
    elif critical_blockers == 0 and overall_score >= 50:
        mvp_ready = "PARTIAL"
    else:
        mvp_ready = "FAIL"

    # JSON report
    json_report: dict = {
        "date": today,
        "evaluator": evaluator_model,
        "overall_status": mvp_ready.lower(),
        "overall_score": overall_score,
        "mvp_complete": mvp_ready in ("PASS", "PARTIAL"),
        "browser_mode": "api_fallback",
        "scores": avg_scores,
        "issues": all_issues,
        "scenarios": [],
    }
    for sc in scenarios:
        sid = sc["id"]
        res = results[sid]
        ev = evaluations[sid]
        json_report["scenarios"].append({
            "id": sid,
            "title": sc["title"],
            "status": ev.get("status", "fail"),
            "scores": ev.get("scores", {}),
            "duration_seconds": res["duration_seconds"],
            "assertions_passed": sum(1 for a in res["assertions"] if a["passed"]),
            "total_assertions": len(res["assertions"]),
            "judgement": ev.get("judgement", ""),
        })

    json_path = OUTPUT_DIR / f"gemini_localhost_qa_{today}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)

    # Markdown report
    md_lines = [
        f"# Gemini Localhost QA Report - {today}",
        "",
        "## Overall Result",
        "",
        f"- **MVP readiness**: {mvp_ready}",
        f"- **Overall score**: {overall_score}/100",
        f"- **Evaluator model**: {evaluator_model}",
        f"- **Browser mode**: api_fallback",
        f"- **Critical blockers**: {critical_blockers}",
        f"- **Major issues**: {major_issues}",
        f"- **Minor issues**: {minor_issues}",
        "",
        "## Score Table",
        "",
        "| Category | Score | Notes |",
        "|---|---:|---|",
        f"| UX clarity | {avg_scores['ux_clarity']}/10 | Do ro rang va tuong tac giao dien |",
        f"| Legal relevance | {avg_scores['legal_relevance']}/10 | Do chinh xac phap ly |",
        f"| Evidence/Citation | {avg_scores['evidence_citation_usefulness']}/10 | Tinh huu ich dan chung |",
        f"| Recommendation quality | {avg_scores['recommendation_quality']}/10 | Chat luong NBA |",
        f"| Personalization | {avg_scores['personalization']}/10 | Ca nhan hoa theo persona |",
        f"| Context retention | {avg_scores['context_retention']}/10 | Ghi nho ngu canh |",
        f"| Error resilience | {avg_scores['error_resilience']}/10 | Kha nang chiu loi |",
        f"| MVP completeness | {avg_scores['mvp_completeness']}/10 | San sang demo |",
        "",
        "## Scenario Results",
        "",
    ]

    for sc in scenarios:
        sid = sc["id"]
        res = results[sid]
        ev = evaluations[sid]
        md_lines += [
            f"### {sc['title']}",
            "",
            f"- **Status**: `{ev.get('status', 'fail').upper()}`",
            f"- **Persona**: `{sc['persona']}`",
            f"- **Language**: `{sc.get('language', 'vi')}`",
            f"- **Input**: *\"{sc['input'][:120]}\"*",
            f"- **Response time**: `{res['duration_seconds']:.2f}s`",
            "- **What worked**:",
        ]
        for item in ev.get("what_worked", []):
            md_lines.append(f"  - {item}")
        md_lines.append("- **What failed**:")
        for item in ev.get("what_failed", []):
            md_lines.append(f"  - {item}")
        md_lines += [
            f"- **Gemini judgement**: *{ev.get('judgement', 'N/A')}*",
            "",
        ]

    md_lines += ["## Issues", ""]
    if not all_issues:
        md_lines.append("*No issues found. MVP is in good shape!*")
    else:
        for i, issue in enumerate(all_issues, 1):
            md_lines += [
                f"### {i}. [{issue.get('severity', 'minor').upper()}] {issue.get('title', '')}",
                "",
                f"- **Module**: `{issue.get('module')}`",
                f"- **Step**: `{issue.get('step')}`",
                f"- **Expected**: {issue.get('expected')}",
                f"- **Actual**: {issue.get('actual')}",
                f"- **Suggested fix**: *{issue.get('suggested_fix')}*",
                "",
            ]

    md_lines += [
        "## MVP Gaps",
        "",
        "1. Community case database grows only through user queries — seed more patterns.",
        "2. Browser-mode testing (Playwright) not yet integrated — UI interactions unverified.",
        "3. GraphRAG relation labels depend on seeded law chunks — empty on fresh install.",
        "",
    ]

    md_path = OUTPUT_DIR / f"gemini_localhost_qa_{today}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    if mvp_ready != "PASS":
        _write_fix_plan(all_issues, evaluator_model)

    return str(md_path), str(json_path)


def _write_fix_plan(issues: List[dict], evaluator_model: str) -> str:
    docs_dir = Path("docs/07-implementation")
    docs_dir.mkdir(parents=True, exist_ok=True)
    fix_path = docs_dir / "phase24-gemini-qa-fix-plan.md"

    today = datetime.date.today().strftime("%Y-%m-%d")
    blockers = [i for i in issues if i.get("severity") == "blocker"]
    majors = [i for i in issues if i.get("severity") == "major"]
    minors = [i for i in issues if i.get("severity") == "minor"]

    lines = [
        f"# Phase 24 Gemini QA Fix Plan — {today}",
        "",
        f"Auto-generated from Gemini QA run using model `{evaluator_model}`.",
        "",
        "## Summary",
        "",
        f"- **Total issues**: {len(issues)}",
        f"- **Blockers**: {len(blockers)}",
        f"- **Major**: {len(majors)}",
        f"- **Minor**: {len(minors)}",
        "",
        "## Blockers",
        "",
    ]
    if not blockers:
        lines.append("*No blockers found.*")
    else:
        for i, b in enumerate(blockers, 1):
            lines += [
                f"### B.{i} — [{b.get('module')}] {b.get('title')}",
                f"- **Actual**: {b.get('actual')}",
                f"- **Expected**: {b.get('expected')}",
                f"- **Fix**: {b.get('suggested_fix')}",
                "",
            ]

    lines += ["", "## Major Issues", ""]
    if not majors:
        lines.append("*No major issues found.*")
    else:
        for i, m in enumerate(majors, 1):
            lines += [
                f"### M.{i} — [{m.get('module')}] {m.get('title')}",
                f"- **Actual**: {m.get('actual')}",
                f"- **Expected**: {m.get('expected')}",
                f"- **Fix**: {m.get('suggested_fix')}",
                "",
            ]

    lines += ["", "## Minor Issues", ""]
    if not minors:
        lines.append("*No minor issues found.*")
    else:
        for i, mi in enumerate(minors, 1):
            lines += [
                f"### Mi.{i} — [{mi.get('module')}] {mi.get('title')}",
                f"- **Fix**: {mi.get('suggested_fix')}",
                "",
            ]

    lines += [
        "",
        "## Suggested Fix Order",
        "",
        "1. Resolve all Blocker issues first.",
        "2. Seed more official law chunks to improve citation quality.",
        "3. Implement Playwright browser automation for UI smoke tests.",
        "4. Tune community case deduplication threshold.",
        "",
        "## Affected Files",
        "",
        "- `src/api/recommendation_routes.py`",
        "- `src/api/retrieval_routes.py`",
        "- `src/mongodb/mongo_storage.py`",
        "- `src/recommenders/next_best_action.py`",
        "- `frontend/src/pages/SimilarCases.tsx`",
    ]

    with open(fix_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[Fix plan] Written to: {fix_path}")
    return str(fix_path)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 60)
    print("PHASE 24 - GEMINI LOCALHOST USER SIMULATION QA RUNNER")
    print(f"  Time    : {today}")
    print(f"  Backend : {BACKEND_URL}")
    print(f"  Frontend: {FRONTEND_URL}")
    print(f"  Dry-run : {'YES' if IS_DRY_RUN else 'NO (live API calls)'}")
    print("=" * 60)

    # Initialise Gemini evaluator
    try:
        evaluator = GeminiQAEvaluator()
        print(f"[Gemini] Using model: {evaluator.model_name}")
    except Exception as exc:
        print(f"[ERROR] Cannot initialise Gemini evaluator: {exc}")
        return 1

    # Liveness check (skip in dry-run)
    if not IS_DRY_RUN:
        backend_up, frontend_up = check_services()
        print(f"  Backend : {'UP' if backend_up else 'DOWN'}")
        print(f"  Frontend: {'UP' if frontend_up else 'DOWN (api_fallback mode)'}")
        if not backend_up:
            print("\n[FAIL] Backend API is not reachable. Start it with:")
            print("  python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8001 --reload")
            return 1

    # Load scenarios
    scenarios_path = Path(__file__).parent.parent / "qa" / "ai_user_scenarios.json"
    if not scenarios_path.exists():
        print(f"[ERROR] Scenarios file not found: {scenarios_path}")
        return 1
    with open(scenarios_path, "r", encoding="utf-8") as f:
        scenarios: List[Dict[str, Any]] = json.load(f)
    print(f"[Scenarios] Loaded {len(scenarios)} test scenarios")

    results: Dict[str, dict] = {}
    evaluations: Dict[str, dict] = {}

    for sc in scenarios:
        sid = sc["id"]

        observed = run_scenario(sc)
        results[sid] = observed

        print(f"  [Gemini] Evaluating scenario {sid} ...")
        evaluation = evaluator.evaluate_scenario(sc, observed)
        evaluations[sid] = evaluation

        status = evaluation.get("status", "fail").upper()
        mvp_score = evaluation.get("scores", {}).get("mvp_completeness", 0)
        print(f"  [Gemini] Status={status} | MVP score={mvp_score}/10")

    print("\n[Report] Writing reports ...")
    md_rep, json_rep = write_reports(scenarios, results, evaluations, evaluator.model_name)

    print("\n" + "=" * 60)
    print("GEMINI QA RUN COMPLETE")
    print(f"  Markdown : {md_rep}")
    print(f"  JSON     : {json_rep}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
