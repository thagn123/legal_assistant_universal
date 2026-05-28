"""
Behavior-based Recommendation Engine for Legal Knowledge Assistant.

Analyses user interaction history to provide personalised suggestions:
  1. Proactive        — topics the user should revisit or explore next
  2. Sequential       — what to do after the user's latest action
  3. Peer-trending    — what users with similar interests are engaging with
  4. Daily digest     — personalised activity summary + ranked suggestions

Algorithms:
  - Recency-weighted scoring : exponential decay (half-life ≈ 8.7 days)
  - Sequential bigrams       : co-occurrence of consecutive action pairs
  - Peer discovery           : top-K overlapping legal domain interest sets
  - Cross-domain expansion   : predefined legal domain adjacency graph
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.mongodb.mongo_storage import VectorStorage

logger = logging.getLogger(__name__)

# ── Legal domain adjacency graph ─────────────────────────────────────────────
# Exploring domain A suggests exploring domain B
_DOMAIN_ADJACENCY: Dict[str, List[str]] = {
    "dat_dai":      ["hop_dong", "dan_su", "hanh_chinh"],
    "hop_dong":     ["dat_dai", "lao_dong", "doanh_nghiep"],
    "lao_dong":     ["hop_dong", "bao_hiem", "doanh_nghiep"],
    "doanh_nghiep": ["hop_dong", "thue", "lao_dong"],
    "dan_su":       ["dat_dai", "hop_dong", "gia_dinh"],
    "hinh_su":      ["dan_su", "hanh_chinh"],
    "hanh_chinh":   ["dat_dai", "hinh_su"],
    "bao_hiem":     ["lao_dong", "doanh_nghiep"],
    "thue":         ["doanh_nghiep", "hop_dong"],
    "gia_dinh":     ["dan_su", "dat_dai"],
}

# ── Sequential action transition graph ───────────────────────────────────────
# After action X, these (next_action, description) pairs are suggested
_ACTION_TRANSITIONS: Dict[str, List[Tuple[str, str]]] = {
    "view": [
        ("query",              "Đặt câu hỏi về tài liệu vừa xem"),
        ("situation_analysis", "Phân tích tình huống từ nội dung tài liệu"),
    ],
    "query": [
        ("case_recommendation",    "Tìm án lệ liên quan đến kết quả truy vấn"),
        ("risk_recommendation",    "Đánh giá rủi ro từ kết quả truy vấn"),
    ],
    "situation_analysis": [
        ("case_recommendation",        "Tìm án lệ tương tự để tham khảo"),
        ("document_recommendation",    "Xem văn bản luật liên quan"),
        ("risk_recommendation",        "Đánh giá rủi ro pháp lý của tình huống"),
    ],
    "case_recommendation": [
        ("situation_analysis",      "Phân tích tình huống dựa trên án lệ tìm được"),
        ("document_recommendation", "Nghiên cứu văn bản luật được trích dẫn"),
    ],
    "risk_recommendation": [
        ("checklist_generation",    "Tạo checklist tuân thủ để giảm rủi ro"),
        ("document_recommendation", "Xem văn bản luật liên quan đến rủi ro"),
    ],
    "save": [
        ("query",              "Tiếp tục nghiên cứu tài liệu đã lưu"),
        ("situation_analysis", "Phân tích tình huống từ tài liệu đã lưu"),
    ],
    "download": [
        ("situation_analysis", "Phân tích nội dung tài liệu vừa tải"),
        ("risk_recommendation","Đánh giá rủi ro từ hợp đồng vừa tải"),
    ],
    "document_recommendation": [
        ("view",  "Mở và đọc tài liệu được gợi ý"),
        ("query", "Đặt câu hỏi về nội dung tài liệu"),
    ],
    "__risk__": [
        ("checklist_generation", "Tạo checklist để giảm thiểu rủi ro phát hiện"),
    ],
    "__recommendation__": [
        ("situation_analysis", "Phân tích tình huống cụ thể hơn"),
    ],
}

_DECAY_RATE = 0.08            # exp(-0.08 * days) → half-life ≈ 8.7 days
_RE_ENGAGE_DAYS = 7           # suggest re-engagement after this many idle days
_MIN_WEIGHT_RE_ENGAGE = 0.25  # minimum historical weight to trigger re-engagement


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class UserBehaviorProfile:
    user_id: str
    law_type_weights: Dict[str, float]   # domain → recency-weighted score (0–1)
    action_frequencies: Dict[str, int]   # action_type → total count
    active_hours: List[int]              # top hours-of-day (0-23) by frequency
    total_interactions: int
    days_active: int
    top_law_type: str                    # primary legal domain
    last_active_iso: str                 # ISO timestamp of latest interaction
    adjacent_domains: List[str]          # unexplored domains adjacent to top_law_type


@dataclass
class BehaviorRecommendation:
    rec_id: str
    rec_type: str        # proactive | re_engage | cross_domain | sequential | peer_trending
    title: str
    description: str
    law_type: Optional[str]
    score: float         # 0.0 – 1.0
    reason: str
    action_hint: str     # suggested action the user should take


# ---------------------------------------------------------------------------
# BehaviorRecommender
# ---------------------------------------------------------------------------


class BehaviorRecommender:
    """
    Personalised recommendations driven by user interaction history.

    Usage:
        br = BehaviorRecommender(vector_storage)
        profile = br.build_user_profile("u_123")
        recs    = br.recommend_proactive("u_123")
        digest  = br.get_daily_digest("u_123")
    """

    def __init__(self, vector_storage: VectorStorage) -> None:
        self._vs = vector_storage

    # ── Core profile builder ─────────────────────────────────────────────────

    def build_user_profile(self, user_id: str) -> UserBehaviorProfile:
        """
        Construct a UserBehaviorProfile from the last 60 days of interactions.

        law_type_weights use exponential decay so that recent activity has a
        proportionally higher influence on the score.
        """
        history = self._vs.get_user_interaction_history(user_id, days=60, limit=200)
        action_freq = self._vs.get_user_action_frequency(user_id)
        active_hours = self._vs.get_user_active_hours(user_id)

        now = datetime.now(timezone.utc)
        law_type_weights: Dict[str, float] = {}
        last_active = now - timedelta(days=365)
        days_set: set[str] = set()

        for entry in history:
            ts = _parse_ts(entry.get("timestamp", ""))
            if ts is None:
                continue
            days_ago = max(0.0, (now - ts).total_seconds() / 86400)
            weight = math.exp(-_DECAY_RATE * days_ago)

            lt = (entry.get("context") or {}).get("law_type") or ""
            if lt:
                law_type_weights[lt] = law_type_weights.get(lt, 0.0) + weight

            if ts > last_active:
                last_active = ts
            days_set.add(ts.strftime("%Y-%m-%d"))

        # Normalise to [0, 1]
        max_w = max(law_type_weights.values(), default=1.0)
        law_type_weights = {
            k: round(v / max_w, 3)
            for k, v in sorted(law_type_weights.items(), key=lambda x: -x[1])
        }

        top_law_type = next(iter(law_type_weights), "general")

        explored = set(law_type_weights.keys())
        adjacent = [d for d in _DOMAIN_ADJACENCY.get(top_law_type, []) if d not in explored]

        return UserBehaviorProfile(
            user_id=user_id,
            law_type_weights=law_type_weights,
            action_frequencies=action_freq,
            active_hours=active_hours[:5],
            total_interactions=len(history),
            days_active=len(days_set),
            top_law_type=top_law_type,
            last_active_iso=last_active.isoformat(),
            adjacent_domains=adjacent,
        )

    # ── Proactive recommendations ────────────────────────────────────────────

    def recommend_proactive(
        self,
        user_id: str,
        limit: int = 6,
    ) -> List[BehaviorRecommendation]:
        """
        Return proactive suggestions based on user history patterns:
          - re_engage   : domains with high historical weight but no recent activity
          - cross_domain: adjacent legal domains not yet explored
          - proactive   : globally trending domains the user hasn't visited
        """
        profile = self.build_user_profile(user_id)
        recent_law_types = set(
            self._vs.get_user_law_types_since(user_id, days=_RE_ENGAGE_DAYS)
        )

        recs: List[BehaviorRecommendation] = []

        # ── Re-engage: historical interest but idle recently ─────────────────
        for lt, weight in profile.law_type_weights.items():
            if weight >= _MIN_WEIGHT_RE_ENGAGE and lt not in recent_law_types:
                recs.append(BehaviorRecommendation(
                    rec_id=f"re_engage_{lt}",
                    rec_type="re_engage",
                    title=f"Tiếp tục nghiên cứu {_law_label(lt)}",
                    description=(
                        f"Bạn đã từng quan tâm đến lĩnh vực {_law_label(lt)}. "
                        f"Có thể có các văn bản pháp lý mới hoặc thay đổi liên quan."
                    ),
                    law_type=lt,
                    score=round(weight * 0.9, 3),
                    reason=f"Lĩnh vực bạn từng tìm hiểu nhưng chưa xem trong {_RE_ENGAGE_DAYS} ngày qua (điểm: {weight:.0%}).",
                    action_hint=f"Tìm kiếm văn bản luật hoặc phân tích tình huống về {_law_label(lt)}",
                ))

        # ── Cross-domain: adjacent but unexplored ────────────────────────────
        for adjacent in profile.adjacent_domains[:3]:
            recs.append(BehaviorRecommendation(
                rec_id=f"cross_domain_{adjacent}",
                rec_type="cross_domain",
                title=f"Khám phá thêm: {_law_label(adjacent)}",
                description=(
                    f"Dựa trên mối quan tâm của bạn về {_law_label(profile.top_law_type)}, "
                    f"lĩnh vực {_law_label(adjacent)} thường liên quan và có thể hữu ích."
                ),
                law_type=adjacent,
                score=round(profile.law_type_weights.get(profile.top_law_type, 0.5) * 0.6, 3),
                reason=f"Lĩnh vực pháp lý liền kề với {_law_label(profile.top_law_type)} mà bạn chưa khám phá.",
                action_hint=f"Phân tích một tình huống pháp lý liên quan đến {_law_label(adjacent)}",
            ))

        # ── Trending: popular domains user hasn't engaged with ───────────────
        trending = self._vs.get_trending_law_types(limit=5)
        explored = set(profile.law_type_weights.keys())
        for i, lt in enumerate(trending):
            if lt not in explored:
                recs.append(BehaviorRecommendation(
                    rec_id=f"trending_{lt}",
                    rec_type="proactive",
                    title=f"Xu hướng pháp lý: {_law_label(lt)}",
                    description=(
                        f"Nhiều người dùng đang tìm hiểu về {_law_label(lt)}. "
                        f"Lĩnh vực này có thể liên quan đến nhu cầu của bạn."
                    ),
                    law_type=lt,
                    score=round(max(0.3, 0.55 - i * 0.05), 3),
                    reason="Lĩnh vực đang được nhiều người dùng trên nền tảng quan tâm.",
                    action_hint=f"Tìm hiểu các văn bản pháp lý cơ bản về {_law_label(lt)}",
                ))

        # ── Web Search Alert: Cost-free DuckDuckGo live updates ────────────────
        if profile.top_law_type and profile.top_law_type != "general":
            from src.utils.web_search import search_duckduckgo_free
            
            domain_label = _law_label(profile.top_law_type)
            search_query = f"\"mới nhất\" site:thuvienphapluat.vn \"{domain_label}\""
            try:
                search_results = search_duckduckgo_free(search_query, limit=2)
                for j, res in enumerate(search_results):
                    title = res["title"]
                    if " - Thư Viện Pháp Luật" in title:
                        title = title.replace(" - Thư Viện Pháp Luật", "")
                    if "Thư Viện Pháp Luật" in title:
                        title = title.replace("Thư Viện Pháp Luật", "")
                    title = title.strip(" -|")
                    
                    recs.append(BehaviorRecommendation(
                        rec_id=f"web_alert_{profile.top_law_type}_{j}",
                        rec_type="proactive",
                        title=f"Cập nhật: {title[:75]}...",
                        description=res["snippet"] or f"Tin tức trực tuyến mới nhận về lĩnh vực {domain_label}.",
                        law_type=profile.top_law_type,
                        score=round(max(0.65, 0.85 - j * 0.1), 3),
                        reason=f"Phát hiện tin tức pháp lý trực tuyến mới liên quan đến lĩnh vực quan tâm nhất của bạn ({domain_label}).",
                        action_hint=f"Xem nguồn: {res['url']}",
                    ))
            except Exception as e:
                logger.warning("Failed to fetch proactive web alert: %s", e)

        recs.sort(key=lambda r: r.score, reverse=True)
        return recs[:limit]

    # ── Sequential next-action suggestions ──────────────────────────────────

    def recommend_next_action(
        self,
        user_id: str,
        last_action_type: str,
        current_law_type: Optional[str] = None,
        limit: int = 3,
    ) -> List[BehaviorRecommendation]:
        """
        Suggest the next logical action based on what the user just did.

        Two signals are combined:
          1. Predefined action-transition graph (high baseline quality)
          2. Historical bigram co-occurrence from the user's own behaviour
        """
        recs: List[BehaviorRecommendation] = []
        seen: set[str] = set()

        # ── Predefined transitions ────────────────────────────────────────────
        for i, (next_action, title) in enumerate(_ACTION_TRANSITIONS.get(last_action_type, [])):
            rec_id = f"seq_{last_action_type}_{next_action}"
            if rec_id in seen:
                continue
            seen.add(rec_id)
            recs.append(BehaviorRecommendation(
                rec_id=rec_id,
                rec_type="sequential",
                title=title,
                description=_seq_description(last_action_type, next_action, current_law_type),
                law_type=current_law_type,
                score=round(0.85 - i * 0.1, 3),
                reason=f"Bước tiếp theo tự nhiên sau hành động '{_action_label(last_action_type)}'.",
                action_hint=_action_hint(next_action, current_law_type),
            ))

        # ── Historical bigrams from user's own sequence ──────────────────────
        bigrams = self._vs.get_user_action_bigrams(user_id, limit=20)
        for bg in bigrams:
            if bg.get("first_action") != last_action_type:
                continue
            rec_id = f"hist_seq_{bg['second_action']}"
            if rec_id in seen:
                continue
            seen.add(rec_id)
            count = bg.get("count", 1)
            recs.append(BehaviorRecommendation(
                rec_id=rec_id,
                rec_type="sequential",
                title=f"Bạn thường làm tiếp: {_action_label(bg['second_action'])}",
                description=(
                    f"Dựa trên thói quen của bạn, sau khi {_action_label(last_action_type)} "
                    f"bạn thường thực hiện {_action_label(bg['second_action'])}."
                ),
                law_type=current_law_type,
                score=round(min(0.78, count * 0.13), 3),
                reason=f"Bạn đã thực hiện chuỗi hành động này {count} lần trước đây.",
                action_hint=_action_hint(bg["second_action"], current_law_type),
            ))

        recs.sort(key=lambda r: r.score, reverse=True)
        return recs[:limit]

    # ── Peer-trending recommendations ────────────────────────────────────────

    def recommend_from_peers(
        self,
        user_id: str,
        limit: int = 5,
    ) -> List[BehaviorRecommendation]:
        """
        Find users with a similar law_type profile, then return documents/topics
        those peers are engaging with that the current user hasn't seen.
        """
        profile = self.build_user_profile(user_id)
        top_domains = list(profile.law_type_weights.keys())[:3]

        peer_ids = self._vs.find_peer_users(user_id, top_domains, limit=20)
        if not peer_ids:
            return []

        user_viewed = set(self._vs.get_user_viewed_docs(user_id, limit=100))
        trending = self._vs.get_trending_content_for_peers(
            peer_user_ids=peer_ids,
            exclude_doc_ids=list(user_viewed),
            days=14,
            limit=limit * 2,
        )

        recs: List[BehaviorRecommendation] = []
        for i, item in enumerate(trending[:limit]):
            lt = item.get("law_type") or (top_domains[0] if top_domains else None)
            peer_count = item.get("peer_count", 1)
            doc_id = item.get("doc_id", f"doc_{i}")
            recs.append(BehaviorRecommendation(
                rec_id=f"peer_{doc_id}",
                rec_type="peer_trending",
                title=f"Tài liệu phổ biến trong nhóm bạn ({peer_count} người xem)",
                description=(
                    f"Người dùng có hồ sơ pháp lý tương tự đang nghiên cứu tài liệu này. "
                    f"Được {peer_count} người dùng cùng nhóm quan tâm trong 14 ngày qua."
                ),
                law_type=lt,
                score=round(min(0.95, peer_count * 0.15), 3),
                reason="Xu hướng trong nhóm người dùng có quan tâm pháp lý tương tự bạn.",
                action_hint=f"Xem tài liệu {doc_id} và phân tích nội dung",
            ))

        return recs

    # ── Daily digest ─────────────────────────────────────────────────────────

    def get_daily_digest(self, user_id: str) -> Dict[str, Any]:
        """
        Personalised daily summary combining profile snapshot, activity stats,
        proactive suggestions, peer-trending items, and sequential hints.
        """
        profile = self.build_user_profile(user_id)
        proactive = self.recommend_proactive(user_id, limit=4)
        peer_recs = self.recommend_from_peers(user_id, limit=3)

        recent_history = self._vs.get_user_interaction_history(user_id, days=7, limit=50)
        action_counts: Dict[str, int] = {}
        for entry in recent_history:
            at = entry.get("action_type", "other")
            action_counts[at] = action_counts.get(at, 0) + 1

        sequential: List[BehaviorRecommendation] = []
        if recent_history:
            last_entry = recent_history[0]
            last_action = last_entry.get("action_type", "")
            last_lt = (last_entry.get("context") or {}).get("law_type")
            if last_action:
                sequential = self.recommend_next_action(user_id, last_action, last_lt, limit=2)

        all_recs = proactive + sequential + peer_recs
        all_recs.sort(key=lambda r: r.score, reverse=True)

        profile_summary = {
            "top_law_type": profile.top_law_type,
            "top_law_type_label": _law_label(profile.top_law_type),
            "total_interactions": profile.total_interactions,
            "days_active": profile.days_active,
            "law_type_weights": profile.law_type_weights,
            "last_active": profile.last_active_iso,
            "active_hours": profile.active_hours,
            "adjacent_domains": [
                {"law_type": d, "label": _law_label(d)}
                for d in profile.adjacent_domains
            ],
        }

        # Build a personalized digest block
        top_label = _law_label(profile.top_law_type)
        digest_summary = f"Bạn đang tập trung tra cứu {top_label.lower()} và các tranh chấp liên quan."
        focus_area = "Chuẩn bị các hồ sơ tài liệu và bằng chứng pháp lý liên quan."
        if profile.top_law_type == "lao_dong":
            digest_summary = "Bạn đang tập trung tra cứu luật lao động và các tranh chấp liên quan đến sa thải, hợp đồng."
            focus_area = "Tập trung chuẩn bị bằng chứng về thời hạn hợp đồng và nghĩa vụ bồi thường."
        elif profile.top_law_type == "gia_dinh":
            digest_summary = "Bạn đang tập trung tra cứu luật hôn nhân gia đình và các tranh chấp liên quan đến quyền nuôi con."
            focus_area = "Tập trung chuẩn bị bằng chứng về điều kiện tài chính và nơi cư trú ổn định."

        digest_block = {
            "summary": digest_summary,
            "recommendation_focus": focus_area,
            "proactive_tips": [
                f"Nên lưu trữ đầy đủ các tài liệu, giao dịch liên quan đến {top_label.lower()}."
            ]
        }

        return {
            "user_id": user_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "profile_summary": profile_summary,
            "profile": profile_summary,  # FE & Test compatibility
            "activity_last_7_days": {
                "total": len(recent_history),
                "by_action": action_counts,
            },
            "recommendations": [
                {
                    "rec_id": r.rec_id,
                    "rec_type": r.rec_type,
                    "title": r.title,
                    "description": r.description,
                    "law_type": r.law_type,
                    "score": r.score,
                    "reason": r.reason,
                    "action_hint": r.action_hint,
                }
                for r in all_recs[:8]
            ],
            "digest": digest_block,  # FE & Test compatibility
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LAW_TYPE_LABELS: Dict[str, str] = {
    "dat_dai":      "Luật Đất đai",
    "hop_dong":     "Hợp đồng",
    "lao_dong":     "Luật Lao động",
    "doanh_nghiep": "Doanh nghiệp",
    "dan_su":       "Dân sự",
    "hinh_su":      "Hình sự",
    "hanh_chinh":   "Hành chính",
    "bao_hiem":     "Bảo hiểm",
    "thue":         "Thuế",
    "gia_dinh":     "Gia đình",
    "general":      "Pháp lý chung",
}

_ACTION_LABELS: Dict[str, str] = {
    "view":                    "Xem tài liệu",
    "save":                    "Lưu tài liệu",
    "query":                   "Tra cứu pháp lý",
    "download":                "Tải tài liệu",
    "situation_analysis":      "Phân tích tình huống",
    "case_recommendation":     "Tìm án lệ",
    "risk_recommendation":     "Đánh giá rủi ro",
    "document_recommendation": "Gợi ý tài liệu",
    "checklist_generation":    "Tạo checklist",
    "__risk__":                "Phân tích rủi ro",
    "__recommendation__":      "Gợi ý tài liệu",
    "__situation__":           "Phân tích tình huống",
    "__cases__":               "Tìm án lệ",
}


def _law_label(law_type: str) -> str:
    return _LAW_TYPE_LABELS.get(law_type, law_type.replace("_", " ").title())


def _action_label(action_type: str) -> str:
    return _ACTION_LABELS.get(action_type, action_type.replace("_", " ").title())


def _seq_description(from_action: str, to_action: str, law_type: Optional[str]) -> str:
    domain = f" về {_law_label(law_type)}" if law_type else ""
    return (
        f"Sau khi {_action_label(from_action)}{domain}, "
        f"bước tiếp theo được gợi ý là: {_action_label(to_action)}."
    )


def _action_hint(action_type: str, law_type: Optional[str]) -> str:
    domain = f" về {_law_label(law_type)}" if law_type else ""
    hints: Dict[str, str] = {
        "query":               f"Nhập câu hỏi pháp lý cụ thể{domain} vào ô Chat",
        "situation_analysis":  f"Mô tả tình huống pháp lý của bạn{domain} để nhận đánh giá",
        "case_recommendation": f"Nhập tình huống để tìm án lệ tương tự{domain}",
        "risk_recommendation": f"Mô tả tình huống hoặc xem rủi ro từ lịch sử{domain}",
        "document_recommendation": "Xem danh sách tài liệu được gợi ý phù hợp với hồ sơ của bạn",
        "checklist_generation": "Chọn loại doanh nghiệp và giao dịch để tạo checklist tuân thủ",
        "view":                "Mở tài liệu và đọc nội dung chi tiết",
        "save":                "Lưu tài liệu quan trọng vào thư viện cá nhân",
        "download":            "Tải tài liệu về máy để xem offline",
    }
    return hints.get(action_type, f"Thực hiện {_action_label(action_type)}{domain}")


def _parse_ts(ts_str: str) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None
