from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.engine.query_planner import QueryPlanner
from src.services.timeline_tracker import TimelineTracker


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "research": [
        "tra cứu", "tìm hiểu", "quy định gì", "luật nào", "điều nào quy định",
        "có luật nào", "được phép không", "có quyền không", "hỏi về",
        "muốn biết", "cho biết", "thông tin về",
    ],
    "analysis": [
        "phân tích", "đánh giá", "nhận xét", "tư vấn", "rủi ro gì",
        "nguy cơ gì", "có vấn đề gì", "có rủi ro không", "hợp lệ không",
        "hợp pháp không", "vi phạm không", "đúng luật không",
    ],
    "draft": [
        "soạn hợp đồng", "mẫu hợp đồng", "viết hợp đồng", "ký hợp đồng",
        "cần soạn", "nhờ soạn", "soạn thảo", "điều khoản cần có",
        "mẫu đơn", "viết đơn",
    ],
    "next_step": [
        "nên làm gì", "phải làm gì", "bước tiếp theo", "làm sao bây giờ",
        "giải quyết thế nào", "hướng xử lý", "xử lý ra sao", "làm thế nào",
        "có thể làm gì", "cần làm gì tiếp", "hướng đi",
    ],
    "warning": [
        "cảnh báo", "phản đối", "khiếu nại", "tố cáo", "khởi kiện",
        "đòi bồi thường", "yêu cầu bồi thường", "kiện ra toà", "nộp đơn kiện",
    ],
}

_INTENT_LABELS: Dict[str, str] = {
    "research":  "Tra cứu quy định pháp lý",
    "analysis":  "Phân tích và đánh giá tình huống",
    "draft":     "Soạn thảo văn bản / hợp đồng",
    "next_step": "Tìm bước tiếp theo cần làm",
    "warning":   "Khiếu nại / đòi quyền lợi",
}

# ---------------------------------------------------------------------------
# Fact extraction — concrete sentences with event-like structure
# ---------------------------------------------------------------------------

_FACT_INDICATORS = [
    "tôi", "chúng tôi", "hàng xóm", "bên bán", "bên mua", "ông", "bà",
    "công ty", "đã", "bị", "không", "đang", "sẽ", "mua", "bán", "thuê",
    "ký", "giao", "nhận", "trả", "đòi", "từ chối", "lấn", "chiếm",
    "vi phạm", "không trả", "bị sa thải", "bị đuổi", "không thanh toán",
]

_SENT_SPLIT = re.compile(r'[.!?;,\n]+')

# ---------------------------------------------------------------------------
# Risk level: stage-based heuristic
# ---------------------------------------------------------------------------

_HIGH_RISK_STAGES  = {"violation_occurred", "pre_litigation", "in_litigation", "awaiting_decision"}
_MED_RISK_STAGES   = {"dispute_emerging", "negotiation", "post_decision"}


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class SituationProfile:
    domain: str
    domain_confidence: float
    dispute_type: str
    stage: str
    stage_label: str
    stage_confidence: float
    intent: str
    intent_label: str
    entities: Dict[str, List[str]]
    extracted_facts: List[str]
    risk_level: str          # "low" | "medium" | "high"
    confidence: float        # average of domain + stage confidence
    law_references: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_intent(query: str) -> Tuple[str, str]:
    q = query.lower()
    scores: Dict[str, int] = {}
    for intent, keywords in _INTENT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in q)
        if hits:
            scores[intent] = hits
    if not scores:
        return "next_step", _INTENT_LABELS["next_step"]
    best = max(scores, key=lambda k: scores[k])
    return best, _INTENT_LABELS[best]


def _extract_facts(query: str, extra_facts: List[str]) -> List[str]:
    sentences = [s.strip() for s in _SENT_SPLIT.split(query) if len(s.strip()) > 15]
    facts = [s for s in sentences if any(ind in s.lower() for ind in _FACT_INDICATORS)]
    # Merge in user-supplied facts that aren't already captured
    seen = {f.lower() for f in facts}
    for ef in extra_facts:
        if ef.lower() not in seen and len(ef) > 5:
            facts.append(ef)
            seen.add(ef.lower())
    return facts[:6]


def _compute_risk(stage: str) -> str:
    if stage in _HIGH_RISK_STAGES:
        return "high"
    if stage in _MED_RISK_STAGES:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class SituationClassifier:
    """
    Lightweight (<20ms, no I/O) situation classifier.

    Combines QueryPlanner (domain / entities / dispute_type) with
    TimelineTracker (legal stage) and adds user-intent detection +
    extracted-facts extraction.
    """

    def __init__(self) -> None:
        self._planner  = QueryPlanner()
        self._timeline = TimelineTracker()

    def classify(
        self,
        situation: str,
        facts: Optional[List[str]] = None,
        domain_hint: Optional[str] = None,
    ) -> SituationProfile:
        if facts is None:
            facts = []

        plan     = self._planner.plan(situation, law_type_hint=domain_hint)
        timeline = self._timeline.track(
            situation=situation,
            domain=plan.detected_domain,
            facts=facts,
        )

        intent, intent_label = _detect_intent(situation)
        extracted_facts      = _extract_facts(situation, facts)
        risk_level           = _compute_risk(timeline.stage)
        confidence           = round((plan.domain_confidence + timeline.stage_confidence) / 2, 2)

        # Import lazily to avoid circular dependency
        from src.services.legal_journey_service import _DOMAIN_LAW_HINTS
        law_refs = _DOMAIN_LAW_HINTS.get(plan.detected_domain, [])

        return SituationProfile(
            domain=plan.detected_domain,
            domain_confidence=plan.domain_confidence,
            dispute_type=plan.dispute_type,
            stage=timeline.stage,
            stage_label=timeline.stage_label,
            stage_confidence=timeline.stage_confidence,
            intent=intent,
            intent_label=intent_label,
            entities=plan.extracted_entities,
            extracted_facts=extracted_facts,
            risk_level=risk_level,
            confidence=confidence,
            law_references=law_refs,
        )
