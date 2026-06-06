"""
Next-best-action recommendation engine for the legal analysis MVP.

This module turns an analysis result into a ranked list of follow-up actions.
It is intentionally deterministic and dependency-free so the MVP can still
guide users when MongoDB/vector search is unavailable.
"""

from __future__ import annotations

import unicodedata
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
    detected_goals: List[str] = field(default_factory=list)
    user_position: str = "general_user"
    next_questions: List[str] = field(default_factory=list)
    journey_steps: List[str] = field(default_factory=list)


@dataclass
class GoalProfile:
    detected_goals: List[str] = field(default_factory=list)
    user_position: str = "general_user"
    next_questions: List[str] = field(default_factory=list)
    journey_steps: List[str] = field(default_factory=list)


class NextBestActionRecommender:
    """Rule-based recommender that ranks follow-up modules for an analysis."""

    def recommend(
        self,
        context: RecommendationContext,
        limit: int = 6,
        behavior_scores: Optional[Dict[str, float]] = None,
    ) -> List[NextBestAction]:
        cleaned = _normalize_context(context)
        goal_profile = _build_goal_profile(cleaned)
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
        scored = [_apply_goal_profile(item, goal_profile) for item in scored]
        if behavior_scores:
            scored = [_apply_behavior_score(item, behavior_scores) for item in scored]
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


def _apply_behavior_score(
    item: NextBestAction,
    behavior_scores: Dict[str, float],
) -> NextBestAction:
    """Adjust score using persisted demo feedback/click signals."""
    boost = behavior_scores.get(item.action_id, 0.0) + behavior_scores.get(item.module, 0.0) * 0.5
    if not boost:
        return item
    adjusted = round(max(0.0, min(item.score + boost, 0.98)), 3)
    reason = item.reason
    if boost > 0.015:
        reason = f"{reason} Người dùng từng phản hồi tích cực với gợi ý tương tự."
    elif boost < -0.015:
        reason = f"{reason} Điểm đã giảm nhẹ do phản hồi trước đó."
    return NextBestAction(
        action_id=item.action_id,
        title=item.title,
        description=item.description,
        module=item.module,
        action_url=item.action_url,
        category=item.category,
        priority=_priority(adjusted),
        score=adjusted,
        reason=reason,
        evidence=item.evidence,
        prefill=item.prefill,
        blocking_gaps=item.blocking_gaps,
        detected_goals=item.detected_goals,
        user_position=item.user_position,
        next_questions=item.next_questions,
        journey_steps=item.journey_steps,
    )


def _apply_goal_profile(item: NextBestAction, profile: GoalProfile) -> NextBestAction:
    boost = _goal_boost(item, profile.detected_goals)
    adjusted = round(max(0.0, min(item.score + boost, 0.98)), 3)
    reason = _enrich_reason(item.reason, item, profile)
    return NextBestAction(
        action_id=item.action_id,
        title=item.title,
        description=item.description,
        module=item.module,
        action_url=item.action_url,
        category=item.category,
        priority=_priority(adjusted),
        score=adjusted,
        reason=reason,
        evidence=item.evidence,
        prefill=item.prefill,
        blocking_gaps=item.blocking_gaps,
        detected_goals=profile.detected_goals,
        user_position=profile.user_position,
        next_questions=profile.next_questions,
        journey_steps=profile.journey_steps,
    )


