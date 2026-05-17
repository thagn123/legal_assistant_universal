"""
LegalIntelligenceOrchestrator — Core reasoning pipeline coordinator.

Replaces the monolithic LegalAgent with an explicit 7-stage pipeline:

  Stage 1 │ QueryPlanner          — detect domain, extract entities, select strategy
  Stage 2 │ SessionLoader         — load/create conversation context from MongoDB
  Stage 3 │ RetrievalFusionEngine — hybrid retrieval (vector + BM25 + graph + behavior)
  Stage 4 │ GraphExpander         — graph context via dispatch_tool()
  Stage 5 │ ReasoningEngine       — LLM tool-calling OR deterministic fallback
  Stage 6 │ RecommendationRanker  — multi-signal reranking of retrieved laws
  Stage 7 │ Persist               — save trace + session context to MongoDB

Each stage is independently testable and observable via ExecutionTracer.
The orchestrator returns IntelligenceResult — a superset of LegalAgentResult.

Backward compatibility:
  LegalAgent.analyze_situation() delegates here (lazy import in legal_agent.py).
  On any orchestrator failure it transparently falls back to the original loop.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.engine.query_planner import QueryPlanner, QueryPlan
from src.engine.retrieval_fusion import RetrievalFusionEngine, FusedResultSet
from src.engine.recommendation_ranker import RecommendationRanker, RankedItem
from src.engine.reasoning_trace import TraceBuilder, ReasoningTrace
from src.memory.session_store import SessionStore, SessionContext
from src.mongodb.mongo_storage import VectorStorage
from src.observability.tracer import get_tracer
from src.pipeline.embedding_stage import embed_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass (superset of LegalAgentResult)
# ---------------------------------------------------------------------------


@dataclass
class IntelligenceResult:
    """
    Unified result from the Legal Intelligence Orchestrator.

    Contains all fields of LegalAgentResult plus orchestrator metadata.
    Used by /intelligence/analyze endpoint directly.
    """
    # Core (mirrors LegalAgentResult exactly)
    session_id: str
    situation_summary: str
    legal_position_strength: str        # Mạnh | Trung bình | Yếu
    position_score: float
    position_reasoning: str
    relevant_laws: List[Dict[str, Any]]
    similar_cases: List[Dict[str, Any]]
    recommended_actions: List[str]
    warnings: List[str]
    risk_assessment: Dict[str, Any]
    full_assessment: str
    citations: List[str]
    is_grounded: bool
    used_llm: bool
    tool_calls_made: List[str]

    # Orchestrator metadata (new)
    trace_id: str
    detected_domain: str
    domain_confidence: float
    dispute_classification: str
    stage_count: int                     # how many stages completed
    stage_timings: Dict[str, float]      # stage_name → duration_ms
    ranking_weights: Dict[str, float]    # weights used in stage 6
    reasoning_trace: Optional[Dict[str, Any]] = None  # full trace dict for API response
    is_chitchat: bool = False            # True when query is greeting/small-talk


class OrchestratorError(Exception):
    """Raised when an unrecoverable pipeline failure occurs."""
    def __init__(self, stage_id: int, stage_name: str, cause: Exception) -> None:
        super().__init__(f"Stage {stage_id} ({stage_name}) failed: {cause}")
        self.stage_id = stage_id
        self.stage_name = stage_name
        self.cause = cause


# ---------------------------------------------------------------------------
# LegalIntelligenceOrchestrator
# ---------------------------------------------------------------------------


class LegalIntelligenceOrchestrator:
    """
    Production-grade legal intelligence pipeline coordinator.

    Usage:
        orch = LegalIntelligenceOrchestrator(vector_storage)
        result = orch.analyze(
            situation="Hàng xóm lấn 50cm đất sổ đỏ của tôi",
            user_id="u_123",
            session_id="s_abc",      # optional; creates new if omitted
        )
        print(result.reasoning_trace)  # full JSON trace for UI
    """

    def __init__(self, vector_storage: VectorStorage) -> None:
        self._vs = vector_storage
        self._planner = QueryPlanner()
        self._fusion = RetrievalFusionEngine(vector_storage)
        self._ranker = RecommendationRanker(vector_storage)
        self._session_store = SessionStore()
        self._tracer = get_tracer()

    def analyze(
        self,
        situation: str,
        user_id: str,
        user_role: str = "nguyen_don",
        law_type: Optional[str] = None,
        session_id: Optional[str] = None,
        top_k: int = 8,
        include_trace: bool = True,
    ) -> IntelligenceResult:
        """
        Execute the 7-stage pipeline for a legal situation analysis.
        Returns IntelligenceResult with optional full reasoning trace.
        """
        sid = session_id or f"orch_{uuid.uuid4().hex[:12]}"

        # Fast-path: greetings/small-talk — skip the full pipeline
        if _is_chitchat(situation):
            return _make_chitchat_result(situation, sid)
        builder = TraceBuilder(session_id=sid, user_id=user_id, query=situation)
        trace_id = builder.trace_id
        stage_timings: Dict[str, float] = {}
        tool_calls: List[str] = []
        used_llm = False

        # ── Stage 1: Query Planning ──────────────────────────────────────────
        builder.begin_stage(1, "query_planning", {
            "query_len": len(situation),
            "user_role": user_role,
            "law_type_hint": law_type,
        })
        plan = self._planner.plan(situation, law_type_hint=law_type)
        s1 = builder.end_stage({
            "detected_domain": plan.detected_domain,
            "domain_confidence": plan.domain_confidence,
            "dispute_type": plan.dispute_type,
            "strategy": plan.retrieval_strategy,
            "variants_count": len(plan.query_variants),
            "entities_found": sum(len(v) for v in plan.extracted_entities.values()),
        })
        stage_timings["query_planning"] = s1.duration_ms
        self._tracer.log_stage(trace_id, 1, "query_planning", "end", s1.output_summary, s1.duration_ms)

        # ── Stage 2: Session Loading ─────────────────────────────────────────
        builder.begin_stage(2, "session_loader", {"session_id": sid, "user_id": user_id})
        session_ctx = self._session_store.load_context(sid, user_id)
        s2 = builder.end_stage({
            "session_turns": len(session_ctx.history),
            "known_domains": session_ctx.law_type_preferences[:3],
        })
        stage_timings["session_loader"] = s2.duration_ms

        # ── Stage 3: Retrieval Fusion ────────────────────────────────────────
        builder.begin_stage(3, "retrieval_fusion", {
            "strategy": plan.retrieval_strategy,
            "query_variants": plan.query_variants,
        })
        fused: FusedResultSet = self._fusion.fuse(plan=plan, user_id=user_id, limit=16, trace_id=trace_id)
        s3 = builder.end_stage({
            "total_raw_hits": fused.total_raw_hits,
            "vector_hits": fused.vector_hits,
            "bm25_hits": fused.bm25_hits,
            "graph_hits": fused.graph_hits,
            "behavior_hits": fused.behavior_hits,
            "fused_candidates": len(fused.results),
            "top_fusion_score": fused.results[0].fusion_score if fused.results else 0,
            "weights": fused.fusion_weights,
        })
        stage_timings["retrieval_fusion"] = s3.duration_ms

        # ── Stage 4: Graph Expansion ─────────────────────────────────────────
        graph_context: List[Dict[str, Any]] = []
        builder.begin_stage(4, "graph_expansion", {
            "law_refs": plan.extracted_entities.get("laws", [])[:3],
            "requires_graph": plan.requires_graph_expansion,
        })
        if plan.requires_graph_expansion:
            try:
                from src.agents.tools import dispatch_tool
                law_refs = plan.extracted_entities.get("laws", [])[:3]
                if not law_refs and fused.results:
                    law_refs = [r.law_reference for r in fused.results[:3] if r.law_reference]
                if law_refs:
                    t_g = time.perf_counter()
                    graph_result = dispatch_tool(
                        "retrieve_graph_context",
                        {"law_references": law_refs, "depth": 2},
                        self._vs,
                    )
                    tool_calls.append("retrieve_graph_context")
                    try:
                        graph_context = json.loads(graph_result).get("results", [])
                    except Exception as _ge:
                        logger.debug("graph_context parse failed: %s", _ge)
                    d_g = (time.perf_counter() - t_g) * 1000
                    self._tracer.log_graph_traversal(
                        trace_id, len(law_refs), len(graph_context), 2, d_g
                    )
            except Exception as exc:
                logger.debug("graph expansion skipped: %s", exc)
        s4 = builder.end_stage({
            "law_refs_used": len(plan.extracted_entities.get("laws", [])),
            "graph_nodes_found": len(graph_context),
        })
        stage_timings["graph_expansion"] = s4.duration_ms

        # ── Stage 5: Reasoning (LLM tool-calling or deterministic) ───────────
        builder.begin_stage(5, "reasoning_engine", {
            "fused_candidates": len(fused.results),
            "graph_context_nodes": len(graph_context),
            "user_role": user_role,
        })

        raw_laws: List[Dict] = []
        raw_cases: List[Dict] = []
        llm_full_assessment = ""

        # Try LLM tool-calling
        try:
            from src.llm.client import get_llm_client
            from src.llm.tool_calling import SITUATION_TOOLS
            from src.agents.tools import dispatch_tool

            llm = get_llm_client()
            if llm is not None:
                # Pre-populate context from fusion so LLM sees grounded content
                context_snippets = "\n\n".join(
                    f"[{r.law_reference}]: {r.content[:200]}"
                    for r in fused.results[:5]
                    if r.content
                )
                messages = [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Tình huống: {situation[:800]}\n\n"
                            f"Vai trò: {user_role}\n\n"
                            f"Bối cảnh pháp lý đã truy xuất:\n{context_snippets}"
                        ),
                    },
                ]
                for _round in range(3):
                    response = llm.chat_complete_with_tools(messages, SITUATION_TOOLS)
                    if not response or not response.get("tool_calls"):
                        llm_full_assessment = response.get("content", "") if response else ""
                        break
                    for tc in response["tool_calls"]:
                        name = tc.get("function", {}).get("name", "")
                        args_str = tc.get("function", {}).get("arguments", "{}")
                        try:
                            args = json.loads(args_str)
                        except Exception:
                            args = {}
                        t_tc = time.perf_counter()
                        tool_result_str = dispatch_tool(name, args, self._vs)
                        d_tc = (time.perf_counter() - t_tc) * 1000
                        tool_calls.append(name)
                        self._tracer.log_tool_call(trace_id, name, args, tool_result_str[:80], d_tc)
                        messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id", ""),
                            "content": tool_result_str,
                        })
                        try:
                            tr = json.loads(tool_result_str)
                            if name == "retrieve_relevant_laws":
                                raw_laws.extend(tr.get("results", [])[:4])
                            elif name == "retrieve_similar_cases":
                                raw_cases.extend(tr.get("results", [])[:3])
                        except Exception:
                            pass
                used_llm = True
        except Exception as exc:
            logger.info("LLM unavailable in orchestrator stage 5: %s", exc)

        # Fallback: build raw_laws from fused results if LLM yielded none
        if not raw_laws:
            raw_laws = [
                {
                    "chunk_id": r.item_id,
                    "content": r.content,
                    "law_reference": r.law_reference,
                    "relevance_score": r.fusion_score,
                    "applicability": "Liên quan đến tình huống",
                }
                for r in fused.results[:8]
            ]

        # Fetch cases via vector if none retrieved by LLM
        if not raw_cases and plan.requires_case_retrieval:
            try:
                embedding = embed_text(situation)
                if embedding:
                    raw_cases = self._vs.vector_search_cases(
                        query_vector=embedding,
                        law_type=plan.detected_domain if plan.detected_domain != "general" else None,
                        limit=3,
                    )
            except Exception as exc:
                logger.debug("case retrieval fallback failed: %s", exc)

        s5 = builder.end_stage({
            "used_llm": used_llm,
            "tool_calls": tool_calls,
            "laws_collected": len(raw_laws),
            "cases_collected": len(raw_cases),
        })
        stage_timings["reasoning_engine"] = s5.duration_ms

        # ── Stage 6: Recommendation Reranking ───────────────────────────────
        builder.begin_stage(6, "recommendation_ranker", {
            "candidates_in": len(fused.results),
            "weights": self._ranker._weights,
        })
        ranking = self._ranker.rank(fused, user_id=user_id, top_k=top_k, trace_id=trace_id)
        s6 = builder.end_stage({
            "candidates_out": len(ranking.ranked),
            "top_score": ranking.ranked[0].final_score if ranking.ranked else 0,
            "top_explanation": ranking.ranked[0].explanation if ranking.ranked else "",
        })
        stage_timings["recommendation_ranker"] = s6.duration_ms

        # ── Assemble final result ────────────────────────────────────────────
        position_score, strength, reasoning = _compute_position(raw_laws, plan)
        risks = _identify_risks(situation, plan)
        warnings = _extract_warnings(raw_laws, plan)
        recommended_actions = _generate_recommendations(plan, strength, risks)
        full_assessment = llm_full_assessment or _synthesize_assessment(
            situation, plan, strength, raw_laws, raw_cases
        )
        citations = [
            l.get("law_reference", "")
            for l in raw_laws[:5]
            if l.get("law_reference")
        ]

        # Merge ranking into relevant_laws (ranked items take priority)
        relevant_laws = []
        if ranking.ranked:
            for ri in ranking.ranked[:6]:
                relevant_laws.append({
                    "chunk_id": ri.item_id,
                    "content": ri.content,
                    "law_reference": ri.law_reference,
                    "relevance_score": ri.final_score,
                    "applicability": "Liên quan đến tình huống",
                    "score_breakdown": ri.score_components,
                    "rank_explanation": ri.explanation,
                })
        else:
            for l in raw_laws[:6]:
                relevant_laws.append({
                    "chunk_id": l.get("chunk_id", ""),
                    "content": l.get("content", "")[:300],
                    "law_reference": l.get("law_reference", ""),
                    "relevance_score": round(float(l.get("relevance_score", 0.5)), 3),
                    "applicability": l.get("applicability", "Liên quan đến tình huống"),
                    "score_breakdown": {},
                    "rank_explanation": "",
                })

        similar_cases = [
            {
                "case_id": c.get("case_id", ""),
                "title": c.get("title", ""),
                "situation_summary": c.get("situation_summary", "")[:200],
                "outcome": c.get("outcome", ""),
                "result": c.get("result", ""),
                "law_type": c.get("law_type", ""),
                "similarity_score": round(float(c.get("vector_score", 0.5)), 3),
                "lesson": c.get("lesson", ""),
            }
            for c in raw_cases[:3]
        ]

        # ── Stage 7: Persist trace + session ────────────────────────────────
        builder.begin_stage(7, "persist", {"has_trace": True, "has_session": True})
        result_summary = {
            "query": situation[:200],
            "detected_domain": plan.detected_domain,
            "position_strength": strength,
            "position_score": position_score,
            "laws_found": len(relevant_laws),
            "cases_found": len(similar_cases),
            "used_llm": used_llm,
            "trace_id": trace_id,
        }
        trace = builder.build(
            final_result_summary=result_summary,
            used_fallback=not used_llm,
        )
        try:
            self._session_store.save_trace(trace)
            self._session_store.save_context(
                context=session_ctx,
                result_summary=result_summary,
                trace_id=trace_id,
                query_plan=plan.to_dict(),
            )
            self._session_store.cache_retrieval_context(
                session_id=sid,
                law_type=plan.detected_domain,
                top_chunk_ids=[r.item_id for r in fused.results[:10]],
                top_case_ids=[c["case_id"] for c in raw_cases[:5] if c.get("case_id")],
                query_plan_dict=plan.to_dict(),
            )
            self._vs.log_interaction(
                user_id=user_id,
                doc_id="__intelligence__",
                action_type="intelligence_analysis",
                context={
                    "law_type": plan.detected_domain,
                    "dispute_type": plan.dispute_type,
                    "trace_id": trace_id,
                },
            )
        except Exception as exc:
            logger.warning("stage 7 persist failed (non-fatal): %s", exc)
        s7 = builder.end_stage({"trace_saved": True, "session_saved": True})
        stage_timings["persist"] = s7.duration_ms

        return IntelligenceResult(
            session_id=sid,
            trace_id=trace_id,
            situation_summary=situation[:300],
            legal_position_strength=strength,
            position_score=position_score,
            position_reasoning=reasoning,
            relevant_laws=relevant_laws,
            similar_cases=similar_cases,
            recommended_actions=recommended_actions,
            warnings=warnings,
            risk_assessment={"risks": risks, "risk_count": len(risks)},
            full_assessment=full_assessment,
            citations=citations,
            is_grounded=bool(relevant_laws),
            used_llm=used_llm,
            tool_calls_made=tool_calls,
            detected_domain=plan.detected_domain,
            domain_confidence=plan.domain_confidence,
            dispute_classification=plan.dispute_type,
            stage_count=len(stage_timings),
            stage_timings=stage_timings,
            ranking_weights=ranking.weights_used,
            reasoning_trace=trace.to_dict() if include_trace else None,
        )


# ---------------------------------------------------------------------------
# Stage helper functions
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """Bạn là LexAI — trợ lý pháp lý AI cao cấp, được đào tạo chuyên sâu về hệ thống pháp luật Việt Nam.

