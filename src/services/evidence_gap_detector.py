from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.evidence.evidence_extractor import extract_evidence_facts
from src.evidence.evidence_gap_engine import analyze_evidence_gap
from src.evidence.evidence_normalizer import (
    REQUIRED_EVIDENCE,
    alias_matches_text,
    aliases_for_schema,
    all_evidence_schemas,
    get_required_evidence,
    normalize_domain,
)
from src.evidence.evidence_schemas import (
    CONTRADICTED,
    MISSING,
    PRESENT,
    UNCERTAIN,
    EvidenceAssessment,
    EvidenceSchema,
)


@dataclass
class EvidenceItem:
    item: str
    priority: str  # "high" | "medium" | "low"
    category: str = ""
    evidence_id: str = ""
    status: str = UNCERTAIN
    matched_text: str = ""
    matched_alias: str = ""
    confidence: float = 0.0
    reason: str = ""
    category_label: str = ""


@dataclass
class EvidenceGapResult:
    domain: str
    missing_evidence: List[EvidenceItem]
    strong_evidence: List[str]
    weak_evidence: List[str]
    coverage_score: float
    priority_items: List[EvidenceItem]
    advice: str = ""
    present_evidence: List[EvidenceItem] = field(default_factory=list)
    uncertain_evidence: List[EvidenceItem] = field(default_factory=list)
    contradictions: List[EvidenceItem] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    debug: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""


def _to_legacy_item(assessment: EvidenceAssessment) -> EvidenceItem:
    return EvidenceItem(
        item=assessment.title,
        priority=assessment.priority,
        category=assessment.category,
        evidence_id=assessment.evidence_id,
        status=assessment.status,
        matched_text=assessment.matched_text,
        matched_alias=assessment.matched_alias,
        confidence=assessment.confidence,
        reason=assessment.reason,
    )


def _schema_to_legacy_item(schema: EvidenceSchema) -> EvidenceItem:
    return EvidenceItem(
        item=schema.title,
        priority=schema.priority,
        category=schema.category,
        evidence_id=schema.evidence_id,
        status=UNCERTAIN,
    )


_CHECKLISTS: Dict[str, List[EvidenceItem]] = {
    domain: [_schema_to_legacy_item(schema) for schema in schemas]
    for domain, schemas in REQUIRED_EVIDENCE.items()
}

_DOMAIN_ADVICE_BASE = {
    "dat_dai": (
        "Trong tranh chấp đất đai, giấy chứng nhận quyền sử dụng đất, giấy tờ chuyển nhượng, "
        "chứng từ thanh toán và xác nhận của UBND địa phương là nhóm chứng cứ lõi. "
        "Hòa giải tại UBND cấp xã là bước bắt buộc theo pháp luật đất đai trước khi có thể khởi kiện."
    ),
    "hop_dong": (
        "Trong tranh chấp hợp đồng, ưu tiên thu thập: bản hợp đồng/thỏa thuận gốc, "
        "chứng từ thanh toán, trao đổi bằng văn bản (email, tin nhắn) và biên bản bàn giao. "
        "Thông báo vi phạm bằng văn bản có xác nhận nhận là căn cứ pháp lý quan trọng."
    ),
    "lao_dong": (
        "Hợp đồng lao động, thông báo chấm dứt hợp đồng và chứng từ lương là ba tài liệu cốt lõi. "
        "Người lao động có quyền khiếu nại trong vòng 1 năm kể từ ngày phát sinh tranh chấp — "
        "đừng để quá thời hiệu."
    ),
    "gia_dinh": (
        "Trong vụ ly hôn, ưu tiên: giấy đăng ký kết hôn, giấy khai sinh của con, "
        "chứng cứ về điều kiện chăm sóc con (thu nhập, chỗ ở, thời gian dành cho con) "
        "và danh sách tài sản chung/riêng kèm chứng từ. "
        "Tòa án sẽ tiến hành hòa giải bắt buộc trước khi ra phán quyết."
    ),
    "dan_su": (
        "Trong tranh chấp dân sự và thừa kế, ưu tiên làm rõ quyền sở hữu và quan hệ pháp lý: "
        "di chúc, giấy khai sinh, hợp đồng mua bán và chứng từ liên quan tài sản tranh chấp. "
        "Thời hiệu khởi kiện thường là 3 năm — xác định ngay mốc thời gian để không bỏ lỡ."
    ),
    "general": (
        "Hãy mô tả chi tiết hơn tình huống pháp lý để nhận checklist chứng cứ phù hợp với lĩnh vực cụ thể."
    ),
}