def _goal_boost(item: NextBestAction, goals: List[str]) -> float:
    boost = 0.0
    if "child_custody" in goals:
        if item.action_id == "evidence_gap":
            boost += 0.14
        if item.action_id == "action_plan":
            boost += 0.1
        if item.action_id == "risk_review":
            boost += 0.08
        if item.action_id == "timeline":
            boost += 0.06
    if "asset_division" in goals or "asset_protection" in goals:
        if item.action_id == "evidence_gap":
            boost += 0.08
        if item.action_id == "risk_review":
            boost += 0.1
        if item.action_id == "law_search":
            boost += 0.05
    if "divorce" in goals:
        if item.action_id == "action_plan":
            boost += 0.1
        if item.action_id == "timeline":
            boost += 0.08
        if item.action_id == "journey":
            boost += 0.05
    if "debt_recovery" in goals or "complaint_or_lawsuit" in goals:
        if item.action_id == "action_plan":
            boost += 0.08
        if item.action_id == "timeline":
            boost += 0.08
        if item.action_id == "evidence_gap":
            boost += 0.08
    if "employment_termination" in goals:
        if item.action_id == "timeline":
            boost += 0.12
        if item.action_id == "risk_review":
            boost += 0.08
    if "land_dispute" in goals:
        if item.action_id == "evidence_gap":
            boost += 0.1
        if item.action_id == "timeline":
            boost += 0.08
        if item.action_id == "law_search":
            boost += 0.06
    if "contract_enforcement" in goals:
        if item.action_id == "contract_review":
            boost += 0.16
        if item.action_id == "risk_review":
            boost += 0.08
    if "risk_avoidance" in goals and item.action_id in {"risk_review", "checklist"}:
        boost += 0.1
    return min(boost, 0.22)


def _enrich_reason(reason: str, item: NextBestAction, profile: GoalProfile) -> str:
    if not profile.detected_goals:
        return reason
    goal_labels = ", ".join(_goal_label(goal) for goal in profile.detected_goals[:3])
    if item.action_id == "evidence_gap":
        return f"{reason} Phù hợp vì mục tiêu chính đang là {goal_labels}, cần chứng cứ đủ mạnh trước khi đi tiếp."
    if item.action_id == "action_plan":
        return f"{reason} Phù hợp vì người dùng đang cần chuyển mục tiêu {goal_labels} thành việc cần làm cụ thể."
    if item.action_id == "risk_review":
        return f"{reason} Phù hợp vì mục tiêu {goal_labels} có thể phát sinh rủi ro nếu thiếu dữ kiện."
    if item.action_id == "timeline":
        return f"{reason} Phù hợp vì mục tiêu {goal_labels} thường phụ thuộc vào trình tự và thời hạn."
    return f"{reason} Được cá nhân hóa theo mục tiêu: {goal_labels}."


def _build_goal_profile(ctx: RecommendationContext) -> GoalProfile:
    text = _fold_vietnamese(" ".join([ctx.situation, " ".join(ctx.recommended_actions), " ".join(ctx.warnings)]))
    goals: List[str] = []

    def add(goal: str) -> None:
        if goal not in goals:
            goals.append(goal)

    if _contains_any(text, ["ly hon", "hon nhan", "vo chong", "cham dut hon nhan"]):
        add("divorce")
    if _contains_any(text, ["nuoi con", "nhan nuoi", "cham soc con", "giao con", "quyen nuoi con", "gianh con", "cap duong", "con gai", "con trai"]):
        add("child_custody")
    if _contains_any(text, ["chia tai san", "giu tai san", "tai san chung", "tai san rieng", "so huu tai san"]):
        add("asset_division")
    if _contains_any(text, ["giu duoc tai san", "bao ve tai san", "khong mat tai san"]):
        add("asset_protection")
    if _contains_any(text, ["doi no", "no tien", "vay tien", "khong tra tien", "thu hoi no"]):
        add("debt_recovery")
    if _contains_any(text, ["sa thai", "duoi viec", "khong tra luong", "ky luat lao dong", "tro cap thoi viec"]):
        add("employment_termination")
    if _contains_any(text, ["dat dai", "so do", "lan chiem", "tranh chap dat", "mua dat", "dat coc mua nha"]):
        add("land_dispute")
    if _contains_any(text, ["hop dong", "vi pham hop dong", "phat vi pham", "dat coc", "thoa thuan"]):
        add("contract_enforcement")
    if _contains_any(text, ["khoi kien", "khieu nai", "to cao", "nop don", "toa an"]):
        add("complaint_or_lawsuit")
    if _contains_any(text, ["rui ro", "tranh rui ro", "co bi phat", "co vi pham", "bao ve"]):
        add("risk_avoidance")

    position = _detect_user_position(text, goals)
    return GoalProfile(
        detected_goals=goals or ["clarify_legal_goal"],
        user_position=position,
        next_questions=_next_questions(goals, position, folded_situation=text),
        journey_steps=_journey_steps(goals, position),
    )


