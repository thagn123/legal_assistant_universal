"""
QueryPlanner — Stage 1 of the Legal Intelligence Orchestration Pipeline.

Responsibilities (all deterministic, zero LLM calls):
  - Detect legal domain from query text (keyword scoring)
  - Extract structured entities (law refs, parties, amounts, dates)
  - Classify dispute type
  - Select retrieval strategy based on intent + entity profile
  - Generate 2–4 query variants for multi-pass fusion retrieval

Design philosophy:
  Fast (<10ms), reproducible, observable.
  No external calls — pure text processing.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Domain detection vocabulary
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "dat_dai": [
        "đất", "sổ đỏ", "quyền sử dụng đất", "qsd đất", "thửa đất", "mảnh đất",
        "lấn chiếm", "tranh chấp đất", "thu hồi đất", "bồi thường đất",
        "giải phóng mặt bằng", "ranh giới", "đất đai", "giấy chứng nhận qsd",
        "gcn", "luật đất đai",
    ],
    "hop_dong": [
        "hợp đồng", "điều khoản", "ký kết", "vi phạm hợp đồng", "phạt vi phạm",
        "bồi thường thiệt hại", "đơn phương chấm dứt", "bên mua", "bên bán",
        "thanh toán", "giao hàng", "dịch vụ", "thuê nhà", "mua bán", "xây dựng",
    ],
    "lao_dong": [
        "lao động", "người lao động", "người sử dụng lao động", "sa thải", "thôi việc",
        "nghỉ việc", "lương", "tiền lương", "bảo hiểm xã hội", "bhxh",
        "hợp đồng lao động", "nghỉ phép", "kỷ luật", "tai nạn lao động",
        "luật lao động",
    ],
    "doanh_nghiep": [
        "doanh nghiệp", "công ty", "cổ đông", "cổ phần", "thành lập công ty",
        "giải thể", "phá sản", "vốn điều lệ", "điều lệ công ty", "hội đồng quản trị",
        "ban giám đốc", "tnhh", "cổ phần",
    ],
    "dan_su": [
        "dân sự", "tranh chấp dân sự", "tài sản", "thừa kế", "di chúc",
        "hôn nhân", "ly hôn", "nuôi con", "quyền tài sản", "bồi thường",
        "thiệt hại ngoài hợp đồng",
    ],
    "hinh_su": [
        "hình sự", "tội phạm", "bị cáo", "truy tố", "xét xử", "tù giam",
        "phạt tù", "điều tra", "khởi tố", "cơ quan điều tra", "viện kiểm sát",
    ],
    "hanh_chinh": [
        "hành chính", "cơ quan nhà nước", "khiếu nại hành chính", "tố cáo",
        "quyết định hành chính", "ủy ban nhân dân", "ubnd", "giấy phép",
        "xử phạt vi phạm hành chính",
    ],
    "gia_dinh": [
        "hôn nhân", "ly hôn", "nuôi con", "cấp dưỡng", "tài sản chung",
        "thừa kế", "gia đình", "vợ chồng", "con cái", "nhận con nuôi",
    ],
}

_DISPUTE_TYPE_PATTERNS: Dict[str, List[str]] = {
    "tranh_chap_ranh_gioi":    ["ranh giới", "lấn chiếm", "tranh chấp đất"],
    "thu_hoi_dat_boi_thuong":  ["thu hồi", "bồi thường", "giải phóng mặt bằng"],
    "vi_pham_hop_dong":        ["vi phạm", "không thực hiện", "đơn phương chấm dứt", "phạt vi phạm"],
    "tranh_chap_lao_dong":     ["sa thải", "thôi việc", "tranh chấp lao động", "lương"],
    "tranh_chap_thua_ke":      ["thừa kế", "di chúc", "chia tài sản", "di sản"],
    "tranh_chap_hop_dong_mua_ban": ["mua bán", "thanh toán", "giao hàng", "bên mua", "bên bán"],
    "tranh_chap_thuong_mai":   ["thương mại", "kinh doanh", "hợp đồng thương mại"],
    "khieu_nai_hanh_chinh":    ["khiếu nại", "tố cáo", "quyết định hành chính"],
    "tranh_chap_hinh_su":      ["hình sự", "tố giác", "khởi tố", "tội phạm"],
}

# Domain → related domains (for cross-domain query expansion)
_DOMAIN_CONTEXT_TERMS: Dict[str, List[str]] = {
    "dat_dai":      ["quyền sử dụng đất", "luật đất đai 2024"],
    "hop_dong":     ["điều khoản hợp đồng", "bộ luật dân sự"],
    "lao_dong":     ["bộ luật lao động", "quan hệ lao động"],
    "doanh_nghiep": ["luật doanh nghiệp", "quản trị công ty"],
    "dan_su":       ["bộ luật dân sự", "quyền dân sự"],
    "hinh_su":      ["bộ luật hình sự", "tố tụng hình sự"],
    "hanh_chinh":   ["pháp luật hành chính", "tố tụng hành chính"],
}


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class QueryPlan:
    plan_id: str
    original_query: str
    detected_domain: str             # dat_dai | hop_dong | lao_dong | ...
    domain_confidence: float         # 0.0–1.0
    extracted_entities: Dict[str, List[str]]  # laws, parties, amounts, dates, locations
    dispute_type: str
    retrieval_strategy: List[str]    # ordered: ["vector", "bm25", "graph", "cases", "behavior"]
    query_variants: List[str]        # original + up to 3 paraphrases
    requires_graph_expansion: bool
    requires_case_retrieval: bool
    requires_risk_analysis: bool
    planned_at: str                  # ISO 8601

    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "detected_domain": self.detected_domain,
            "domain_confidence": self.domain_confidence,
            "dispute_type": self.dispute_type,
            "retrieval_strategy": self.retrieval_strategy,
            "entities": self.extracted_entities,
            "variants_count": len(self.query_variants),
        }


# ---------------------------------------------------------------------------
# QueryPlanner
# ---------------------------------------------------------------------------


class QueryPlanner:
    """
    Stage 1: deterministic query analysis and retrieval planning.

    No LLM calls, no external I/O. Runs in <10ms.

    Usage:
        planner = QueryPlanner()
        plan = planner.plan("Hàng xóm lấn 50cm đất sổ đỏ của tôi", law_type_hint="dat_dai")
    """

    def plan(
        self,
        query: str,
        law_type_hint: Optional[str] = None,
        session_context: Optional[object] = None,  # SessionContext, avoid circular import
    ) -> QueryPlan:
        """
        Build a QueryPlan from the raw query string.
        law_type_hint overrides domain detection if provided.
        session_context informs multi-turn continuity.
        """
        plan_id = f"qp_{uuid.uuid4().hex[:10]}"

        # 1. Domain detection
        detected_domain, domain_confidence = self._detect_domain(query, law_type_hint)

        # 2. Incorporate session continuity
        if session_context and hasattr(session_context, "law_type_preferences"):
            prefs: List[str] = session_context.law_type_preferences
            if detected_domain == "general" and prefs:
                detected_domain = prefs[0]
                domain_confidence = 0.55  # medium confidence from session history

        # 3. Entity extraction
        entities = self._extract_entities(query)

        # 4. Dispute classification
        dispute_type = self._classify_dispute(query, detected_domain)

        # 5. Retrieval strategy
        strategy = self._select_strategy(detected_domain, dispute_type, entities)

        # 6. Query variants
        variants = self._generate_variants(query, detected_domain, entities)

        return QueryPlan(
            plan_id=plan_id,
            original_query=query[:500],
            detected_domain=detected_domain,
            domain_confidence=domain_confidence,
            extracted_entities=entities,
            dispute_type=dispute_type,
            retrieval_strategy=strategy,
            query_variants=variants,
            requires_graph_expansion="graph" in strategy,
            requires_case_retrieval="cases" in strategy,
            requires_risk_analysis="risks" in strategy,
            planned_at=_now(),
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    def _detect_domain(
        self, query: str, hint: Optional[str]
    ) -> Tuple[str, float]:
        # Explicit hint wins
        if hint and hint in _DOMAIN_KEYWORDS:
            return hint, 1.0

        query_lower = query.lower()
        scores: Dict[str, int] = {}
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in query_lower)
            if hits:
                scores[domain] = hits

        if not scores:
            return "general", 0.25

        total = sum(scores.values())
        top_domain = max(scores, key=scores.__getitem__)
        confidence = round(scores[top_domain] / max(total, 1), 3)
        return top_domain, confidence

    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        entities: Dict[str, List[str]] = {
            "laws": [], "parties": [], "amounts": [], "dates": [], "locations": []
        }

        # Law / article references
        entities["laws"] = list(dict.fromkeys(re.findall(
            r"(?:Luật|Nghị định|Thông tư|Điều|Khoản|Điểm)\s+[\w\d\s\/\-\.]+?\d{4}",
            query, re.IGNORECASE,
        )))[:4]

        # Monetary amounts
        entities["amounts"] = list(dict.fromkeys(re.findall(
            r"\d[\d\.,]*\s*(?:tỷ|triệu|nghìn|ngàn|đồng|VNĐ|USD|%)",
            query, re.IGNORECASE,
        )))[:4]

        # Dates
        entities["dates"] = list(dict.fromkeys(re.findall(
            r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\b(?:năm\s*)?\d{4}\b",
            query,
        )))[:3]

        # Parties
        entities["parties"] = list(dict.fromkeys(re.findall(
            r"(?:nguyên đơn|bị đơn|người bán|người mua|chủ nhà|người thuê|"
            r"công ty\s+\w+|ông\s+\w+|bà\s+\w+)",
            query, re.IGNORECASE,
        )))[:3]

        # Locations
        entities["locations"] = list(dict.fromkeys(re.findall(
            r"(?:tại|ở|tỉnh|huyện|xã|phường|quận|thành phố)\s+[\w\s]{2,30}",
            query, re.IGNORECASE,
        )))[:3]

        return entities

    def _classify_dispute(self, query: str, domain: str) -> str:
        q = query.lower()
        for dtype, keywords in _DISPUTE_TYPE_PATTERNS.items():
            if any(kw in q for kw in keywords):
                return dtype
        return f"tranh_chap_{domain}"

    def _select_strategy(
        self,
        domain: str,
        dispute_type: str,
        entities: Dict[str, List[str]],
    ) -> List[str]:
        strategy = ["vector", "bm25"]  # always use hybrid base

        # Graph expansion for complex, multi-document disputes
        if domain in ("dat_dai", "dan_su", "doanh_nghiep") or entities["laws"]:
            strategy.append("graph")

        # Case retrieval for adversarial disputes
        if any(x in dispute_type for x in ["tranh_chap", "vi_pham", "khieu_nai"]):
            strategy.append("cases")

        # Risk analysis for contract / commercial disputes
        if domain in ("hop_dong", "doanh_nghiep", "lao_dong"):
            strategy.append("risks")

        # Behavior boost always (adds personalization)
        strategy.append("behavior")

        return strategy

    def _generate_variants(
        self,
        query: str,
        domain: str,
        entities: Dict[str, List[str]],
    ) -> List[str]:
        variants = [query]

        # Domain-enriched variant
        context_terms = _DOMAIN_CONTEXT_TERMS.get(domain, [])
        if context_terms:
            variants.append(f"{query} {context_terms[0]}")

        # Law-reference-focused variant
        if entities["laws"]:
            law_str = " ".join(entities["laws"][:2])
            enriched = f"{law_str}: {query[:120]}"
            variants.append(enriched)

        # Simplified variant (first 60 chars — catches short-form embedding matches)
        if len(query) > 80:
            variants.append(query[:80].rsplit(" ", 1)[0])

        return list(dict.fromkeys(variants))[:4]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
