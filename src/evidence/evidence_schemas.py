from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

PRESENT = "present"
MISSING = "missing"
UNCERTAIN = "uncertain"
CONTRADICTED = "contradicted"

EVIDENCE_STATUSES = {PRESENT, MISSING, UNCERTAIN, CONTRADICTED}


@dataclass(frozen=True)
class EvidenceSchema:
    evidence_id: str
    title: str
    category: str
    domain: str
    priority: str
    aliases: List[str] = field(default_factory=list)
    required: bool = True


@dataclass
class EvidenceFact:
    evidence_id: str
    status: str
    matched_text: str
    matched_alias: str
    confidence: float
    source: str = "situation"
    signals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "status": self.status,
            "matched_text": self.matched_text,
            "matched_alias": self.matched_alias,
            "confidence": self.confidence,
            "source": self.source,
            "signals": list(self.signals),
        }


@dataclass
class EvidenceAssessment:
    evidence_id: str
    title: str
    category: str
    domain: str
    priority: str
    status: str
    matched_text: str = ""
    matched_alias: str = ""
    confidence: float = 0.0
    reason: str = ""
    aliases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "title": self.title,
            "item": self.title,
            "category": self.category,
            "domain": self.domain,
            "priority": self.priority,
            "status": self.status,
            "matched_text": self.matched_text,
            "matched_alias": self.matched_alias,
            "confidence": self.confidence,
            "reason": self.reason,
        }


CATEGORY_LABELS: Dict[str, str] = {
    "title": "Giấy tờ giao dịch / quyền sử dụng",
    "confirmation": "Xác nhận của cơ quan địa phương",
    "certificate": "Giấy chứng nhận",
    "map": "Bản đồ / sơ đồ thửa đất",
    "witness": "Nhân chứng",
    "payment": "Chứng từ thanh toán",
    "contract": "Hợp đồng / thỏa thuận",
    "termination": "Quyết định / thông báo chấm dứt",
    "salary": "Chứng từ lương / thu nhập",
    "insurance": "Bảo hiểm xã hội",
    "income": "Chứng minh thu nhập",
    "marriage": "Giấy tờ hôn nhân",
    "birth": "Giấy khai sinh",
    "custody": "Điều kiện chăm sóc con",
    "identity": "Giấy tờ tùy thân",
    "ownership": "Chứng minh quyền sở hữu",
    "will": "Di chúc / thừa kế",
    "communication": "Trao đổi / thông báo",
    "clause": "Điều khoản hợp đồng",
    "other": "Tài liệu khác",
}


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get((category or "").lower(), category or "Tài liệu khác")