## Phong cách tư vấn
Phân tích như một luật sư giàu kinh nghiệm: mạch lạc, có căn cứ pháp lý vững chắc, thực tiễn và dễ hiểu với người không chuyên.

## Cấu trúc bắt buộc — trả lời đúng 4 phần sau, dùng markdown

### I. Xác định vấn đề pháp lý
Chỉ rõ: lĩnh vực pháp lý (đất đai / hợp đồng / lao động / dân sự / hình sự...), bản chất tranh chấp, và các bên liên quan. Tối đa 3 câu.

### II. Cơ sở pháp lý áp dụng
Mỗi điều luật trình bày theo mẫu:
**[Tên văn bản] — Điều [số][, Khoản [số]]**
> "[Nội dung điều khoản — trích nguyên văn hoặc diễn giải trung thực]"
*Ý nghĩa trong tình huống này:* [giải thích ngắn gọn cách điều luật áp dụng vào vụ việc cụ thể]

Chỉ trích dẫn điều luật có trong bối cảnh pháp lý đã cung cấp. Không bịa đặt số điều hay tên văn bản.

### III. Đánh giá vị thế pháp lý
- **Vị thế hiện tại:** [Mạnh / Trung bình / Yếu] — lý do cụ thể dựa trên bằng chứng và quy định pháp luật
- **Rủi ro chính:** [liệt kê 2–3 rủi ro pháp lý cụ thể]
- **Điểm cần chú ý:** thời hiệu khởi kiện, yêu cầu về hình thức (công chứng, đăng ký...), nghĩa vụ chứng minh