def _detect_user_position(text: str, goals: List[str]) -> str:
    if "child_custody" in goals:
        return "parent_seeking_custody"
    if _contains_any(text, ["cong ty toi", "doanh nghiep toi", "nhan vien cua toi"]):
        return "employer_or_company"
    if _contains_any(text, ["bi duoi viec", "bi sa thai", "cong ty khong tra luong"]):
        return "employee"
    if _contains_any(text, ["toi mua", "ben mua"]):
        return "buyer"
    if _contains_any(text, ["toi ban", "ben ban"]):
        return "seller"
    if _contains_any(text, ["doi no", "cho vay", "nguoi no"]):
        return "creditor_or_claimant"
    if _contains_any(text, ["bi kien", "bi khieu nai", "bi to cao"]):
        return "respondent"
    if "complaint_or_lawsuit" in goals:
        return "claimant_or_complainant"
    return "general_user"


def _next_questions(goals: List[str], position: str, folded_situation: str = "") -> List[str]:
    """Generate grounded follow-up questions.

    Two principles ("hỏi/dùng thông tin hợp tình"):
      1. Never presume facts the user did not state — e.g. ask "Bạn có mấy người con"
         instead of asserting "Hai con". Presuming a quantity the user never gave erodes
         trust (reported bug: user mentioned custody but never said two children).
      2. Skip a question whose answer the user already provided in the conversation, so
         the assistant does not re-ask what it was just told.
    """
    questions: List[str] = []

    def add(question: str, answered_if: Optional[List[str]] = None) -> None:
        # Drop the question when the situation already answers it.
        if answered_if and folded_situation and _contains_any(folded_situation, answered_if):
            return
        if question not in questions:
            questions.append(question)

    if "child_custody" in goals:
        add(
            "Bạn có mấy người con, độ tuổi bao nhiêu, và hiện các con đang sống với ai "
            "(ai là người trực tiếp chăm sóc hằng ngày)?",
            answered_if=["con dang song voi", "con o voi", "con song cung", "truc tiep cham soc",
                         "con dang song", "cac con song"],
        )
        add(
            "Bạn có chứng cứ về thu nhập, nơi ở, thời gian chăm sóc và điều kiện học tập của con không?",
            answered_if=["bang luong", "hop dong lao dong", "so ho khau", "giay to thu nhap"],
        )
    if "asset_division" in goals or "asset_protection" in goals:
        add("Tài sản bạn muốn giữ là tài sản hình thành trước hay sau khi kết hôn?",
            answered_if=["truoc khi ket hon", "sau khi ket hon", "tai san rieng truoc"])
        add("Tài sản đang đứng tên ai và có giấy tờ chứng minh nguồn tiền/công sức đóng góp không?")
    if "divorce" in goals:
        add("Hai bên có đồng ý ly hôn không, hay dự kiến sẽ ly hôn đơn phương?",
            answered_if=["dong y ly hon", "thuan tinh ly hon", "ly hon don phuong", "chua ly hon"])
    if "employment_termination" in goals:
        add("Bạn nhận quyết định sa thải/nghỉ việc vào ngày nào và có văn bản hay tin nhắn làm chứng cứ không?")
    if "land_dispute" in goals:
        add("Bạn đang có sổ đỏ, giấy viết tay, hợp đồng đặt cọc hay chứng từ thanh toán nào?",
            answered_if=["co so do", "co giay viet tay", "co hop dong dat coc", "co chung tu thanh toan"])
        add("Tranh chấp đất bắt đầu từ thời điểm nào và hiện trạng sử dụng đất ra sao?")
    if "contract_enforcement" in goals:
        add("Hợp đồng/thỏa thuận có điều khoản phạt, bồi thường hoặc thời hạn thực hiện không?")
    if "debt_recovery" in goals:
        add("Khoản nợ có giấy vay, chuyển khoản, tin nhắn xác nhận hoặc người làm chứng không?")
    if "complaint_or_lawsuit" in goals:
        add("Bạn muốn thương lượng, khiếu nại hay khởi kiện ngay?")
    if not questions:
        add("Mục tiêu chính của bạn là muốn đòi quyền lợi, giảm rủi ro hay chuẩn bị hồ sơ?")
        add("Bạn đang có những giấy tờ/chứng cứ nào liên quan?")
    return questions[:4]


