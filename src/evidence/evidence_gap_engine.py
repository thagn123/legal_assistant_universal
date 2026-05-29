from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from src.evidence.evidence_extractor import aggregate_evidence_facts, extract_evidence_facts
from src.evidence.evidence_normalizer import (
    aliases_for_schema,
    find_schemas_by_titles_or_ids,
    get_required_evidence,
    normalize_domain,
    normalize_text,
)
from src.evidence.evidence_schemas import (
    CONTRADICTED,
    MISSING,
    PRESENT,
    UNCERTAIN,
    EvidenceAssessment,
    EvidenceFact,
    EvidenceSchema,
)


@dataclass
class EvidenceGapAnalysis:
    domain: str
    coverage_score: float
    summary: str
    present_evidence: List[EvidenceAssessment] = field(default_factory=list)
    missing_evidence: List[EvidenceAssessment] = field(default_factory=list)
    uncertain_evidence: List[EvidenceAssessment] = field(default_factory=list)
    contradictions: List[EvidenceAssessment] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    normalized_facts: List[EvidenceFact] = field(default_factory=list)
    matched_aliases: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self, debug: bool = False) -> Dict[str, Any]:
        data = {
            "domain": self.domain,
            "coverage_score": self.coverage_score,
            "summary": self.summary,
            "present_evidence": [item.to_dict() for item in self.present_evidence],
            "missing_evidence": [item.to_dict() for item in self.missing_evidence],
            "uncertain_evidence": [item.to_dict() for item in self.uncertain_evidence],
            "contradictions": [item.to_dict() for item in self.contradictions],
            "recommendations": list(self.recommendations),
        }
        if debug:
            data["debug"] = {
                "normalized_facts": [fact.to_dict() for fact in self.normalized_facts],
                "matched_aliases": list(self.matched_aliases),
            }
        return data


_PRIORITY_WEIGHT = {"high": 2.0, "medium": 1.0, "low": 0.5}


def analyze_evidence_gap(
    user_input: str,
    domain: str = "general",
    facts: Optional[List[str]] = None,
) -> EvidenceGapAnalysis:
    normalized_domain = normalize_domain(domain)
    required = get_required_evidence(normalized_domain, user_input)
    normalized_domain = normalize_domain(normalized_domain)

    extracted = extract_evidence_facts(
        text=user_input or "",
        domain=normalized_domain,
        facts=facts or [],
        evidence_items=required,
    )
    by_id = aggregate_evidence_facts(extracted)
    has_any_input = bool((user_input or "").strip() or any((facts or [])))

    present: List[EvidenceAssessment] = []
    missing: List[EvidenceAssessment] = []
    uncertain: List[EvidenceAssessment] = []
    contradicted: List[EvidenceAssessment] = []
    matched_aliases: List[Dict[str, Any]] = []

    for schema in required:
        fact = by_id.get(schema.evidence_id)
        assessment = _assessment_for_schema(schema, fact, has_any_input)
        if fact and fact.matched_alias:
            matched_aliases.append(
                {
                    "evidence_id": schema.evidence_id,
                    "alias": fact.matched_alias,
                    "status": fact.status,
                    "matched_text": fact.matched_text,
                }
            )
        if assessment.status == PRESENT:
            present.append(assessment)
        elif assessment.status == MISSING:
            missing.append(assessment)
        elif assessment.status == CONTRADICTED:
            contradicted.append(assessment)
        else:
            uncertain.append(assessment)

    coverage = _coverage_score(required, present, uncertain, contradicted)
    recs = _build_recommendations(present, missing, uncertain, contradicted)
    recs = filter_contradictory_recommendations(recs, present)

    return EvidenceGapAnalysis(
        domain=normalized_domain,
        coverage_score=coverage,
        summary=_summary(present, missing, uncertain, contradicted, coverage),
        present_evidence=present,
        missing_evidence=missing,
        uncertain_evidence=uncertain,
        contradictions=contradicted,
        recommendations=recs,
        normalized_facts=list(by_id.values()),
        matched_aliases=matched_aliases,
    )


def filter_contradictory_recommendations(
    recommendations: Iterable[str],
    present_evidence: Iterable[object],
) -> List[str]:
    """Remove or rewrite recommendations that ask for evidence the user already has."""
    present_values: List[object] = list(present_evidence)
    present_titles = [_present_value_title(item) for item in present_values]
    schemas = _schemas_from_present_values(present_values)

    filtered: List[str] = []
    seen: set[str] = set()
    for rec in recommendations:
        text = rec.strip()
        if not text:
            continue
        conflicting_schema = _find_conflicting_schema(text, schemas)
        if conflicting_schema and _is_supplement_action(text):
            replacement = (
                f"Bạn đã có {conflicting_schema.title}. Hãy kiểm tra tính hợp lệ, "
                "bản gốc/bản sao công chứng, thời điểm lập và nội dung thể hiện trên tài liệu."
            )
            key = normalize_text(replacement)
            if key not in seen:
                seen.add(key)
                filtered.append(replacement)
            continue

        title_conflict = _find_conflicting_title(text, present_titles)
        if title_conflict and _is_supplement_action(text):
            replacement = (
                f"Bạn đã có {title_conflict}. Hãy kiểm tra tính hợp lệ, bản gốc/bản sao "
                "và thông tin chính trên tài liệu."
            )
            key = normalize_text(replacement)
            if key not in seen:
                seen.add(key)
                filtered.append(replacement)
            continue

        key = normalize_text(text)
        if key not in seen:
            seen.add(key)
            filtered.append(text)
    return filtered