### IV. Khuyến nghị hành động
Các bước cụ thể, có thứ tự ưu tiên:
1. **Ngay lập tức (trong 7 ngày):** [hành động cấp bách nhất]
2. **Trung hạn (1–3 tháng):** [chuẩn bị hồ sơ, thương lượng...]
3. **Nếu thương lượng thất bại:** [con đường pháp lý — hòa giải / khởi kiện / tố cáo...]

## Nguyên tắc bắt buộc
- Viết tiếng Việt chuẩn mực, trang trọng nhưng rõ ràng
- Chỉ dựa vào bối cảnh pháp lý được cung cấp trong tin nhắn này
- Ghi chú "(cần xác minh thêm)" nếu thiếu cơ sở pháp lý rõ ràng
- Cuối bài luôn thêm: *Lưu ý: Phân tích trên mang tính tham khảo. Để giải quyết tranh chấp chính thức, bạn nên tham vấn luật sư có thẩm quyền.*"""


# ---------------------------------------------------------------------------
# Chitchat detection
# ---------------------------------------------------------------------------

_CHITCHAT_STARTERS = (
    "chào", "hello", "hi", "xin chào", "hey", "alo",
    "cảm ơn", "cam on", "thanks", "thank you",
    "bạn là ai", "bạn là gì", "mày là ai",
    "ok", "oke", "okay", "được rồi", "tốt",
    "xin lỗi", "sorry",
)

_LEGAL_KEYWORDS = (
    "luật", "điều", "khoản", "hợp đồng", "đất", "tòa", "kiện",
    "vi phạm", "quyền", "nghĩa vụ", "tranh chấp", "bồi thường",
    "lao động", "sa thải", "nợ", "tiền", "thuê", "mua", "bán",
    "thừa kế", "di chúc", "ly hôn", "công ty", "cổ đông",
)


def _is_chitchat(text: str) -> bool:
    """Returns True for greetings/small-talk that don't need legal analysis."""
    t = text.strip().lower()
    if len(t) > 80:
        return False
    if any(kw in t for kw in _LEGAL_KEYWORDS):
        return False
    return any(t == p or t.startswith(p + " ") or t.startswith(p + "!") or t.startswith(p + ",")
               for p in _CHITCHAT_STARTERS)