def _journey_steps(goals: List[str], position: str) -> List[str]:
    if "child_custody" in goals or "divorce" in goals:
        return [
            "Chốt mục tiêu: ly hôn, quyền nuôi con, cấp dưỡng và tài sản.",
            "Bổ sung chứng cứ về con, thu nhập, nơi ở và tài sản chung/riêng.",
            "Đánh giá rủi ro về quyền nuôi con và chia tài sản.",
            "Lập kế hoạch hồ sơ và mốc nộp tại tòa.",
        ]
    if "employment_termination" in goals:
        return [
            "Xác định mốc nhận quyết định và thời hạn khiếu nại/khởi kiện.",
            "Thu thập hợp đồng lao động, bảng lương, quyết định và trao đổi nội bộ.",
            "Đánh giá quyền lợi có thể yêu cầu.",
            "Soạn phương án thương lượng hoặc hồ sơ khiếu nại.",
        ]
    if "land_dispute" in goals:
        return [
            "Xác định loại giấy tờ đất và hiện trạng sử dụng.",
            "Lập timeline giao dịch, thanh toán và phát sinh tranh chấp.",
            "Đối chiếu căn cứ pháp lý và rủi ro chứng cứ.",
            "Chuẩn bị bước thương lượng, hòa giải hoặc khởi kiện.",
        ]
    if "contract_enforcement" in goals:
        return [
            "Rà soát điều khoản nghĩa vụ, vi phạm, phạt và bồi thường.",
            "Thu thập chứng cứ thực hiện/vi phạm hợp đồng.",
            "Đánh giá rủi ro và khả năng yêu cầu bồi thường.",
            "Lập kế hoạch thông báo, thương lượng hoặc khởi kiện.",
        ]
    return [
        "Làm rõ mục tiêu pháp lý chính.",
        "Bổ sung chứng cứ và mốc thời gian quan trọng.",
        "Đánh giá rủi ro trước khi hành động.",
        "Chọn module tiếp theo để lập kế hoạch hoặc tra cứu căn cứ.",
    ]


def _goal_label(goal: str) -> str:
    labels = {
        "divorce": "ly hôn",
        "child_custody": "quyền nuôi con",
        "asset_division": "chia tài sản",
        "asset_protection": "bảo vệ tài sản",
        "debt_recovery": "đòi nợ",
        "employment_termination": "xử lý chấm dứt lao động",
        "land_dispute": "tranh chấp đất đai",
        "contract_enforcement": "thực hiện hợp đồng",
        "complaint_or_lawsuit": "khiếu nại/khởi kiện",
        "risk_avoidance": "giảm rủi ro",
        "clarify_legal_goal": "làm rõ mục tiêu pháp lý",
    }
    return labels.get(goal, goal.replace("_", " "))


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle in text for needle in needles)


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
    lowered = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(char for char in lowered if unicodedata.category(char) != "Mn")
    stripped = stripped.replace("đ", "d")
    return "".join(replacements.get(char, char) for char in stripped)