def _build_dynamic_advice(
    domain: str,
    present: "List[EvidenceItem]",
    missing: "List[EvidenceItem]",
    coverage_score: float,
    contradictions: "List[EvidenceItem]",
) -> str:
    parts: List[str] = [_DOMAIN_ADVICE_BASE.get(domain, _DOMAIN_ADVICE_BASE["general"])]

    present_titles = [e.item for e in present[:3]]
    high_missing = [e.item for e in missing if e.priority == "high"][:3]

    if present_titles:
        parts.append(
            f"Bạn đã có: {', '.join(present_titles)}. "
            "Hãy đảm bảo tất cả tài liệu là bản gốc hoặc bản sao có công chứng."
        )

    if contradictions:
        parts.append(
            f"Cần làm rõ mâu thuẫn về: {', '.join(e.item for e in contradictions[:2])} "
            "— hãy trả lời câu hỏi này để hệ thống đánh giá chính xác hơn."
        )

    if high_missing:
        parts.append(f"Ưu tiên thu thập ngay: {', '.join(high_missing)}.")

    if coverage_score >= 0.7:
        parts.append(
            "Độ phủ chứng cứ tốt — tập trung vào chất lượng (bản gốc, công chứng, thời điểm lập)."
        )
    elif coverage_score < 0.3:
        parts.append(
            "Độ phủ chứng cứ còn thấp — cần thu thập thêm tài liệu ưu tiên cao trước khi tiến hành vụ kiện."
        )

    return " ".join(parts)

_CATEGORY_KEYWORDS: Dict[str, List[str]] = {}
for schemas in REQUIRED_EVIDENCE.values():
    for schema in schemas:
        _CATEGORY_KEYWORDS.setdefault(schema.category, [])
        _CATEGORY_KEYWORDS[schema.category].extend(schema.aliases)
for category, aliases in list(_CATEGORY_KEYWORDS.items()):
    _CATEGORY_KEYWORDS[category] = list(dict.fromkeys(aliases))


def _extract_claimed_evidence(situation: str) -> List[str]:
    """Backward-compatible helper: return snippets the user says are present."""
    facts = extract_evidence_facts(
        situation,
        domain="general",
        evidence_items=all_evidence_schemas(),
    )
    return [fact.matched_text for fact in facts if fact.status == PRESENT]


def _keywords_match(fact: str, item: EvidenceItem) -> bool:
    """Backward-compatible phrase/alias matcher used by existing tests."""
    aliases = [item.item, item.evidence_id.replace("_", " ") if item.evidence_id else ""]
    aliases.extend(_CATEGORY_KEYWORDS.get(item.category, []))
    for schema in get_required_evidence("general") + [
        schema for schemas in REQUIRED_EVIDENCE.values() for schema in schemas
    ]:
        if item.evidence_id and schema.evidence_id == item.evidence_id:
            aliases.extend(aliases_for_schema(schema))
        elif item.category and schema.category == item.category:
            aliases.extend(schema.aliases)
    return alias_matches_text(fact, aliases)


class EvidenceGapDetector:
    def detect_gaps(
        self,
        domain: str,
        facts: Optional[List[str]],
        situation: str = "",
    ) -> EvidenceGapResult:
        normalized_domain = normalize_domain(domain)
        analysis = analyze_evidence_gap(
            user_input=situation or "",
            domain=normalized_domain,
            facts=facts or [],
        )

        present = [_to_legacy_item(item) for item in analysis.present_evidence]
        missing = [_to_legacy_item(item) for item in analysis.missing_evidence]
        uncertain = [_to_legacy_item(item) for item in analysis.uncertain_evidence]
        contradictions = [_to_legacy_item(item) for item in analysis.contradictions]
        strong = [item.item for item in present if item.priority == "high"]
        weak = [item.item for item in present if item.priority != "high"]
        priority_items = [item for item in missing if item.priority == "high"]

        return EvidenceGapResult(
            domain=analysis.domain,
            missing_evidence=missing,
            strong_evidence=list(dict.fromkeys(strong)),
            weak_evidence=list(dict.fromkeys(weak)),
            coverage_score=analysis.coverage_score,
            priority_items=priority_items,
            advice=_build_dynamic_advice(
                analysis.domain, present, missing, analysis.coverage_score, contradictions
            ),
            present_evidence=present,
            uncertain_evidence=uncertain,
            contradictions=contradictions,
            recommendations=analysis.recommendations,
            debug={
                "normalized_facts": [fact.to_dict() for fact in analysis.normalized_facts],
                "matched_aliases": analysis.matched_aliases,
            },
            summary=analysis.summary,
        )