def _make_chitchat_result(situation: str, session_id: str) -> "IntelligenceResult":
    """Return a fast conversational response without running the pipeline."""
    t = situation.strip().lower()
    if any(kw in t for kw in ("cảm ơn", "cam on", "thanks", "thank")):
        reply = "Không có gì! Nếu bạn có câu hỏi pháp lý, tôi luôn sẵn sàng hỗ trợ."
    elif any(kw in t for kw in ("là ai", "là gì", "mày là")):
        reply = (
            "Tôi là **LexAI** — trợ lý pháp lý AI chuyên về luật Việt Nam. "
            "Tôi có thể giúp bạn phân tích tình huống pháp lý, trích dẫn điều luật "
            "và đề xuất hành động phù hợp trong các lĩnh vực: đất đai, hợp đồng, "
            "lao động, doanh nghiệp, dân sự, hình sự và hành chính."
        )
    elif any(kw in t for kw in ("xin lỗi", "sorry")):
        reply = "Không sao! Bạn cần tôi giúp gì về pháp lý không?"
    else:
        reply = (
            "Xin chào! Tôi là **LexAI**, trợ lý pháp lý AI. "
            "Bạn hãy mô tả tình huống pháp lý của mình — tôi sẽ phân tích quyền lợi, "
            "trích dẫn điều luật cụ thể và đề xuất các bước thực hiện."
        )
    return IntelligenceResult(
        session_id=session_id,
        trace_id=f"chitchat_{uuid.uuid4().hex[:8]}",
        situation_summary=situation,
        legal_position_strength="",
        position_score=0.0,
        position_reasoning="",
        relevant_laws=[],
        similar_cases=[],
        recommended_actions=[],
        warnings=[],
        risk_assessment={},
        full_assessment=reply,
        citations=[],
        is_grounded=False,
        used_llm=False,
        tool_calls_made=[],
        detected_domain="general",
        domain_confidence=0.0,
        dispute_classification="chitchat",
        stage_count=0,
        stage_timings={},
        ranking_weights={},
        is_chitchat=True,
    )


