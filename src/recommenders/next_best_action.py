"""
Next-best-action recommendation engine for the legal analysis MVP.

This module turns an analysis result into a ranked list of follow-up actions.
It is intentionally deterministic and dependency-free so the MVP can still
guide users when MongoDB/vector search is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class RecommendationContext:
    situation: str
    domain: str = "general"
    position_score: float = 0.0
    domain_confidence: float = 0.0
    citations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    risk_assessment: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NextBestAction:
    action_id: str
    title: str
    description: str
    module: str
    action_url: str
    category: str
    priority: str
    score: float
    reason: str
    evidence: List[str]
    prefill: Dict[str, Any]
    blocking_gaps: List[str] = field(default_factory=list)


class NextBestActionRecommender:
    """Rule-based recommender that ranks follow-up modules for an analysis."""

    def recommend(
        self,
        context: RecommendationContext,
        limit: int = 6,
    ) -> List[NextBestAction]:
        cleaned = _normalize_context(context)
        scored = [
            self._evidence_gap(cleaned),
            self._law_search(cleaned),
            self._action_plan(cleaned),
            self._risk_review(cleaned),
            self._timeline(cleaned),
            self._similar_cases(cleaned),
            self._contract_review(cleaned),
            self._checklist(cleaned),
            self._journey(cleaned),
        ]
        ranked = [item for item in scored if item.score >= 0.34]
        ranked.sort(key=lambda item: (-item.score, item.action_id))
        return ranked[: max(1, limit)]

    def _evidence_gap(self, ctx: RecommendationContext) -> NextBestAction:
        score = 0.38
        gaps: List[str] = []
        if len(ctx.citations) < 2:
            score += 0.18
            gaps.append("Chua du can cu phap ly duoc trich dan.")
        if ctx.position_score < 0.55:
            score += 0.16
            gaps.append("Vi the phap ly con yeu hoac chua chac chan.")
        if ctx.warnings:
            score += 0.08
        return _action(
            "evidence_gap",
            "Kiem tra chung cu con thieu",
            "Xac dinh giay to, moc thoi gian va bang chung can bo sung truoc khi di tiep.",
            "evidence_gap",
            "/evidence-gap",
            "evidence",
            score,
            "Uu tien vi ket qua phan tich phu thuoc vao do day cua chung cu.",
            ctx,
            gaps,
        )

    def _law_search(self, ctx: RecommendationContext) -> NextBestAction:
        score = 0.36
        gaps: List[str] = []
        if len(ctx.citations) < 3:
            score += 0.14
            gaps.append("Can doi chieu them dieu luat hoac van ban lien quan.")
        if ctx.domain_confidence < 0.45:
            score += 0.12
            gaps.append("Linh vuc phap ly chua duoc xac dinh that chac.")
        if ctx.domain != "general":
            score += 0.04
        return _action(
            "law_search",
            "Mo rong dan chung phap ly",
            "Tra cuu them dieu luat de kiem tra va gia co lap luan.",
            "law_search",
            "/law-search",
            "authority",
            score,
            "Dan chung phap ly la co so de xep hang cac goi y tiep theo.",
            ctx,
            gaps,
        )

    def _action_plan(self, ctx: RecommendationContext) -> NextBestAction:
        score = 0.44 + min(0.2, len(ctx.recommended_actions) * 0.04)
        if ctx.warnings:
            score += 0.08
        if ctx.position_score < 0.5:
            score += 0.06
        return _action(
            "action_plan",
            "Lap ke hoach hanh dong",
            "Chuyen khuyen nghi thanh cac viec can lam theo muc do khan cap.",
            "actions",
            "/actions",
            "execution",
            score,
            "Phan tich da co ket luan va can duoc chuyen thanh buoc hanh dong cu the.",
            ctx,
        )

    def _risk_review(self, ctx: RecommendationContext) -> NextBestAction:
        risks = _risk_count(ctx.risk_assessment)
        score = 0.32 + min(0.18, risks * 0.06) + min(0.12, len(ctx.warnings) * 0.04)
        if _has_keywords(ctx.situation, ["thoi hieu", "qua han", "khong cong chung", "giay tay", "phat vi pham"]):
            score += 0.12
        return _action(
            "risk_review",
            "Danh gia rui ro phap ly",
            "Xep hang rui ro, diem yeu va cach giam thieu truoc khi nop ho so.",
            "risks",
            "/risks",
            "risk",
            score,
            "Can nhin ro rui ro truoc khi quyet dinh thuong luong, khieu nai hay khoi kien.",
            ctx,
        )

    def _timeline(self, ctx: RecommendationContext) -> NextBestAction:
        score = 0.3
        if ctx.domain in {"dat_dai", "lao_dong", "hop_dong", "hanh_chinh"}:
            score += 0.14
        if _has_keywords(ctx.situation, ["thoi hieu", "han", "ngay", "thang", "nam", "qua han", "khieu nai"]):
            score += 0.18
        return _action(
            "timeline",
            "Kiem tra tien trinh va thoi han",
            "Xac dinh giai doan vu viec, thoi hieu va moc viec can lam.",
            "timeline",
            "/timeline",
            "procedure",
            score,
            "Nhieu vu viec phap ly mat quyen vi bo lo thoi han hoac sai trinh tu.",
            ctx,
        )

    def _similar_cases(self, ctx: RecommendationContext) -> NextBestAction:
        score = 0.3
        if ctx.domain != "general":
            score += 0.12
        if 0.35 <= ctx.position_score <= 0.75:
            score += 0.1
        return _action(
            "similar_cases",
            "Tim vu viec tuong tu",
            "So sanh voi tinh huong co ket qua gan giong de rut ra bai hoc.",
            "similar_cases",
            "/similar-cases",
            "authority",
            score,
            "Vu viec tuong tu giup kiem tra tinh thuc te cua chien luoc.",
            ctx,
        )

    def _contract_review(self, ctx: RecommendationContext) -> NextBestAction:
        score = 0.22
        if ctx.domain == "hop_dong":
            score += 0.28
        if _has_keywords(ctx.situation, ["hop dong", "thoa thuan", "dat coc", "thue", "mua ban", "phat vi pham"]):
            score += 0.2
        return _action(
            "contract_review",
            "Ra soat hop dong va dieu khoan",
            "Kiem tra dieu khoan bat loi, dieu khoan thieu va can cu sua doi.",
            "contract",
            "/contract",
            "contract",
            score,
            "Tinh huong co dau hieu phu thuoc vao noi dung hop dong hoac thoa thuan.",
            ctx,
        )

    def _checklist(self, ctx: RecommendationContext) -> NextBestAction:
        score = 0.22
        if ctx.domain in {"doanh_nghiep", "lao_dong", "hop_dong"}:
            score += 0.18
        if ctx.warnings or _risk_count(ctx.risk_assessment) > 0:
            score += 0.12
        return _action(
            "checklist",
            "Tao checklist tuan thu",
            "Bien rui ro thanh danh sach kiem tra va theo doi tien do.",
            "checklists",
            "/checklists",
            "compliance",
            score,
            "Checklist giup khong bo sot ho so, nghia vu va viec can theo doi.",
            ctx,
        )

    def _journey(self, ctx: RecommendationContext) -> NextBestAction:
        score = 0.34
        if ctx.warnings:
            score += 0.06
        if ctx.recommended_actions:
            score += 0.06
        return _action(
            "journey",
            "Mo hanh trinh phap ly tong hop",
            "Gom giai doan, chung cu, rui ro va buoc tiep theo vao mot luong.",
            "journey",
            "/journey",
            "workflow",
            score,
            "Phu hop khi can nhin toan canh thay vi xu ly tung module rieng.",
            ctx,
        )


def build_recommendation_context(
    situation: str,
    domain: Optional[str] = None,
    position_score: float = 0.0,
    domain_confidence: float = 0.0,
    citations: Optional[Iterable[str]] = None,
    warnings: Optional[Iterable[str]] = None,
    recommended_actions: Optional[Iterable[str]] = None,
    risk_assessment: Optional[Dict[str, Any]] = None,
) -> RecommendationContext:
    return RecommendationContext(
        situation=situation or "",
        domain=domain or "general",
        position_score=_normalize_score(position_score),
        domain_confidence=_normalize_score(domain_confidence),
        citations=[c for c in (citations or []) if c],
        warnings=[w for w in (warnings or []) if w],
        recommended_actions=[a for a in (recommended_actions or []) if a],
        risk_assessment=risk_assessment or {},
    )


def _normalize_context(ctx: RecommendationContext) -> RecommendationContext:
    ctx.position_score = _normalize_score(ctx.position_score)
    ctx.domain_confidence = _normalize_score(ctx.domain_confidence)
    ctx.domain = ctx.domain or "general"
    return ctx


def _normalize_score(value: float) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score > 1:
        score = score / 100
    return max(0.0, min(score, 1.0))


def _priority(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.52:
        return "medium"
    return "low"


def _action(
    action_id: str,
    title: str,
    description: str,
    module: str,
    action_url: str,
    category: str,
    score: float,
    reason: str,
    ctx: RecommendationContext,
    blocking_gaps: Optional[List[str]] = None,
) -> NextBestAction:
    bounded = round(max(0.0, min(score, 0.98)), 3)
    return NextBestAction(
        action_id=action_id,
        title=title,
        description=description,
        module=module,
        action_url=action_url,
        category=category,
        priority=_priority(bounded),
        score=bounded,
        reason=reason,
        evidence=ctx.citations[:4],
        prefill={
            "summary": ctx.situation[:1200],
            "domain": ctx.domain,
            "citations": ctx.citations[:8],
        },
        blocking_gaps=blocking_gaps or [],
    )


def _risk_count(risk_assessment: Dict[str, Any]) -> int:
    risks = risk_assessment.get("risks")
    if isinstance(risks, list):
        return len(risks)
    count = risk_assessment.get("risk_count")
    if isinstance(count, int):
        return count
    return 0


def _has_keywords(text: str, keywords: Iterable[str]) -> bool:
    folded = _fold_vietnamese(text)
    return any(keyword in folded for keyword in keywords)


def _fold_vietnamese(text: str) -> str:
    replacements = {
        "á": "a", "à": "a", "ả": "a", "ã": "a", "ạ": "a", "ă": "a", "ắ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a", "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
        "đ": "d",
        "é": "e", "è": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e", "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
        "í": "i", "ì": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
        "ó": "o", "ò": "o", "ỏ": "o", "õ": "o", "ọ": "o", "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o", "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
        "ú": "u", "ù": "u", "ủ": "u", "ũ": "u", "ụ": "u", "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
        "ý": "y", "ỳ": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
    }
    lowered = text.lower()
    return "".join(replacements.get(char, char) for char in lowered)
