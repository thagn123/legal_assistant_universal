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

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.api.deps import require_user
from src.mongodb.mongo_storage import VectorStorage
from src.recommenders.behavior_recommender import BehaviorRecommender
from src.recommenders.checklist_recommender import ChecklistRecommender
from src.recommenders.document_recommender import DocumentRecommender
from src.recommenders.risk_recommender import RiskRecommender
from src.recommenders.situation_analyzer import SituationAnalyzer
from src.recommenders.template_recommender import TemplateRecommender

rec_router = APIRouter(prefix="/recommendations", tags=["recommendations"])
interact_router = APIRouter(prefix="/interactions", tags=["interactions"])
agent_router = APIRouter(prefix="/agent", tags=["agent"])


# ---------------------------------------------------------------------------
# Shared dependency
# ---------------------------------------------------------------------------


def _get_vector_storage(request: Request) -> VectorStorage:
    vs = getattr(request.app.state, "vector_storage", None)
    if vs is None:
        raise HTTPException(
            status_code=503,
            detail="MongoDB vector storage is not available. Start MongoDB and restart the server.",
        )
    return vs


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
    doc_id: str
    action_type: str                    # view | save | query | download
    context: Dict[str, Any] = {}
    chunk_id: Optional[str] = None


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
    recommender = DocumentRecommender(vs)
    results = recommender.recommend(
        user_id=user_id,
        query=body.query,
        law_type=body.law_type,
        limit=body.limit,
    )
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
    recommender = TemplateRecommender(vs)
    results = recommender.recommend(
        context=body.context,
        industry=body.industry,
        contract_type=body.contract_type,
        limit=body.limit,
        user_id=user_id,
    )
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
    recommender = ChecklistRecommender(vs)
    results = recommender.recommend(
        business_type=body.business_type,
        transaction_type=body.transaction_type,
        user_id=user_id,
        limit=body.limit,
    )
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


@interact_router.post("/log", status_code=204)
def log_interaction(
    body: InteractionLogRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> None:
    """
    Log a user interaction to power collaborative filtering recommendations.

    action_type: "view" | "save" | "query" | "download" | "situation_analysis"
    """
    vs = _get_vector_storage(request)
    vs.log_interaction(
        user_id=user_id,
        doc_id=body.doc_id,
        action_type=body.action_type,
        context=body.context,
        chunk_id=body.chunk_id,
    )


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

    from src.pipeline.embedding_stage import embed_text

    embedding = embed_text(body.situation)

    if embedding:
        raw = vs.vector_search_cases(
            query_vector=embedding,
            law_type=body.law_type,
            limit=body.limit,
        )
    else:
        keywords = [w for w in body.situation.split() if len(w) > 3][:6]
        raw = vs.keyword_search_cases(keywords, limit=body.limit)

    vs.log_interaction(
        user_id=user_id,
        doc_id="__cases__",
        action_type="case_recommendation",
        context={"situation": body.situation[:200], "law_type": body.law_type},
    )

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
    vs = _get_vector_storage(request)
    br = BehaviorRecommender(vs)
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
    vs = _get_vector_storage(request)
    br = BehaviorRecommender(vs)
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
    vs = _get_vector_storage(request)
    br = BehaviorRecommender(vs)
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
    vs = _get_vector_storage(request)
    br = BehaviorRecommender(vs)
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
    vs = _get_vector_storage(request)
    br = BehaviorRecommender(vs)
    return br.get_daily_digest(user_id)


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
    position_score: float
    relevant_laws: List[Dict[str, Any]]
    recommended_actions: List[str]
    warnings: List[str]
    risk_assessment: str
    full_assessment: str
    citations: List[str]
    is_grounded: bool
    used_llm: bool
    stage_timings: Dict[str, float]


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

    return IntelligenceOut(
        session_id=result.session_id,
        trace_id=result.trace_id,
        detected_domain=result.detected_domain,
        domain_confidence=result.domain_confidence,
        situation_summary=result.situation_summary,
        legal_position_strength=result.legal_position_strength,
        position_score=result.position_score,
        relevant_laws=result.relevant_laws,
        recommended_actions=result.recommended_actions,
        warnings=result.warnings,
        risk_assessment=result.risk_assessment,
        full_assessment=result.full_assessment,
        citations=result.citations,
        is_grounded=result.is_grounded,
        used_llm=result.used_llm,
        stage_timings=result.stage_timings,
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