def _compute_position(
    laws: List[Dict], plan: QueryPlan
) -> tuple[float, str, str]:
    if not laws:
        return 0.28, "Yếu", "Không tìm thấy đủ cơ sở pháp lý để đánh giá."

    top_score = float(laws[0].get("relevance_score", 0.5))
    strong_count = sum(1 for l in laws if float(l.get("relevance_score", 0)) >= 0.55)

    if top_score >= 0.75 and strong_count >= 3:
        return 0.83, "Mạnh", (
            f"Tìm thấy {strong_count} điều luật liên quan trực tiếp "
            f"(độ phù hợp cao nhất: {top_score:.0%}). Cơ sở pháp lý vững chắc."
        )
    if top_score >= 0.55 or strong_count >= 2:
        return 0.55, "Trung bình", (
            f"Tìm thấy {strong_count} điều luật liên quan "
            f"(độ phù hợp cao nhất: {top_score:.0%}). Cần thêm bằng chứng."
        )
    return 0.28, "Yếu", (
        f"Cơ sở pháp lý còn yếu (độ phù hợp cao nhất: {top_score:.0%}). "
        "Cần tư vấn chuyên sâu từ luật sư."
    )


def _identify_risks(situation: str, plan: QueryPlan) -> List[str]:
    q = situation.lower()
    risk_map = [
        ("giấy tay", "Giao dịch bằng giấy tay tiềm ẩn rủi ro vô hiệu hợp đồng."),
        ("không công chứng", "Hợp đồng chưa công chứng có thể không có giá trị pháp lý."),
        ("quá hạn", "Có thể đã hết thời hiệu khởi kiện — cần kiểm tra ngay."),
        ("không có biên lai", "Thiếu bằng chứng thanh toán là rủi ro pháp lý lớn."),
        ("miệng", "Thỏa thuận bằng miệng rất khó chứng minh trước tòa."),
        ("không đăng ký", "Giao dịch chưa đăng ký có thể không được pháp luật bảo vệ."),
        ("sang tên", "Chưa hoàn tất thủ tục sang tên — quyền sở hữu có thể chưa hợp lệ."),
        ("tranh chấp nhiều bên", "Tranh chấp nhiều bên làm tăng độ phức tạp và chi phí pháp lý."),
    ]
    return [msg for kw, msg in risk_map if kw in q][:4]


