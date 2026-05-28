"""
Seed data cho Video Demo — LexAI Competition.

Tạo interaction history phong phú cho demo_user_001 với lĩnh vực lao_dong
để Dashboard hiển thị đầy đủ: behavior chart, top domain, proactive recommendations.

Usage:
    python scripts/seed_video_demo.py
    python scripts/seed_video_demo.py --user demo_user_001 --base-url http://localhost:8001
    python scripts/seed_video_demo.py --dry-run   # chỉ in ra không gửi request
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("requests not installed. Run: pip install requests")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Demo interaction data — lao_dong dominant
# ---------------------------------------------------------------------------

DEMO_USER = "demo_user_001"

# Seed cả hai user: demo_user_001 (default) + demo_user_employee (persona switcher "Người lao động")
ALL_USERS = ["demo_user_001", "demo_user_employee"]

INTERACTIONS = [
    # Lao dong — primary domain (7 events)
    {"doc_id": "demo_case_labor_dismissal_001", "action_type": "view",
     "context": {"law_type": "lao_dong", "module": "similar_cases", "domain": "lao_dong"}},
    {"doc_id": "demo_case_labor_dismissal_002", "action_type": "recommendation_click",
     "context": {"law_type": "lao_dong", "module": "similar_cases", "domain": "lao_dong"}},
    {"doc_id": "demo_checklist_labor_termination", "action_type": "recommendation_useful",
     "context": {"law_type": "lao_dong", "module": "checklists", "domain": "lao_dong"}},
    {"doc_id": "demo_evidence_gap_labor", "action_type": "save",
     "context": {"law_type": "lao_dong", "module": "evidence_gap", "domain": "lao_dong"}},
    {"doc_id": "demo_case_labor_dismissal_003", "action_type": "view",
     "context": {"law_type": "lao_dong", "module": "similar_cases", "domain": "lao_dong"}},
    {"doc_id": "demo_timeline_labor_lawsuit", "action_type": "save",
     "context": {"law_type": "lao_dong", "module": "timeline", "domain": "lao_dong"}},
    {"doc_id": "demo_risk_labor_compensation", "action_type": "recommendation_click",
     "context": {"law_type": "lao_dong", "module": "risks", "domain": "lao_dong"}},
    # Dan su — secondary domain (3 events)
    {"doc_id": "demo_case_civil_contract", "action_type": "view",
     "context": {"law_type": "dan_su", "module": "similar_cases", "domain": "dan_su"}},
    {"doc_id": "demo_checklist_civil", "action_type": "recommendation_click",
     "context": {"law_type": "dan_su", "module": "checklists", "domain": "dan_su"}},
    {"doc_id": "demo_template_civil", "action_type": "view",
     "context": {"law_type": "dan_su", "module": "templates", "domain": "dan_su"}},
    # Hop dong — tertiary (2 events)
    {"doc_id": "demo_template_labor_contract", "action_type": "view",
     "context": {"law_type": "hop_dong", "module": "templates", "domain": "hop_dong"}},
    {"doc_id": "demo_clause_labor", "action_type": "recommendation_click",
     "context": {"law_type": "hop_dong", "module": "clause_search", "domain": "hop_dong"}},
]


def check_backend(base_url: str) -> bool:
    try:
        resp = requests.get(f"{base_url}/health", timeout=5)
        return resp.status_code < 500
    except Exception as e:
        print(f"[ERROR] Backend unreachable at {base_url}: {e}")
        return False


def seed_interactions(base_url: str, user_id: str, dry_run: bool) -> int:
    """Seed interaction events. Returns number of successful POSTs."""
    ok = 0
    headers = {"X-User-ID": user_id, "Content-Type": "application/json"}

    for i, item in enumerate(INTERACTIONS):
        payload = {
            "user_id": user_id,
            "doc_id": item["doc_id"],
            "action_type": item["action_type"],
            "context": item["context"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if dry_run:
            print(f"  [DRY] {item['action_type']:30s} {item['doc_id']}")
            ok += 1
            continue

        try:
            resp = requests.post(
                f"{base_url}/interactions/log",
                json=payload,
                headers=headers,
                timeout=8,
            )
            status = "OK" if resp.status_code < 300 else f"HTTP {resp.status_code}"
            print(f"  [{status}] {item['action_type']:30s} {item['doc_id']}")
            if resp.status_code < 300:
                ok += 1
            time.sleep(0.15)
        except Exception as e:
            print(f"  [FAIL] {item['doc_id']}: {e}")

    return ok


def verify_profile(base_url: str, user_id: str) -> None:
    """Fetch and print behavior profile to verify seeding worked."""
    try:
        resp = requests.get(
            f"{base_url}/recommendations/behavior/profile",
            headers={"X-User-ID": user_id},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            weights = data.get("law_type_weights", {})
            top = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]
            print(f"\n  Behavior profile for {user_id}:")
            for domain, score in top:
                bar = "#" * int(score * 20)
                print(f"    {domain:15s} {bar} {score:.3f}")
        else:
            print(f"  Profile fetch returned HTTP {resp.status_code}")
    except Exception as e:
        print(f"  Could not fetch profile: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo interaction data for LexAI video demo")
    parser.add_argument("--user", default=DEMO_USER, help="User ID to seed (default: demo_user_001)")
    parser.add_argument("--base-url", default="http://localhost:8001", help="Backend base URL")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without sending")
    args = parser.parse_args()

    print("=" * 60)
    print("LexAI Video Demo — Seed Script")
    print(f"  User     : {args.user}")
    print(f"  Backend  : {args.base_url}")
    print(f"  Dry run  : {args.dry_run}")
    print("=" * 60)

    if not args.dry_run:
        if not check_backend(args.base_url):
            print("\n[ABORT] Start backend first: python -m uvicorn src.api.app:app --port 8001 --reload")
            sys.exit(1)
        print("[OK] Backend reachable\n")

    users_to_seed = [args.user] if args.user != DEMO_USER else ALL_USERS
    total_ok = 0

    for uid in users_to_seed:
        print(f"\nSeeding {len(INTERACTIONS)} interactions for {uid}...\n")
        ok = seed_interactions(args.base_url, uid, args.dry_run)
        total_ok += ok
        print(f"  Done: {ok}/{len(INTERACTIONS)} seeded for {uid}")

    print(f"\nTotal: {total_ok} interactions seeded across {len(users_to_seed)} user(s)")

    if not args.dry_run:
        for uid in users_to_seed:
            print(f"\nVerifying behavior profile for {uid}...")
            verify_profile(args.base_url, uid)
        print("\n[READY] Dashboard should now show lao_dong as top domain.")
        print("Persona switcher in Header also has 'Nguoi lao dong' pre-seeded.")
        print("Open http://localhost:3000 to verify before recording.")


if __name__ == "__main__":
    main()
