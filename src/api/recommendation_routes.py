"""
Recommendation API routes for Phase 11/12 — Legal Knowledge Recommendation Engine.

Endpoints:
    POST /recommendations/situation   — analyse a legal situation, recommend relevant laws
    POST /recommendations/cases       — find similar legal cases via $vectorSearch
    POST /recommendations/documents   — hybrid (vector + collaborative) document recommendations
    POST /recommendations/templates   — contract template recommendations by context/industry
    POST /recommendations/risks       — legal risk recommendations (situation or history)
    POST /recommendations/checklists  — compliance checklist by business/transaction type
    POST /agent/analyze               — full agentic analysis with OpenAI tool calling
    POST /agent/contract              — agentic contract analysis with clause extraction
    POST /interactions/log            — log a user interaction (for collaborative filtering)
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field, BaseModel

from src.api.deps import get_storage, require_user
from src.mongodb.mongo_storage import VectorStorage
from src.recommenders.behavior_recommender import BehaviorRecommender
from src.recommenders.checklist_recommender import ChecklistRecommender
from src.recommenders.document_recommender import DocumentRecommender
from src.recommenders.next_best_action import (
    NextBestActionRecommender,
    build_recommendation_context,
)
from src.recommenders.risk_recommender import RiskRecommender
from src.recommenders.situation_analyzer import SituationAnalyzer
from src.recommenders.template_recommender import TemplateRecommender

rec_router = APIRouter(prefix="/recommendations", tags=["recommendations"])
interact_router = APIRouter(prefix="/interactions", tags=["interactions"])
agent_router = APIRouter(prefix="/agent", tags=["agent"])


# ---------------------------------------------------------------------------
# Shared dependency
# ---------------------------------------------------------------------------


def _get_vector_storage(request: Request) -> Optional[VectorStorage]:
    if getattr(request.app.state, "mongodb_enabled", True) is False:
        return None
    vs = getattr(request.app.state, "vector_storage", None)
    if vs is not None:
        return vs
    try:
        return VectorStorage()
    except Exception:
        return None


def _get_behavior_source(request: Request):
    """Return Mongo vector storage when available, otherwise SQLite storage."""
    return getattr(request.app.state, "vector_storage", None) or get_storage(request)


def _next_best_action_behavior_scores(source: Any, user_id: str) -> Dict[str, float]:
    """
    Demo-friendly personalization from recommendation feedback signals.

    Positive signals nudge a module up; dismiss/not-useful nudges it down.
    The output is intentionally bounded so analysis quality remains primary.
    """
    try:
        history = source.get_user_interaction_history(user_id, days=60, limit=500)
    except Exception:
        return {}

    weights = {
        "recommendation_impression": 0.003,
        "recommendation_click": 0.045,
        "recommendation_useful": 0.09,
        "recommendation_not_useful": -0.11,
        "recommendation_dismiss": -0.08,
        "recommendation_feedback": 0.0,
    }
    scores: Dict[str, float] = {}
    for entry in history:
        action_type = entry.get("action_type", "")
        context = entry.get("context") or {}
        action_id = context.get("action_id") or entry.get("doc_id") or ""
        module = context.get("module") or ""
        delta = weights.get(action_type, 0.0)
        if action_type == "recommendation_feedback":
            feedback = context.get("feedback")
            if feedback == "useful":
                delta = 0.09
            elif feedback == "not_useful":
                delta = -0.11
        for key, factor in ((action_id, 1.0), (module, 0.8)):
            if key:
                scores[key] = scores.get(key, 0.0) + delta * factor

    return {key: round(max(-0.18, min(value, 0.18)), 3) for key, value in scores.items()}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SituationRequest(BaseModel):
    situation: str
    user_role: str = "nguyen_don"       # nguyen_don | bi_don | tu_van
    law_type: Optional[str] = None      # dat_dai | hop_dong | lao_dong | ...
    situation_id: Optional[str] = None


class LawRecommendationOut(BaseModel):
    chunk_id: str
    content: str
    law_reference: str
    relevance_score: float
    applicability: str


class SituationAnalysisOut(BaseModel):
    situation_id: str
    situation_summary: str
    legal_position_strength: str
    position_score: float
    position_reasoning: str
    relevant_laws: List[LawRecommendationOut]
    recommended_actions: List[str]
    warnings: List[str]
    missing_evidence: List[str]
    full_assessment: str
    citations: List[str]
    is_grounded: bool
    similar_situations_count: int


class DocumentRecRequest(BaseModel):
    query: str = ""
    law_type: Optional[str] = None
    limit: int = 8


class DocumentRecOut(BaseModel):
    doc_id: str
    law_type: str
    snippet: str
    vector_score: float
    collab_score: float
    final_score: float
    reason: str


class TemplateRecRequest(BaseModel):
    context: str
    industry: Optional[str] = None
    contract_type: Optional[str] = None
    template_type: Optional[str] = None   # "contract" | "official_form"
    limit: int = 5


class ChecklistItemOut(BaseModel):
    item_id: str
    category: str
    description: str
    required: bool
    related_law: str
    deadline_note: str


class TemplateRecOut(BaseModel):
    template_id: str
    name: str
    industry: str
    contract_type: str
    description: str
    key_clauses: List[str]
    related_laws: List[str]
    vector_score: float
    download_hint: str
    template_type: str = "contract"
    form_code: Optional[str] = None
    issuer: Optional[str] = None


class RiskRecRequest(BaseModel):
    situation: Optional[str] = None     # for vector search
    use_history: bool = False           # for aggregation pipeline on history
    limit: int = 6


class RiskRecOut(BaseModel):
    risk_id: str
    name: str
    severity: str
    description: str
    indicators: List[str]
    mitigation: List[str]
    related_law_types: List[str]
    source: str
    score: float


class ChecklistRecRequest(BaseModel):
    business_type: Optional[str] = None
    transaction_type: Optional[str] = None
    limit: int = 5


class ChecklistRecOut(BaseModel):
    checklist_id: str
    name: str
    business_type: str
    transaction_type: str
    description: str
    items: List[ChecklistItemOut]
    related_laws: List[str]
    priority: int


class InteractionLogRequest(BaseModel):
    doc_id: str = ""
    action_type: str                    # view | save | query | download
    context: Dict[str, Any] = Field(default_factory=dict)
    chunk_id: Optional[str] = None


def _fallback_documents(query: str, law_type: Optional[str], limit: int) -> List[DocumentRecOut]:
    domain = law_type or "dan_su"
    return [
        DocumentRecOut(
            doc_id="demo_doc_hngd_2014",
            law_type=domain,
            snippet="Demo fallback: Luat Hon nhan va Gia dinh - can cu ve ly hon, nuoi con, cap duong va chia tai san chung.",
            vector_score=0.62,
            collab_score=0.0,
            final_score=0.62,
            reason="MongoDB/vector search chua san sang; tra tai lieu demo phu hop de luong UX khong bi dut.",
        ),
        DocumentRecOut(
            doc_id="demo_doc_civil_2015",
            law_type="dan_su",
            snippet="Demo fallback: Bo luat Dan su - can cu ve giao dich, nghia vu, boi thuong va dat coc.",
            vector_score=0.51,
            collab_score=0.0,
            final_score=0.51,
            reason=f"Phu hop voi truy van: {query[:80] or 'phan tich phap ly tong quat'}.",
        ),
    ][:limit]


def _fallback_templates(limit: int) -> List[TemplateRecOut]:
    return [
        TemplateRecOut(
            template_id="demo_template_notice",
            name="Thong bao/yeu cau bang van ban",
            industry="general",
            contract_type="general",
            description="Mau thong bao giup xac lap moc thoi gian, yeu cau phan hoi va bao toan chung cu.",
            key_clauses=["Noi dung yeu cau", "Thoi han phan hoi", "Tai lieu kem theo"],
            related_laws=["Bo luat Dan su", "Bo luat To tung dan su"],
            vector_score=0.58,
            download_hint="Dung lam khung demo, can luat su ra soat truoc khi gui chinh thuc.",
        )
    ][:limit]


def _fallback_risks(limit: int) -> List[RiskRecOut]:
    return [
        RiskRecOut(
            risk_id="demo_risk_evidence_gap",
            name="Thieu chung cu va moc thoi gian",
            severity="trung_binh",
            description="Ho so chua du chung cu co the lam giam do tin cay cua danh gia va kha nang bao ve yeu cau.",
            indicators=["Chua co tai lieu goc", "Chua co timeline ro", "Chua co van ban trao doi"],
            mitigation=["Luu tin nhan/email", "Lap bang thoi gian su viec", "Tai len tai lieu vao ho so"],
            related_law_types=["dan_su", "lao_dong", "dat_dai"],
            source="demo_fallback",
            score=0.56,
        )
    ][:limit]


def _fallback_checklists(limit: int) -> List[ChecklistRecOut]:
    return [
        ChecklistRecOut(
            checklist_id="demo_checklist_case_file",
            name="Checklist ho so vu viec MVP",
            business_type="general",
            transaction_type="general",
            description="Bo muc toi thieu de nguoi dung tiep tuc thao tac khi database chua san sang.",
            items=[
                ChecklistItemOut(item_id="timeline", category="Chung cu", description="Lap timeline su viec theo ngay/thang.", required=True, related_law="", deadline_note="Lam ngay"),
                ChecklistItemOut(item_id="documents", category="Tai lieu", description="Tap hop hop dong, bien nhan, email, tin nhan, anh chup.", required=True, related_law="", deadline_note="Trong 3 ngay"),
                ChecklistItemOut(item_id="goal", category="Muc tieu", description="Ghi ro ket qua mong muon: thu tien, cham dut, nuoi con, giu tai san...", required=True, related_law="", deadline_note="Truoc khi nop don/gui thong bao"),
            ],
            related_laws=[],
            priority=1,
        )
    ][:limit]


def _fallback_cases(situation: str, law_type: Optional[str], limit: int) -> List[CaseRecOut]:
    return [
        CaseRecOut(
            case_id="demo_case_general",
            title="Vu viec demo co tinh huong tuong tu",
            situation_summary=situation[:240] or "Tinh huong phap ly tong quat",
            outcome="Can doi chieu chung cu, moc thoi gian va can cu phap ly truoc khi ket luan.",
            result="Tham khao",
            law_type=law_type or "general",
            key_laws=["Can cu phap ly se duoc bo sung khi database san sang"],
            lesson="Uu tien bo sung chung cu va dung module ke hoach hanh dong de tach cac buoc can lam.",
            similarity_score=0.5,
        )
    ][:limit]


class NextBestActionRequest(BaseModel):
    situation: str
    domain: Optional[str] = None
    position_score: float = 0.0
    domain_confidence: float = 0.0
    citations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=6, ge=1, le=10)


class NextBestActionOut(BaseModel):
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
    blocking_gaps: List[str]
    detected_goals: List[str] = Field(default_factory=list)
    user_position: str = "general_user"
    next_questions: List[str] = Field(default_factory=list)
    journey_steps: List[str] = Field(default_factory=list)
    # Phase 23 — personalization transparency
    behavior_score: float = 0.0
    personalization_reason: str = ""
    personalization_explanation: str = ""
    ranking_signals: Dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@rec_router.post("/situation", response_model=SituationAnalysisOut)
def analyse_situation(
    body: SituationRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> SituationAnalysisOut:
    """
    Analyse a legal situation and return grounded law recommendations.

    Example request:
        {
          "situation": "Người hàng xóm xây tường lấn 50cm đất sổ đỏ của tôi.",
          "user_role": "nguyen_don",
          "law_type": "dat_dai"
        }
    """
    vs = _get_vector_storage(request)
    analyzer = SituationAnalyzer(vs)
    result = analyzer.analyze(
        situation=body.situation,
        user_id=user_id,
        user_role=body.user_role,
        law_type=body.law_type,
        situation_id=body.situation_id,
    )
    return SituationAnalysisOut(
        situation_id=result.situation_id,
        situation_summary=result.situation_summary,
        legal_position_strength=result.legal_position_strength,
        position_score=result.position_score,
        position_reasoning=result.position_reasoning,
        relevant_laws=[
            LawRecommendationOut(
                chunk_id=r.chunk_id,
                content=r.content,
                law_reference=r.law_reference,
                relevance_score=r.relevance_score,
                applicability=r.applicability,
            )
            for r in result.relevant_laws
        ],
        recommended_actions=result.recommended_actions,
        warnings=result.warnings,
        missing_evidence=result.missing_evidence,
        full_assessment=result.full_assessment,
        citations=result.citations,
        is_grounded=result.is_grounded,
        similar_situations_count=result.similar_situations_count,
    )


@rec_router.post("/next-best-actions", response_model=List[NextBestActionOut])
def recommend_next_best_actions(
    body: NextBestActionRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> List[NextBestActionOut]:
    """
    Rank the next best modules/actions after a legal analysis.

    This endpoint is deterministic and does not require MongoDB. It uses the
    analysis context (domain, score, citations, warnings, risks) to recommend
    which module should be used next and why.
    """
    ctx = build_recommendation_context(
        situation=body.situation,
        domain=body.domain,
        position_score=body.position_score,
        domain_confidence=body.domain_confidence,
        citations=body.citations,
        warnings=body.warnings,
        recommended_actions=body.recommended_actions,
        risk_assessment=body.risk_assessment,
    )
    behavior_scores = _next_best_action_behavior_scores(_get_behavior_source(request), user_id)
    results = NextBestActionRecommender().recommend(ctx, limit=body.limit, behavior_scores=behavior_scores)

    enriched: List[NextBestActionOut] = []
    has_behavior = bool(behavior_scores)
    for item in results:
        d = asdict(item)
        b_score = behavior_scores.get(item.action_id, 0.0) + behavior_scores.get(item.module, 0.0) * 0.5
        b_score = round(max(-0.12, min(b_score, 0.18)), 4)
        p_reason = ""
        p_explanation = "Cá nhân hóa theo hồ sơ/hành vi của bạn" if has_behavior else ""
        if b_score > 0.02:
            p_reason = "Ưu tiên vì bạn đã phản hồi tích cực với gợi ý tương tự"
        elif b_score < -0.02:
            p_reason = "Điều chỉnh giảm theo phản hồi trước đó của bạn"
        enriched.append(NextBestActionOut(
            **d,
            behavior_score=b_score,
            personalization_reason=p_reason,
            personalization_explanation=p_explanation,
            ranking_signals={
                "base_score": round(item.score - b_score, 4),
                "behavior_boost": b_score,
                "final_score": round(item.score, 4),
            },
        ))
    return enriched


@rec_router.post("/documents", response_model=List[DocumentRecOut])
def recommend_documents(
    body: DocumentRecRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> List[DocumentRecOut]:
    """
    Hybrid document recommendations: vector search + collaborative filtering.
    """
    vs = _get_vector_storage(request)
    if vs is None:
        return _fallback_documents(body.query, body.law_type, body.limit)
    recommender = DocumentRecommender(vs)
    try:
        results = recommender.recommend(
            user_id=user_id,
            query=body.query,
            law_type=body.law_type,
            limit=body.limit,
        )
    except Exception:
        return _fallback_documents(body.query, body.law_type, body.limit)
    return [
        DocumentRecOut(
            doc_id=r.doc_id,
            law_type=r.law_type,
            snippet=r.snippet,
            vector_score=r.vector_score,
            collab_score=r.collab_score,
            final_score=r.final_score,
            reason=r.reason,
        )
        for r in results
    ]


@rec_router.post("/templates", response_model=List[TemplateRecOut])
def recommend_templates(
    body: TemplateRecRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> List[TemplateRecOut]:
    """
    Recommend contract templates based on context / industry.

    Example request:
        {"context": "thuê văn phòng 2 năm tại Hà Nội", "industry": "bat_dong_san"}
    """
    vs = _get_vector_storage(request)
    if vs is None:
        return _fallback_templates(body.limit)
    recommender = TemplateRecommender(vs)
    try:
        results = recommender.recommend(
            context=body.context,
            industry=body.industry,
            contract_type=body.contract_type,
            template_type=body.template_type,
            limit=body.limit,
            user_id=user_id,
        )
    except Exception:
        return _fallback_templates(body.limit)
    return [
        TemplateRecOut(
            template_id=r.template_id,
            name=r.name,
            industry=r.industry,
            contract_type=r.contract_type,
            description=r.description,
            key_clauses=r.key_clauses,
            related_laws=r.related_laws,
            vector_score=r.vector_score,
            download_hint=r.download_hint,
            template_type=r.template_type,
            form_code=r.form_code,
            issuer=r.issuer,
        )
        for r in results
    ]


@rec_router.post("/risks", response_model=List[RiskRecOut])
def recommend_risks(
    body: RiskRecRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> List[RiskRecOut]:
    """
    Recommend legal risks.

    Set use_history=true to run the Aggregation Pipeline over interaction history.
    Provide situation for $vectorSearch-based risk matching.
    Both can be combined (results are merged and deduplicated).
    """
    vs = _get_vector_storage(request)
    if vs is None:
        return _fallback_risks(body.limit)
    recommender = RiskRecommender(vs)

    results = []
    seen_ids: set[str] = set()

    if body.situation:
        vec_results = recommender.recommend_from_situation(
            situation=body.situation,
            user_id=user_id,
            limit=body.limit,
        )
        for r in vec_results:
            if r.risk_id not in seen_ids:
                results.append(r)
                seen_ids.add(r.risk_id)

    if body.use_history:
        hist_results = recommender.recommend_from_history(
            user_id=user_id,
            limit=body.limit,
        )
        for r in hist_results:
            if r.risk_id not in seen_ids:
                results.append(r)
                seen_ids.add(r.risk_id)

    # If no input given, default to history
    if not body.situation and not body.use_history:
        results = recommender.recommend_from_history(user_id=user_id, limit=body.limit)

    return [
        RiskRecOut(
            risk_id=r.risk_id,
            name=r.name,
            severity=r.severity,
            description=r.description,
            indicators=r.indicators,
            mitigation=r.mitigation,
            related_law_types=r.related_law_types,
            source=r.source,
            score=r.score,
        )
        for r in results[: body.limit]
    ]


@rec_router.post("/checklists", response_model=List[ChecklistRecOut])
def recommend_checklists(
    body: ChecklistRecRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> List[ChecklistRecOut]:
    """
    Recommend compliance checklists by business type / transaction type.

    Example request:
        {"business_type": "tnhh", "transaction_type": "thanh_lap_cong_ty"}
    """
    vs = _get_vector_storage(request)
    if vs is None:
        return _fallback_checklists(body.limit)
    recommender = ChecklistRecommender(vs)
    try:
        results = recommender.recommend(
            business_type=body.business_type,
            transaction_type=body.transaction_type,
            user_id=user_id,
            limit=body.limit,
        )
    except Exception:
        return _fallback_checklists(body.limit)
    return [
        ChecklistRecOut(
            checklist_id=r.checklist_id,
            name=r.name,
            business_type=r.business_type,
            transaction_type=r.transaction_type,
            description=r.description,
            items=[
                ChecklistItemOut(
                    item_id=it.item_id,
                    category=it.category,
                    description=it.description,
                    required=it.required,
                    related_law=it.related_law,
                    deadline_note=it.deadline_note,
                )
                for it in r.items
            ],
            related_laws=r.related_laws,
            priority=r.priority,
        )
        for r in results
    ]


# ---------------------------------------------------------------------------
# Interaction logging
# ---------------------------------------------------------------------------


@interact_router.post("/log", status_code=200)
def log_interaction(
    body: InteractionLogRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> dict:
    """
    Log a user interaction to power collaborative filtering recommendations.

    action_type: "view" | "save" | "query" | "download" | "situation_analysis"
    """
    source = _get_behavior_source(request)
    source.log_interaction(
        user_id=user_id,
        doc_id=body.doc_id,
        action_type=body.action_type,
        context=body.context,
        chunk_id=body.chunk_id,
    )
    return {"logged": True, "source": "mongodb" if hasattr(source, "interactions") else "sqlite"}


# ---------------------------------------------------------------------------
# Similar Legal Cases
# ---------------------------------------------------------------------------


class CaseRecRequest(BaseModel):
    situation: str
    law_type: Optional[str] = None
    limit: int = 5


class CaseRecOut(BaseModel):
    case_id: str
    title: str
    situation_summary: str
    outcome: str
    result: str
    law_type: str
    key_laws: List[str]
    lesson: str
    similarity_score: float


@rec_router.post("/cases", response_model=List[CaseRecOut])
def recommend_similar_cases(
    body: CaseRecRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> List[CaseRecOut]:
    """
    Find similar legal cases using MongoDB $vectorSearch on legal_cases.embedding.

    Example:
        {"situation": "Hàng xóm lấn chiếm 50cm đất sổ đỏ của tôi", "law_type": "dat_dai"}
    """
    vs = _get_vector_storage(request)
    if vs is None:
        return _fallback_cases(body.situation, body.law_type, body.limit)

    from src.pipeline.embedding_stage import embed_text

    try:
        embedding = embed_text(body.situation)
    except Exception:
        embedding = None

    raw = []
    if embedding:
        try:
            raw = vs.vector_search_cases(
                query_vector=embedding,
                law_type=body.law_type,
                limit=body.limit,
            )
        except Exception:
            raw = []
    if not raw:
        keywords = [w for w in body.situation.split() if len(w) > 3][:6]
        try:
            raw = vs.keyword_search_cases(keywords, limit=body.limit)
        except Exception:
            raw = []
    if not raw:
        return _fallback_cases(body.situation, body.law_type, body.limit)

    try:
        vs.log_interaction(
            user_id=user_id,
            doc_id="__cases__",
            action_type="case_recommendation",
            context={"situation": body.situation[:200], "law_type": body.law_type},
        )
    except Exception:
        pass

    return [
        CaseRecOut(
            case_id=c.get("case_id", ""),
            title=c.get("title", ""),
            situation_summary=c.get("situation_summary", ""),
            outcome=c.get("outcome", ""),
            result=c.get("result", ""),
            law_type=c.get("law_type", ""),
            key_laws=c.get("key_laws", []),
            lesson=c.get("lesson", ""),
            similarity_score=round(float(c.get("vector_score", 0.5)), 3),
        )
        for c in raw[: body.limit]
    ]


# ---------------------------------------------------------------------------
# Agent endpoints (LLM tool-calling + deterministic fallback)
# ---------------------------------------------------------------------------


class AgentSituationRequest(BaseModel):
    situation: str
    user_role: str = "nguyen_don"
    law_type: Optional[str] = None
    session_id: Optional[str] = None


class AgentLawOut(BaseModel):
    chunk_id: str
    law_reference: str
    content: str
    relevance_score: float
    applicability: Optional[str] = None


class AgentCaseOut(BaseModel):
    case_id: str
    title: str
    situation: str
    outcome: str
    result: str
    law_type: str
    similarity_score: float
    lesson: str


class AgentAnalysisOut(BaseModel):
    session_id: str
    situation_summary: str
    legal_position_strength: str
    position_score: float
    position_reasoning: str
    relevant_laws: List[AgentLawOut]
    similar_cases: List[AgentCaseOut]
    recommended_actions: List[str]
    warnings: List[str]
    risk_assessment: Dict[str, Any]
    full_assessment: str
    citations: List[str]
    is_grounded: bool
    used_llm: bool
    tool_calls_made: List[str]


class AgentContractRequest(BaseModel):
    contract_text: str
    contract_type: Optional[str] = None
    session_id: Optional[str] = None


@agent_router.post("/analyze", response_model=AgentAnalysisOut)
def agent_analyze_situation(
    body: AgentSituationRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> AgentAnalysisOut:
    """
    Full agentic legal situation analysis.

    Uses OpenAI tool calling (if OPENAI_API_KEY is set) to:
      1. Retrieve relevant laws via $vectorSearch
      2. Find similar legal cases
      3. Expand graph context
      4. Synthesize a structured assessment

    Falls back to deterministic SituationAnalyzer when LLM is unavailable.

    Example:
        {
          "situation": "Tôi mua đất bằng giấy viết tay năm 2018, bây giờ người bán đòi lại",
          "user_role": "nguyen_don",
          "law_type": "dat_dai"
        }
    """
    vs = _get_vector_storage(request)

    from src.agents.legal_agent import LegalAgent

    agent = LegalAgent(vs)
    result = agent.analyze_situation(
        situation=body.situation,
        user_id=user_id,
        user_role=body.user_role,
        law_type=body.law_type,
        session_id=body.session_id,
    )

    return AgentAnalysisOut(
        session_id=result.session_id,
        situation_summary=result.situation_summary,
        legal_position_strength=result.legal_position_strength,
        position_score=result.position_score,
        position_reasoning=result.position_reasoning,
        relevant_laws=[
            AgentLawOut(
                chunk_id=law.get("chunk_id", ""),
                law_reference=law.get("law_reference", ""),
                content=law.get("content", ""),
                relevance_score=float(law.get("relevance_score", 0.5)),
                applicability=law.get("applicability"),
            )
            for law in result.relevant_laws
        ],
        similar_cases=[
            AgentCaseOut(
                case_id=c.get("case_id", ""),
                title=c.get("title", ""),
                situation=c.get("situation", c.get("situation_summary", "")),
                outcome=c.get("outcome", ""),
                result=c.get("result", ""),
                law_type=c.get("law_type", ""),
                similarity_score=float(c.get("similarity_score", 0.5)),
                lesson=c.get("lesson", ""),
            )
            for c in result.similar_cases
        ],
        recommended_actions=result.recommended_actions,
        warnings=result.warnings,
        risk_assessment=result.risk_assessment,
        full_assessment=result.full_assessment,
        citations=result.citations,
        is_grounded=result.is_grounded,
        used_llm=result.used_llm,
        tool_calls_made=result.tool_calls_made,
    )


# ---------------------------------------------------------------------------
# Behavior-based recommendation routes
# ---------------------------------------------------------------------------


class NextActionRequest(BaseModel):
    last_action_type: str
    current_law_type: Optional[str] = None
    limit: int = 3


class BehaviorRecOut(BaseModel):
    rec_id: str
    rec_type: str
    title: str
    description: str
    law_type: Optional[str]
    score: float
    reason: str
    action_hint: str


behavior_router = APIRouter(prefix="/recommendations/behavior", tags=["behavior"])


@behavior_router.get("/profile")
def get_behavior_profile(
    request: Request,
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """
    Return the user's behavior profile built from interaction history.

    Includes recency-weighted law_type scores, action frequencies,
    active hours, and adjacent unexplored legal domains.
    """
    source = _get_behavior_source(request)
    br = BehaviorRecommender(source)
    profile = br.build_user_profile(user_id)
    return {
        "user_id": profile.user_id,
        "law_type_weights": profile.law_type_weights,
        "action_frequencies": profile.action_frequencies,
        "active_hours": profile.active_hours,
        "total_interactions": profile.total_interactions,
        "days_active": profile.days_active,
        "top_law_type": profile.top_law_type,
        "last_active": profile.last_active_iso,
        "adjacent_domains": profile.adjacent_domains,
    }


@behavior_router.get("/proactive", response_model=List[BehaviorRecOut])
def get_proactive_recommendations(
    request: Request,
    limit: int = 6,
    user_id: str = Depends(require_user),
) -> List[BehaviorRecOut]:
    """
    Proactive recommendations based on the user's interaction history:
      - re_engage   : domains with high historical weight but idle recently
      - cross_domain: adjacent legal domains not yet explored
      - proactive   : globally trending domains the user hasn't visited

    Example: GET /recommendations/behavior/proactive?limit=5
    """
    source = _get_behavior_source(request)
    br = BehaviorRecommender(source)
    results = br.recommend_proactive(user_id, limit=limit)
    return [
        BehaviorRecOut(
            rec_id=r.rec_id,
            rec_type=r.rec_type,
            title=r.title,
            description=r.description,
            law_type=r.law_type,
            score=r.score,
            reason=r.reason,
            action_hint=r.action_hint,
        )
        for r in results
    ]


@behavior_router.post("/next-action", response_model=List[BehaviorRecOut])
def get_next_action_recommendations(
    body: NextActionRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> List[BehaviorRecOut]:
    """
    Sequential next-action suggestions based on the user's last action.

    Combines predefined action-transition rules with historical bigram
    co-occurrence mined from the user's own interaction sequence.

    Example:
        {"last_action_type": "situation_analysis", "current_law_type": "dat_dai"}
    """
    source = _get_behavior_source(request)
    br = BehaviorRecommender(source)
    results = br.recommend_next_action(
        user_id=user_id,
        last_action_type=body.last_action_type,
        current_law_type=body.current_law_type,
        limit=body.limit,
    )
    return [
        BehaviorRecOut(
            rec_id=r.rec_id,
            rec_type=r.rec_type,
            title=r.title,
            description=r.description,
            law_type=r.law_type,
            score=r.score,
            reason=r.reason,
            action_hint=r.action_hint,
        )
        for r in results
    ]


@behavior_router.get("/peers", response_model=List[BehaviorRecOut])
def get_peer_trending_recommendations(
    request: Request,
    limit: int = 5,
    user_id: str = Depends(require_user),
) -> List[BehaviorRecOut]:
    """
    Peer-trending recommendations: documents and topics that users with a
    similar legal interest profile are actively engaging with.

    Example: GET /recommendations/behavior/peers?limit=5
    """
    source = _get_behavior_source(request)
    br = BehaviorRecommender(source)
    results = br.recommend_from_peers(user_id, limit=limit)
    return [
        BehaviorRecOut(
            rec_id=r.rec_id,
            rec_type=r.rec_type,
            title=r.title,
            description=r.description,
            law_type=r.law_type,
            score=r.score,
            reason=r.reason,
            action_hint=r.action_hint,
        )
        for r in results
    ]


@behavior_router.get("/digest")
def get_daily_digest(
    request: Request,
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """
    Personalised daily digest combining:
      - Profile snapshot (top domains, activity stats)
      - Activity summary for the last 7 days
      - Up to 8 ranked recommendations (proactive + sequential + peer-trending)

    Intended for the dashboard home page widget.
    """
    source = _get_behavior_source(request)
    br = BehaviorRecommender(source)
    return br.get_daily_digest(user_id)


@behavior_router.get("/memory")
def get_user_memory(
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """
    Returns the user's cross-session persistent memory:
      - personal_info: name, age, occupation, location, notes
      - situation_summaries: last 20 compressed session summaries
    """
    from src.memory.user_memory_store import UserMemoryStore
    store = UserMemoryStore()
    return store.get(user_id).to_dict()


class _MemoryInfoBody(BaseModel):
    name: Optional[str] = Field(None, max_length=80)
    age: Optional[int] = Field(None, ge=10, le=100)
    occupation: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


@behavior_router.put("/memory")
def update_user_memory(
    body: _MemoryInfoBody,
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """
    Update or clear personal info fields.
    Pass null/None to clear a specific field.
    """
    from src.memory.user_memory_store import UserMemoryStore
    store = UserMemoryStore()
    updates = body.model_dump()  # includes None values so we can clear fields
    store.update_personal_info(user_id, updates)
    return store.get(user_id).to_dict()


@agent_router.post("/contract", response_model=AgentAnalysisOut)
def agent_analyze_contract(
    body: AgentContractRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> AgentAnalysisOut:
    """
    Agentic contract analysis: clause extraction, risk detection, compliance score.

    Uses OpenAI tool calling to retrieve similar risk patterns and relevant laws,
    then synthesizes a full contract assessment.

    Falls back to pattern-based clause extraction when LLM is unavailable.

    Example:
        {
          "contract_text": "ĐIỀU 1: Tiền thuê...\nĐIỀU 5: Phạt vi phạm 20%...",
          "contract_type": "thue_nha"
        }
    """
    vs = _get_vector_storage(request)

    from src.agents.legal_agent import LegalAgent

    agent = LegalAgent(vs)
    result = agent.analyze_contract(
        contract_text=body.contract_text,
        user_id=user_id,
        contract_type=body.contract_type,
        session_id=body.session_id,
    )

    return AgentAnalysisOut(
        session_id=result.session_id,
        situation_summary=result.situation_summary,
        legal_position_strength=result.legal_position_strength,
        position_score=result.position_score,
        position_reasoning=result.position_reasoning,
        relevant_laws=[
            AgentLawOut(
                chunk_id=law.get("chunk_id", ""),
                law_reference=law.get("law_reference", ""),
                content=law.get("content", ""),
                relevance_score=float(law.get("relevance_score", 0.5)),
                applicability=law.get("applicability"),
            )
            for law in result.relevant_laws
        ],
        similar_cases=[],
        recommended_actions=result.recommended_actions,
        warnings=result.warnings,
        risk_assessment=result.risk_assessment,
        full_assessment=result.full_assessment,
        citations=result.citations,
        is_grounded=result.is_grounded,
        used_llm=result.used_llm,
        tool_calls_made=result.tool_calls_made,
    )


# ---------------------------------------------------------------------------
# Intelligence router — full orchestrated pipeline (Stage 1-7)
# ---------------------------------------------------------------------------

intelligence_router = APIRouter(prefix="/intelligence", tags=["intelligence"])


class IntelligenceRequest(BaseModel):
    situation: str
    user_role: str = "nguyen_don"
    law_type: Optional[str] = None
    session_id: Optional[str] = None
    top_k: int = 8


class IntelligenceOut(BaseModel):
    session_id: str
    trace_id: str
    detected_domain: str
    domain_confidence: float
    situation_summary: str
    legal_position_strength: str
    position_reasoning: str = ""
    position_score: float
    relevant_laws: List[Dict[str, Any]]
    recommended_actions: List[str]
    warnings: List[str]
    risk_assessment: Dict[str, Any]
    full_assessment: str
    citations: List[str]
    is_grounded: bool
    used_llm: bool
    stage_timings: Dict[str, float]
    next_best_actions: List[NextBestActionOut] = Field(default_factory=list)
    is_chitchat: bool = False
    tool_calls_made: List[str] = Field(default_factory=list)


@intelligence_router.post("/analyze", response_model=IntelligenceOut)
def intelligence_analyze(
    body: IntelligenceRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> IntelligenceOut:
    """
    Full 7-stage Legal Intelligence Pipeline:
    QueryPlanner → SessionMemory → RetrievalFusion →
    GraphRAG → LLM Reasoning → RecommendationRanker → Persist.
    """
    vs = _get_vector_storage(request)
    try:
        from src.engine.orchestrator import LegalIntelligenceOrchestrator
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Orchestrator unavailable: {exc}")

    orch = LegalIntelligenceOrchestrator(vs)
    try:
        result = orch.analyze(
            situation=body.situation,
            user_id=user_id,
            user_role=body.user_role,
            law_type=body.law_type,
            session_id=body.session_id,
            top_k=body.top_k,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    next_best_actions: List[NextBestActionOut] = []
    if not getattr(result, "is_chitchat", False):
        ctx = build_recommendation_context(
            situation=body.situation,
            domain=result.detected_domain,
            position_score=result.position_score,
            domain_confidence=result.domain_confidence,
            citations=result.citations,
            warnings=result.warnings,
            recommended_actions=result.recommended_actions,
            risk_assessment=result.risk_assessment if isinstance(result.risk_assessment, dict) else {},
        )
        next_best_actions = [
            NextBestActionOut(**asdict(item))
            for item in NextBestActionRecommender().recommend(
                ctx,
                limit=6,
                behavior_scores=_next_best_action_behavior_scores(_get_behavior_source(request), user_id),
            )
        ]

    # Update persistent user profile for cross-session personalization
    try:
        vs.update_user_profile(
            user_id=user_id,
            domain=result.detected_domain,
            user_role=body.user_role or "",
            query_snippet=body.situation[:100],
        )
    except Exception:
        pass  # profile update is non-fatal

    return IntelligenceOut(
        session_id=result.session_id,
        trace_id=result.trace_id,
        detected_domain=result.detected_domain,
        domain_confidence=result.domain_confidence,
        situation_summary=result.situation_summary,
        legal_position_strength=result.legal_position_strength,
        position_reasoning=getattr(result, "position_reasoning", ""),
        position_score=result.position_score,
        relevant_laws=result.relevant_laws,
        recommended_actions=result.recommended_actions,
        warnings=result.warnings,
        risk_assessment=result.risk_assessment if isinstance(result.risk_assessment, dict) else {},
        full_assessment=result.full_assessment,
        citations=result.citations,
        is_grounded=result.is_grounded,
        used_llm=result.used_llm,
        stage_timings=result.stage_timings,
        next_best_actions=next_best_actions,
        is_chitchat=getattr(result, "is_chitchat", False),
        tool_calls_made=getattr(result, "tool_calls_made", []),
    )


@intelligence_router.get("/trace/{trace_id}")
def get_reasoning_trace(
    trace_id: str,
    _user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """Return the full reasoning trace for a past analysis."""
    from src.memory.session_store import SessionStore
    store = SessionStore()
    trace = store.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@intelligence_router.get("/session/{session_id}")
def get_session_history(
    session_id: str,
    _user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """Return conversation history and context for a session."""
    from src.memory.session_store import SessionStore
    store = SessionStore()
    history = store.get_session_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return history


# ---------------------------------------------------------------------------
# Standalone Recommendation Ranker — POST /recommendations/rank
# ---------------------------------------------------------------------------


class RankCandidateIn(BaseModel):
    item_id: str
    item_type: str = "law_chunk"
    content: str = ""
    law_type: str = "general"
    law_reference: str = ""
    vector_score: float = Field(default=0.5, ge=0.0, le=1.0)
    behavior_score: float = Field(default=0.0, ge=0.0, le=1.0)
    graph_score: float = Field(default=0.0, ge=0.0, le=1.0)
    updated_at: Optional[str] = None


class RankRequest(BaseModel):
    candidates: List[RankCandidateIn] = Field(..., min_length=1, max_length=50)
    top_k: int = Field(default=10, ge=1, le=50)


class RankedItemOut(BaseModel):
    item_id: str
    item_type: str
    content: str
    law_type: str
    law_reference: str
    final_score: float
    rank: int
    sources: List[str]
    explanation: str
    score_components: Dict[str, float]


class RankResponse(BaseModel):
    request_id: str
    feature: str = "recommendation_ranker"
    ranked: List[RankedItemOut]
    total: int
    weights_used: Dict[str, float]
    ranking_duration_ms: float


@rec_router.post("/rank", response_model=RankResponse)
def rank_candidates(
    body: RankRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> RankResponse:
    """
    Standalone multi-signal reranking of candidate items (Stage 6).

    Accepts a flat list of candidates with pre-computed signal scores
    (vector, behavior, graph), computes freshness/popularity/acceptance
    from MongoDB interaction history, and returns the top-k ranked list
    with per-signal score breakdowns and Vietnamese explanations.

    Example:
        {
          "candidates": [
            {"item_id": "chunk_abc", "item_type": "law_chunk",
             "content": "Điều 5...", "law_type": "dat_dai",
             "law_reference": "Điều 5 Luật Đất đai 2024",
             "vector_score": 0.85, "updated_at": "2024-07-01T00:00:00Z"}
          ],
          "top_k": 5
        }
    """
    import uuid as _uuid
    from src.engine.retrieval_fusion import FusedResult, FusedResultSet
    from src.engine.recommendation_ranker import RecommendationRanker

    vs = _get_vector_storage(request)

    fused_results = [
        FusedResult(
            item_id=c.item_id,
            item_type=c.item_type,
            content=c.content[:500],
            law_type=c.law_type,
            law_reference=c.law_reference,
            raw_data={"updated_at": c.updated_at} if c.updated_at else {},
            vector_score=c.vector_score,
            bm25_score=0.0,
            graph_score=c.graph_score,
            behavior_score=c.behavior_score,
            fusion_score=c.vector_score,
            sources=["api_input"],
        )
        for c in body.candidates
    ]

    fused_set = FusedResultSet(
        plan_id="rank_" + str(_uuid.uuid4())[:8],
        results=fused_results,
        total_raw_hits=len(fused_results),
        vector_hits=len(fused_results),
        bm25_hits=0,
        graph_hits=0,
        behavior_hits=0,
        fusion_weights={"vector": 1.0, "bm25": 0.0, "graph": 0.0, "behavior": 0.0},
        fusion_duration_ms=0.0,
    )

    ranker = RecommendationRanker(vs)
    result = ranker.rank(fused_set, user_id=user_id, top_k=body.top_k)

    return RankResponse(
        request_id="rank_" + str(_uuid.uuid4())[:8],
        ranked=[
            RankedItemOut(
                item_id=item.item_id,
                item_type=item.item_type,
                content=item.content,
                law_type=item.law_type,
                law_reference=item.law_reference,
                final_score=item.final_score,
                rank=item.rank,
                sources=item.sources,
                explanation=item.explanation,
                score_components=item.score_components,
            )
            for item in result.ranked
        ],
        total=len(result.ranked),
        weights_used=result.weights_used,
        ranking_duration_ms=result.ranking_duration_ms,
    )


# ---------------------------------------------------------------------------
# Personalized Feed  (GET /feed/personalized)
# ---------------------------------------------------------------------------

feed_router = APIRouter(prefix="/feed", tags=["feed"])


class FeedItem(BaseModel):
    type: str          # law | template | checklist | case | topic
    title: str
    reason: str
    score: float
    action_url: str


class FeedResponse(BaseModel):
    user_id: str
    feed_items: List[FeedItem]
    source: str        # "behavior" | "default"


_DEFAULT_FEED: List[Dict[str, Any]] = [
    {"type": "topic", "title": "Luật Đất đai 2024 — điểm mới quan trọng", "reason": "Phổ biến nhất tháng này", "score": 0.9, "action_url": "/analyze?topic=dat_dai"},
    {"type": "template", "title": "Hợp đồng mua bán nhà đất", "reason": "Mẫu được tải nhiều nhất", "score": 0.85, "action_url": "/templates"},
    {"type": "checklist", "title": "Kiểm tra trước khi ký hợp đồng", "reason": "Gợi ý cho người dùng mới", "score": 0.8, "action_url": "/checklists"},
    {"type": "topic", "title": "Quyền lợi người lao động khi bị sa thải", "reason": "Chủ đề quan tâm nhiều", "score": 0.75, "action_url": "/analyze?topic=lao_dong"},
    {"type": "template", "title": "Đơn khiếu nại hành chính", "reason": "Tài liệu thiết yếu", "score": 0.7, "action_url": "/templates"},
]


@feed_router.get("/personalized", response_model=FeedResponse)
def get_personalized_feed(
    request: Request,
    user_id: str = Depends(require_user),
) -> FeedResponse:
    """
    Trả về feed cá nhân hoá dựa trên lịch sử tương tác của người dùng.
    Fallback về feed mặc định nếu chưa có đủ dữ liệu hành vi.
    """
    try:
        source = _get_behavior_source(request)
        br = BehaviorRecommender(source)
        proactive = br.recommend_proactive(user_id, limit=10)

        if not proactive:
            return FeedResponse(
                user_id=user_id,
                feed_items=[FeedItem(**item) for item in _DEFAULT_FEED],
                source="default",
            )

        feed_items = []
        for rec in proactive[:8]:
            rec_id = getattr(rec, "rec_id", "")
            rec_type = "topic"
            if "checklist" in rec_id:
                rec_type = "checklist"
            elif "template" in rec_id:
                rec_type = "template"
            action_url = "/analyze"
            if rec_type == "template":
                action_url = "/templates"
            elif rec_type == "checklist":
                action_url = "/checklists"

            feed_items.append(FeedItem(
                type=rec_type,
                title=getattr(rec, "title", getattr(rec, "name", "Gợi ý pháp lý")),
                reason=getattr(rec, "reason", "Phù hợp với lịch sử của bạn"),
                score=round(getattr(rec, "score", 0.7), 3),
                action_url=action_url,
            ))

        return FeedResponse(user_id=user_id, feed_items=feed_items, source="behavior")

    except Exception:
        return FeedResponse(
            user_id=user_id,
            feed_items=[FeedItem(**item) for item in _DEFAULT_FEED],
            source="default",
        )


# ---------------------------------------------------------------------------
# Role-based Recommendations  (POST /recommendations/by-role)
# ---------------------------------------------------------------------------


class RoleRequest(BaseModel):
    role: str  # hr | startup | sme | individual | legal_staff


class QuickLinkOut(BaseModel):
    label: str
    url: str


class RoleRecommendResponse(BaseModel):
    role: str
    persona_label: str
    pack_explanation: str
    recommended_topics: List[str]
    recommended_templates: List[str]
    recommended_checklists: List[str]
    quick_links: List[QuickLinkOut]


# ---------------------------------------------------------------------------
# Checklist Progress  (GET/POST /recommendations/checklists/{id}/progress)
# ---------------------------------------------------------------------------


class ChecklistProgressRequest(BaseModel):
    checked_items: List[str]


class ChecklistProgressResponse(BaseModel):
    checklist_id: str
    checked_items: List[str]


@rec_router.get("/checklists/{checklist_id}/progress", response_model=ChecklistProgressResponse)
def get_checklist_progress(
    checklist_id: str,
    request: Request,
    user_id: str = Depends(require_user),
) -> ChecklistProgressResponse:
    """Return the saved checked items for a user's checklist."""
    vs = getattr(request.app.state, "vector_storage", None)
    if vs is not None:
        checked = vs.get_checklist_progress(user_id, checklist_id)
    else:
        checked = get_storage(request).get_checklist_progress(user_id, checklist_id)
    return ChecklistProgressResponse(checklist_id=checklist_id, checked_items=checked)