def _extract_warnings(laws: List[Dict], plan: QueryPlan) -> List[str]:
    warnings = []
    if not laws:
        warnings.append("Không tìm thấy đủ văn bản luật liên quan. Hãy cung cấp thêm thông tin.")
    if plan.domain_confidence < 0.35:
        warnings.append("Lĩnh vực pháp lý chưa được xác định rõ ràng. Kết quả có thể cần xem xét lại.")
    return warnings


def _generate_recommendations(
    plan: QueryPlan, strength: str, risks: List[str]
) -> List[str]:
    actions: List[str] = []
    if strength == "Yếu":
        actions.append("Tư vấn ngay với luật sư chuyên môn trước khi thực hiện bất kỳ hành động pháp lý nào.")
    if risks:
        actions.append("Khắc phục các rủi ro pháp lý đã phát hiện trước khi tiến hành vụ kiện.")
    if "tranh_chap" in plan.dispute_type:
        actions.append("Thu thập đầy đủ tài liệu, hợp đồng, biên lai và bằng chứng liên quan.")
        actions.append("Cân nhắc hòa giải trước khi khởi kiện để tiết kiệm thời gian và chi phí.")
    if plan.detected_domain == "dat_dai":
        actions.append("Kiểm tra tính hợp pháp của giấy tờ đất và đối chiếu với bản đồ địa chính.")
    actions.append("Theo dõi thời hiệu khởi kiện để không bỏ lỡ quyền lợi pháp lý.")
    return actions[:5]


