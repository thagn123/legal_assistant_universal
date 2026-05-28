"""
Seed Phase 23 demo personas into MongoDB / SQLite.

Creates 3 demo users with pre-seeded interaction history and community case
patterns so the personalized recommendation demo works out of the box.

Usage:
    python scripts/seed_phase23_demo_personas.py
    python scripts/seed_phase23_demo_personas.py --base-url http://localhost:8001
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Demo persona definitions
# ---------------------------------------------------------------------------

DEMO_PERSONAS = {
    "demo_user_family": {
        "label": "Hồ sơ gia đình",
        "description": "Người dùng quan tâm đến ly hôn, nuôi con, chia tài sản",
        "interactions": [
            # click on similar cases
            {"doc_id": "demo_case_divorce_custody", "action_type": "recommendation_click",
             "context": {"module": "similar_cases", "law_type": "dan_su", "domain": "gia_dinh"}},
            # useful on evidence gap
            {"doc_id": "evidence_gap_demo", "action_type": "recommendation_useful",
             "context": {"module": "evidence_gap", "law_type": "dan_su"}},
            # save child custody
            {"doc_id": "demo_case_divorce_custody", "action_type": "save",
             "context": {"module": "similar_cases", "law_type": "gia_dinh"}},
            # analysis clicks
            {"doc_id": "demo_law_hngd_81", "action_type": "view",
             "context": {"law_type": "gia_dinh", "module": "law_search"}},
            {"doc_id": "demo_law_hngd_59", "action_type": "view",
             "context": {"law_type": "gia_dinh", "module": "law_search"}},
            {"doc_id": "demo_law_hngd_81", "action_type": "save",
             "context": {"law_type": "gia_dinh", "module": "law_search"}},
            {"doc_id": "template_divorce", "action_type": "recommendation_click",
             "context": {"module": "templates", "law_type": "gia_dinh"}},
            {"doc_id": "checklist_custody", "action_type": "recommendation_click",
             "context": {"module": "checklists", "law_type": "gia_dinh"}},
        ],
        "interested_domains": ["gia_dinh", "dan_su"],
        "situation_queries": [
            "Tôi muốn ly hôn, có hai con nhỏ và muốn biết tài sản chung sẽ được chia như thế nào.",
            "Quyền nuôi con sau khi ly hôn theo luật Việt Nam.",
        ],
    },
    "demo_user_employee": {
        "label": "Hồ sơ người lao động",
        "description": "Người dùng quan tâm đến sa thải, lương, bảo hiểm xã hội",
        "interactions": [
            {"doc_id": "demo_law_ld_36", "action_type": "recommendation_click",
             "context": {"module": "law_search", "law_type": "lao_dong"}},
            {"doc_id": "timeline_labor", "action_type": "recommendation_useful",
             "context": {"module": "timeline", "law_type": "lao_dong"}},
            {"doc_id": "demo_case_labor_termination", "action_type": "save",
             "context": {"module": "similar_cases", "law_type": "lao_dong"}},
            {"doc_id": "demo_law_ld_36", "action_type": "view",
             "context": {"law_type": "lao_dong", "module": "law_search"}},
            {"doc_id": "checklist_labor", "action_type": "recommendation_click",
             "context": {"module": "checklists", "law_type": "lao_dong"}},
            {"doc_id": "risk_termination", "action_type": "view",
             "context": {"law_type": "lao_dong", "module": "risks"}},
            {"doc_id": "demo_law_ld_36", "action_type": "save",
             "context": {"law_type": "lao_dong", "module": "law_search"}},
        ],
        "interested_domains": ["lao_dong"],
        "situation_queries": [
            "Tôi bị công ty sa thải không báo trước, không trả lương tháng cuối và không chi trả trợ cấp thôi việc.",
            "Quyền lợi của người lao động khi bị chấm dứt hợp đồng lao động đơn phương.",
        ],
    },
    "demo_user_sme": {
        "label": "Hồ sơ doanh nghiệp nhỏ",
        "description": "Người dùng quan tâm đến hợp đồng, điều khoản phạt, tranh chấp",
        "interactions": [
            {"doc_id": "demo_clause_penalty", "action_type": "recommendation_click",
             "context": {"module": "contract", "law_type": "hop_dong"}},
            {"doc_id": "demo_clause_termination", "action_type": "recommendation_useful",
             "context": {"module": "clause_search", "law_type": "hop_dong"}},
            {"doc_id": "demo_case_land_handwritten", "action_type": "recommendation_dismiss",
             "context": {"module": "similar_cases", "law_type": "dat_dai"}},
            {"doc_id": "demo_law_ds_328", "action_type": "view",
             "context": {"law_type": "hop_dong", "module": "law_search"}},
            {"doc_id": "template_service_contract", "action_type": "recommendation_click",
             "context": {"module": "templates", "law_type": "hop_dong"}},
            {"doc_id": "checklist_contract", "action_type": "recommendation_click",
             "context": {"module": "checklists", "law_type": "hop_dong"}},
            {"doc_id": "demo_clause_penalty", "action_type": "save",
             "context": {"law_type": "hop_dong", "module": "contract"}},
        ],
        "interested_domains": ["hop_dong", "doanh_nghiep"],
        "situation_queries": [
            "Hợp đồng dịch vụ của chúng tôi bị vi phạm điều khoản thanh toán, muốn biết có thể áp dụng phạt vi phạm không.",
            "Cách xử lý khi đối tác vi phạm hợp đồng và không thanh toán tiền dịch vụ.",
        ],
    },
}

# Community case patterns to seed
COMMUNITY_PATTERNS = [
    {
        "pattern_id": "ccp_family_divorce_001",
        "summary": "Người dùng muốn ly hôn, nuôi con nhỏ và chia tài sản chung.",
        "legal_domain": "gia_dinh",
        "user_goal": ["divorce", "child_custody", "asset_division"],
        "resolution_summary": "Cần chuẩn bị hồ sơ ly hôn, chứng cứ điều kiện nuôi con, tài liệu chứng minh tài sản chung/riêng.",
        "recommended_steps": [
            "Thu thập giấy đăng ký kết hôn và giấy khai sinh của con",
            "Chuẩn bị chứng cứ thu nhập, nơi ở, thời gian chăm sóc con",
            "Phân loại tài sản chung và tài sản riêng có giấy tờ chứng minh",
            "Nộp đơn tại Tòa án nhân dân cấp huyện nơi cư trú",
        ],
        "citations": ["Luật Hôn nhân và Gia đình 2014, Điều 81", "Luật Hôn nhân và Gia đình 2014, Điều 59"],
        "tags": ["ly_hon", "nuoi_con", "chia_tai_san", "gia_dinh"],
        "source_user_segment": "parent_custody",
        "popularity": {"impressions": 12, "clicks": 5, "saves": 3, "useful": 4, "not_useful": 0},
    },
    {
        "pattern_id": "ccp_labor_termination_001",
        "summary": "Người lao động bị chấm dứt hợp đồng không có thông báo trước và không nhận trợ cấp.",
        "legal_domain": "lao_dong",
        "user_goal": ["labor_termination", "compensation", "social_insurance"],
        "resolution_summary": "Có thể yêu cầu bồi thường, trợ cấp thôi việc và phục hồi quyền lợi bảo hiểm xã hội.",
        "recommended_steps": [
            "Thu thập hợp đồng lao động, bảng lương, quyết định chấm dứt",
            "Xác nhận thời gian đóng BHXH từ cơ quan BHXH",
            "Gửi khiếu nại đến người sử dụng lao động trong 15 ngày",
            "Nộp đơn đến Phòng Lao động Thương binh Xã hội nếu không giải quyết",
        ],
        "citations": ["Bộ luật Lao động 2019, Điều 36", "Bộ luật Lao động 2019, Điều 41"],
        "tags": ["sa_thai", "cham_dut_hop_dong", "tro_cap_thoi_viec", "lao_dong"],
        "source_user_segment": "employee_dismissal",
        "popularity": {"impressions": 18, "clicks": 8, "saves": 5, "useful": 7, "not_useful": 1},
    },
    {
        "pattern_id": "ccp_contract_breach_001",
        "summary": "Doanh nghiệp nhỏ bị đối tác vi phạm hợp đồng dịch vụ, không thanh toán tiền.",
        "legal_domain": "hop_dong",
        "user_goal": ["contract_enforcement", "payment_dispute", "penalty_clause"],
        "resolution_summary": "Có thể áp dụng điều khoản phạt vi phạm và yêu cầu bồi thường thiệt hại.",
        "recommended_steps": [
            "Rà soát điều khoản thanh toán và phạt vi phạm trong hợp đồng",
            "Gửi thông báo vi phạm và yêu cầu thanh toán bằng văn bản",
            "Thu thập chứng cứ thiệt hại thực tế (invoice, biên nhận, email)",
            "Khởi kiện tại Tòa án hoặc Trung tâm Trọng tài Thương mại nếu không thỏa thuận được",
        ],
        "citations": ["Bộ luật Dân sự 2015, Điều 418", "Bộ luật Dân sự 2015, Điều 360"],
        "tags": ["vi_pham_hop_dong", "phat_vi_pham", "boi_thuong", "hop_dong"],
        "source_user_segment": "sme_contract_dispute",
        "popularity": {"impressions": 9, "clicks": 4, "saves": 2, "useful": 3, "not_useful": 0},
    },
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------

def seed_via_api(base_url: str) -> None:
    """Seed interactions via the HTTP API (for a running server)."""
    import urllib.request
    import urllib.error

    print(f"[Phase 23 Seed] Using deployed API: {base_url}")

    for user_id, persona in DEMO_PERSONAS.items():
        print(f"\n  Seeding persona: {user_id} ({persona['label']})")
        for i, interaction in enumerate(persona["interactions"]):
            payload = json.dumps({
                "doc_id": interaction["doc_id"],
                "action_type": interaction["action_type"],
                "context": interaction["context"],
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/interactions/log",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-User-ID": user_id,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp.read()
                print(f"    [{i+1}/{len(persona['interactions'])}] {interaction['action_type']} on {interaction['doc_id'][:30]} ✓")
            except Exception as exc:
                print(f"    [{i+1}/{len(persona['interactions'])}] FAILED: {exc}")
            time.sleep(0.05)

    print("\n[Phase 23 Seed] Seeding community patterns...")
    for pattern in COMMUNITY_PATTERNS:
        try:
            payload = json.dumps(pattern).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/recommendations/community-patterns",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-User-ID": "admin",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp.read()
                print(f"  Community pattern {pattern['pattern_id']} seeded ✓")
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print(f"  Community pattern endpoint not yet available, seeding direct")
                    _seed_direct(pattern)
                else:
                    print(f"  Community pattern {pattern['pattern_id']} HTTP {e.code}")
        except Exception as exc:
            print(f"  Community pattern FAILED: {exc}")
            _seed_direct(pattern)


def seed_direct() -> None:
    """Seed directly via Python imports (no server needed)."""
    print("[Phase 23 Seed] Seeding directly via Python imports (no server needed)")

    # Try MongoDB first, fall back to SQLite
    storage = None
    try:
        from src.mongodb.mongo_storage import VectorStorage
        storage = VectorStorage()
        print("  Using MongoDB storage")
    except Exception as exc:
        print(f"  MongoDB unavailable ({exc}), using SQLite fallback")
        try:
            from src.runtime.storage import StorageLayer
            from pathlib import Path
            db_path = Path(__file__).parent.parent / "data" / "lka.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            storage = StorageLayer(str(db_path))
            print(f"  Using SQLite at {db_path}")
        except Exception as exc2:
            print(f"  SQLite also failed: {exc2}")
            return

    # Seed interactions per persona
    for user_id, persona in DEMO_PERSONAS.items():
        print(f"\n  Seeding persona: {user_id} ({persona['label']})")
        for i, interaction in enumerate(persona["interactions"]):
            try:
                # Spread interactions over the past 30 days for realistic decay
                days_ago = (len(persona["interactions"]) - i) * 2
                ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
                storage.log_interaction(
                    user_id=user_id,
                    doc_id=interaction["doc_id"],
                    action_type=interaction["action_type"],
                    context=interaction["context"],
                )
                print(f"    [{i+1}/{len(persona['interactions'])}] {interaction['action_type']} ✓")
            except Exception as exc:
                print(f"    [{i+1}/{len(persona['interactions'])}] FAILED: {exc}")

    # Seed community patterns
    print("\n  Seeding community case patterns...")
    for pattern in COMMUNITY_PATTERNS:
        try:
            storage.save_community_case_pattern(
                pattern_id=pattern["pattern_id"],
                summary=pattern["summary"],
                legal_domain=pattern["legal_domain"],
                user_goal=pattern["user_goal"],
                resolution_summary=pattern["resolution_summary"],
                recommended_steps=pattern["recommended_steps"],
                citations=pattern["citations"],
                tags=pattern["tags"],
                source_user_segment=pattern.get("source_user_segment", ""),
            )
            # Seed popularity signals
            for signal, count in pattern.get("popularity", {}).items():
                for _ in range(min(count, 20)):  # cap at 20 to avoid slow loop
                    try:
                        storage.increment_community_case_signal(pattern["pattern_id"], signal)
                    except Exception:
                        pass
            print(f"    Community pattern {pattern['pattern_id']} seeded ✓")
        except Exception as exc:
            print(f"    Community pattern {pattern['pattern_id']} FAILED: {exc}")

    print("\n[Phase 23 Seed] Done.")


def _seed_direct(pattern: dict) -> None:
    """Thin wrapper for seeding a single community pattern directly."""
    try:
        from src.mongodb.mongo_storage import VectorStorage
        vs = VectorStorage()
        vs.save_community_case_pattern(
            pattern_id=pattern["pattern_id"],
            summary=pattern["summary"],
            legal_domain=pattern["legal_domain"],
            user_goal=pattern.get("user_goal", []),
            resolution_summary=pattern.get("resolution_summary", ""),
            recommended_steps=pattern.get("recommended_steps", []),
            citations=pattern.get("citations", []),
            tags=pattern.get("tags", []),
            source_user_segment=pattern.get("source_user_segment", ""),
        )
    except Exception as exc:
        print(f"    _seed_direct failed: {exc}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Phase 23 demo personas")
    parser.add_argument("--base-url", default="", help="Deployed API base URL (empty = direct import mode)")
    args = parser.parse_args()

    if args.base_url:
        seed_via_api(args.base_url)
    else:
        seed_direct()