@rec_router.post("/checklists/{checklist_id}/progress", response_model=ChecklistProgressResponse)
def save_checklist_progress(
    checklist_id: str,
    body: ChecklistProgressRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> ChecklistProgressResponse:
    """Persist the checked items for a user's checklist."""
    vs = getattr(request.app.state, "vector_storage", None)
    if vs is not None:
        vs.save_checklist_progress(user_id, checklist_id, body.checked_items)
    else:
        get_storage(request).save_checklist_progress(user_id, checklist_id, body.checked_items)
    return ChecklistProgressResponse(checklist_id=checklist_id, checked_items=body.checked_items)


@rec_router.post("/by-role", response_model=RoleRecommendResponse)
def recommend_by_role(
    body: RoleRequest,
    user_id: str = Depends(require_user),
) -> RoleRecommendResponse:
    """
    Trả về gói đề xuất cá nhân hoá theo vai trò người dùng:
    hr | startup | sme | individual | legal_staff.
    """
    from src.recommenders.persona_recommender import PersonaRecommender
    recommender = PersonaRecommender()
    result = recommender.recommend_by_role(role=body.role, user_id=user_id)
    return RoleRecommendResponse(
        role=result.role,
        persona_label=result.persona_label,
        pack_explanation=result.pack_explanation,
        recommended_topics=result.recommended_topics,
        recommended_templates=result.recommended_templates,
        recommended_checklists=result.recommended_checklists,
        quick_links=[QuickLinkOut(**lnk) for lnk in result.quick_links],
    )