def _synthesize_assessment(
    situation: str,
    plan: QueryPlan,
    strength: str,
    laws: List[Dict],
    cases: List[Dict],
) -> str:
    domain_labels = {
        "dat_dai": "đất đai", "hop_dong": "hợp đồng", "lao_dong": "lao động",
        "doanh_nghiep": "doanh nghiệp", "dan_su": "dân sự",
        "hinh_su": "hình sự", "hanh_chinh": "hành chính",
    }
    domain_name = domain_labels.get(plan.detected_domain, plan.detected_domain.replace("_", " "))
    law_refs = [l.get("law_reference", "") for l in laws[:3] if l.get("law_reference")]
    law_str = ", ".join(law_refs) if law_refs else "các quy định pháp luật hiện hành"
    case_ref = f" Tìm thấy {len(cases)} án lệ tương tự có thể tham khảo." if cases else ""

    return (
        f"Tình huống pháp lý liên quan đến lĩnh vực {domain_name}. "
        f"Vị thế pháp lý được đánh giá là: {strength}. "
        f"Căn cứ pháp lý chính: {law_str}.{case_ref} "
        f"Khuyến nghị thu thập đầy đủ bằng chứng và tham khảo ý kiến luật sư "
        f"trước khi thực hiện các bước pháp lý tiếp theo."
    )