def _assessment_for_schema(
    schema: EvidenceSchema,
    fact: Optional[EvidenceFact],
    has_any_input: bool,
) -> EvidenceAssessment:
    if fact:
        status = fact.status
        reason = {
            PRESENT: "Người dùng đã nêu rõ đang có tài liệu này.",
            MISSING: "Người dùng đã nêu rõ chưa có/mất/không giữ tài liệu này.",
            UNCERTAIN: "Người dùng có nhắc đến nhưng chưa đủ rõ tình trạng tài liệu.",
            CONTRADICTED: "Có tín hiệu vừa có vừa thiếu/mất tài liệu, cần hỏi lại.",
        }.get(status, "")
        return EvidenceAssessment(
            evidence_id=schema.evidence_id,
            title=schema.title,
            category=schema.category,
            domain=schema.domain,
            priority=schema.priority,
            status=status,
            matched_text=fact.matched_text,
            matched_alias=fact.matched_alias,
            confidence=fact.confidence,
            reason=reason,
            aliases=list(schema.aliases),
        )

    if not has_any_input:
        status = MISSING
        reason = "Chưa có thông tin đầu vào về tài liệu này."
    elif schema.priority == "high":
        status = MISSING
        reason = "Đây là chứng cứ ưu tiên cao nhưng chưa thấy người dùng nêu đã có."
    else:
        status = UNCERTAIN
        reason = "Chưa rõ người dùng có tài liệu hỗ trợ này hay chưa."

    return EvidenceAssessment(
        evidence_id=schema.evidence_id,
        title=schema.title,
        category=schema.category,
        domain=schema.domain,
        priority=schema.priority,
        status=status,
        confidence=0.0 if status == MISSING else 0.35,
        reason=reason,
        aliases=list(schema.aliases),
    )


def _coverage_score(
    required: List[EvidenceSchema],
    present: List[EvidenceAssessment],
    uncertain: List[EvidenceAssessment],
    contradicted: List[EvidenceAssessment],
) -> float:
    total = sum(_PRIORITY_WEIGHT.get(item.priority, 1.0) for item in required)
    if total <= 0:
        return 0.0
    present_ids = {item.evidence_id for item in present}
    uncertain_ids = {item.evidence_id for item in uncertain}
    contradicted_ids = {item.evidence_id for item in contradicted}
    score = 0.0
    for item in required:
        weight = _PRIORITY_WEIGHT.get(item.priority, 1.0)
        if item.evidence_id in present_ids:
            score += weight
        elif item.evidence_id in contradicted_ids:
            score += weight * 0.2
        elif item.evidence_id in uncertain_ids:
            score += weight * 0.1
    return round(min(score / total, 1.0), 2)


def _summary(
    present: List[EvidenceAssessment],
    missing: List[EvidenceAssessment],
    uncertain: List[EvidenceAssessment],
    contradicted: List[EvidenceAssessment],
    coverage: float,
) -> str:
    present_high = sum(1 for item in present if item.priority == "high")
    missing_high = sum(1 for item in missing if item.priority == "high")
    if contradicted:
        return (
            f"Độ phủ chứng cứ: {round(coverage * 100)}%. Có {len(contradicted)} mục mâu thuẫn "
            "cần xác minh lại trước khi kết luận thiếu hay đã có."
        )
    if present:
        return (
            f"Độ phủ chứng cứ: {round(coverage * 100)}%. Bạn đã có {present_high or len(present)} "
            f"chứng cứ quan trọng. Cần bổ sung {missing_high} mục ưu tiên cao "
            f"và xác minh thêm {len(uncertain)} mục."
        )
    if missing_high:
        return (
            f"Độ phủ chứng cứ: {round(coverage * 100)}%. Chưa thấy chứng cứ ưu tiên cao nào; "
            f"cần bổ sung {missing_high} mục quan trọng và xác minh {len(uncertain)} mục."
        )
    return f"Độ phủ chứng cứ: {round(coverage * 100)}%. Cần xác minh thêm {len(uncertain)} mục."


_CONTRADICTION_CLARIFICATIONS: Dict[str, str] = {
    "land_certificate": (
        "Sổ đỏ/Giấy chứng nhận QSDĐ của bạn: đang giữ bản gốc, "
        "chỉ có photo/bản sao, hay bản gốc đã bị mất hoặc đang do người khác giữ?"
    ),
    "labor_contract": (
        "Hợp đồng lao động: bạn đang giữ bản gốc có chữ ký hai bên, "
        "chỉ có bản scan/ảnh chụp, hay chưa bao giờ được công ty cấp bản giấy?"
    ),
    "marriage_certificate": (
        "Giấy đăng ký kết hôn: đang giữ bản gốc, "
        "chỉ có bản sao công chứng, hay đã thất lạc/chưa đăng ký chính thức?"
    ),
    "transfer_document": (
        "Giấy chuyển nhượng/mua bán: đang giữ bản gốc có đủ chữ ký các bên, "
        "chỉ có photo, hay giấy chỉ viết tay chưa công chứng?"
    ),
    "payment_proof": (
        "Biên lai/chứng từ thanh toán: bạn có biên nhận gốc hoặc sao kê chuyển khoản, "
        "hay chỉ thanh toán tiền mặt không có giấy tờ?"
    ),
    "birth_certificate": (
        "Giấy khai sinh: đang giữ bản gốc, "
        "chỉ có bản sao công chứng, hay chưa làm giấy khai sinh?"
    ),
}


def _contradiction_clarification(item: EvidenceAssessment) -> str:
    custom = _CONTRADICTION_CLARIFICATIONS.get(item.evidence_id)
    if custom:
        return custom
    return (
        f"Làm rõ tình trạng {item.title}: bạn đang giữ bản gốc, "
        "bản sao/photo, hay tài liệu đã bị mất hoặc người khác đang giữ?"
    )


def _build_recommendations(
    present: List[EvidenceAssessment],
    missing: List[EvidenceAssessment],
    uncertain: List[EvidenceAssessment],
    contradicted: List[EvidenceAssessment],
) -> List[str]:
    recommendations: List[str] = []
    for item in contradicted:
        recommendations.append(_contradiction_clarification(item))
    for item in missing:
        verb = "Bổ sung" if item.priority == "high" else "Xem xét bổ sung"
        recommendations.append(f"{verb} {item.title}.")
    for item in uncertain[:3]:
        recommendations.append(f"Xác minh bạn có {item.title} hay không; nếu có, kiểm tra bản gốc/bản sao.")
    for item in present[:3]:
        if item.priority == "high":
            recommendations.append(
                f"Bạn đã có {item.title}. Hãy kiểm tra tính hợp lệ, bản gốc/bản sao công chứng và nội dung chính."
            )
    return recommendations[:8]


def _present_value_title(value: object) -> str:
    if isinstance(value, EvidenceAssessment):
        return value.title
    if isinstance(value, dict):
        return str(value.get("title") or value.get("item") or value.get("evidence_id") or "")
    return str(value or "")


def _schemas_from_present_values(values: Iterable[object]) -> List[EvidenceSchema]:
    ids_and_titles: List[object] = []
    for value in values:
        if isinstance(value, EvidenceAssessment):
            ids_and_titles.extend([value.evidence_id, value.title])
        elif isinstance(value, dict):
            ids_and_titles.extend([value.get("evidence_id"), value.get("title"), value.get("item")])
        else:
            ids_and_titles.append(value)
    return find_schemas_by_titles_or_ids(v for v in ids_and_titles if v)


def _find_conflicting_schema(text: str, schemas: Iterable[EvidenceSchema]) -> Optional[EvidenceSchema]:
    folded = normalize_text(text)
    for schema in schemas:
        for alias in aliases_for_schema(schema):
            needle = normalize_text(alias)
            if needle and needle in folded:
                return schema
    return None


def _find_conflicting_title(text: str, titles: Iterable[str]) -> str:
    folded = normalize_text(text)
    for title in titles:
        needle = normalize_text(title)
        if needle and (needle in folded or any(part in folded for part in needle.split("/") if len(part.strip()) > 4)):
            return title
    return ""


_SUPPLEMENT_PATTERNS = [
    r"(bo sung|can bo sung|can chuan bi|chuan bi|thu thap|can thu thap|nop them|cung cap them|can co)",
    r"(nen|can|phai)\s.{0,20}(giay|so\b|bien lai|hop dong|chung tu|tai lieu|van ban)",
    r"viec co\s.{0,30}(la|rat)\s.{0,10}(quan trong|can thiet)",
    r"(xin cap|lam lai|lay them)",
    r"(nen co|hay co|can phai co)",
]


def _is_supplement_action(text: str) -> bool:
    folded = normalize_text(text)
    return any(re.search(pat, folded) for pat in _SUPPLEMENT_PATTERNS)
