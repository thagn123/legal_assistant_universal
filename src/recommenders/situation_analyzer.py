"""
Legal Situation Analyzer — the core recommendation feature.

Given a user's natural-language description of a legal situation, this module:
  1. Embeds the situation with a multilingual sentence model
  2. Runs MongoDB $vectorSearch to find the most relevant law chunks
  3. Falls back to keyword search when embeddings are unavailable
  4. Builds an EvidenceBundle and passes it to ReasoningEngine
  5. Structures the result into a SituationAnalysis with:
       - Relevant laws (grounded in the indexed knowledge base)
       - Legal position strength (Mạnh / Trung bình / Yếu)
       - Recommended action steps
       - Warnings and risks
       - A full AI-generated assessment

Example:
    analyzer = SituationAnalyzer(vector_storage)
    result = analyzer.analyze(
        situation="Tôi đang tranh chấp đất với hàng xóm, họ xây tường lấn sang 50cm đất sổ đỏ của tôi.",
        user_id="u_abc",
        user_role="nguyen_don",
        law_type="dat_dai",
    )
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from src.graphrag.evidence_bundle import EvidenceBundle, assemble_evidence_bundle, empty_bundle
from src.graphrag.reasoning import ReasoningEngine
from src.mongodb.mongo_storage import VectorStorage
from src.pipeline.embedding_stage import embed_text
from src.schemas.chunk import Chunk, ChunkSet

logger = logging.getLogger(__name__)

_reasoning_engine = ReasoningEngine()

# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------


@dataclass
class LawRecommendation:
    """A single relevant law article/clause returned by the analyzer."""

    chunk_id: str
    content: str                # Excerpt (≤ 600 chars)
    law_reference: str          # e.g. "Luật Đất đai 2024 — Điều 168"
    relevance_score: float      # 0.0–1.0 (from $vectorSearch cosine score)
    applicability: str          # Short explanation of how this law applies


@dataclass
class SituationAnalysis:
    """Full analysis result returned to the API caller."""

    situation_id: str
    situation_summary: str

    # Position
    legal_position_strength: str    # "Mạnh" | "Trung bình" | "Yếu"
    position_score: float           # 0.0–1.0
    position_reasoning: str         # 1–3 sentence explanation

    # Grounded recommendations
    relevant_laws: List[LawRecommendation]
    recommended_actions: List[str]
    warnings: List[str]
    missing_evidence: List[str]

    # Full AI assessment (from ReasoningEngine)
    full_assessment: str
    citations: List[str]
    is_grounded: bool               # True if real law chunks were found

    # Collaborative signal
    similar_situations_count: int   # how many similar queries exist in the system


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class SituationAnalyzer:
    """
    Analyses a legal situation using MongoDB Vector Search + ReasoningEngine.

    Thread-safe: no mutable state after __init__.
    """

    def __init__(self, vector_storage: VectorStorage) -> None:
        self._vs = vector_storage

    def analyze(
        self,
        situation: str,
        user_id: str,
        user_role: str = "nguyen_don",
        law_type: Optional[str] = None,
        situation_id: Optional[str] = None,
    ) -> SituationAnalysis:
        """
        Analyse *situation* and return grounded legal recommendations.

        Args:
            situation:    Natural-language description of the legal situation.
            user_id:      Caller's user ID (used for interaction logging).
            user_role:    "nguyen_don" (plaintiff) | "bi_don" (defendant) | "tu_van" (advisor).
            law_type:     Optional domain hint for post-filtering (e.g. "dat_dai").
            situation_id: Stable ID; auto-generated if omitted.
        """
        sit_id = situation_id or ("sit_" + str(uuid.uuid4())[:8])

        # ── 1. Log interaction (for collaborative filtering) ─────────────────
        if self._vs is not None:
            try:
                self._vs.log_interaction(
                    user_id=user_id,
                    doc_id="__situation__",
                    action_type="situation_analysis",
                    context={
                        "situation": situation[:300],
                        "law_type": law_type,
                        "user_role": user_role,
                    },
                )
            except Exception:
                pass

        # ── 2. Retrieve relevant law chunks from MongoDB ──────────────────────
        mongo_chunks = self._retrieve_chunks(situation, law_type)

        # ── 3. Build EvidenceBundle for ReasoningEngine ───────────────────────
        seed_chunks = _mongo_chunks_to_chunks(mongo_chunks)
        bundle = _build_bundle(sit_id, seed_chunks)
        is_grounded = len(seed_chunks) > 0

        # ── 4. Compose a structured analysis query ────────────────────────────
        role_label = {
            "nguyen_don": "nguyên đơn (người khởi kiện)",
            "bi_don": "bị đơn (người bị kiện)",
            "tu_van": "người cần tư vấn pháp lý",
        }.get(user_role, user_role)

        analysis_query = (
            f"Phân tích tình huống pháp lý: {situation}\n\n"
            f"Người dùng là {role_label}.\n"
            + (f"Lĩnh vực pháp lý liên quan: {law_type}.\n" if law_type else "")
            + "Hãy: (1) đánh giá vị thế pháp lý, (2) liệt kê các điều luật áp dụng, "
            "(3) đề xuất hành động cụ thể, (4) cảnh báo rủi ro và thời hiệu quan trọng."
        )

        # ── 5. Run ReasoningEngine ────────────────────────────────────────────
        reasoning = _reasoning_engine.reason(analysis_query, bundle, query_id=sit_id)

        # ── 6. Build LawRecommendations ───────────────────────────────────────
        relevant_laws = _build_law_recommendations(mongo_chunks, user_role)

        # ── 7. Determine legal position ───────────────────────────────────────
        strength, score = _classify_position(
            support_status=getattr(reasoning, "support_status", "UNSUPPORTED"),
            confidence=getattr(reasoning, "confidence", 0.3),
            user_role=user_role,
            num_laws_found=len(relevant_laws),
        )

        # ── 8. Extract actions & warnings ────────────────────────────────────
        answer = getattr(reasoning, "answer", "")
        actions = _extract_recommended_actions(answer, user_role, law_type)
        warnings = list(getattr(reasoning, "warnings", []))
        if not is_grounded:
            warnings.insert(
                0,
                "Chưa có văn bản luật nào được index trong hệ thống. "
                "Upload tài liệu luật để nhận gợi ý chính xác hơn.",
            )

        # ── 9. Count similar situations (collaborative signal) ────────────────
        similar_count = self._count_similar(situation)

        return SituationAnalysis(
            situation_id=sit_id,
            situation_summary=_summarise(situation),
            legal_position_strength=strength,
            position_score=round(score, 3),
            position_reasoning=answer[:400] if answer else "Không đủ bằng chứng để đánh giá.",
            relevant_laws=relevant_laws,
            recommended_actions=actions,
            warnings=warnings,
            missing_evidence=list(getattr(reasoning, "evidence_excerpts", []))[:3],
            full_assessment=answer or "Chưa đủ dữ liệu để phân tích. Vui lòng upload các văn bản luật liên quan.",
            citations=list(getattr(reasoning, "citations", [])),
            is_grounded=is_grounded,
            similar_situations_count=similar_count,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _retrieve_chunks(self, situation: str, law_type: Optional[str]):
        if self._vs is None:
            return []
        embedding = embed_text(situation)
        try:
            if embedding:
                chunks = self._vs.vector_search_chunks(
                    query_vector=embedding,
                    law_type=law_type,
                    limit=12,
                )
            else:
                # Keyword fallback
                keywords = [w for w in situation.split() if len(w) > 3][:8]
                chunks = self._vs.keyword_search_chunks(keywords, limit=10)
            return chunks
        except Exception:
            return []

    def _count_similar(self, situation: str) -> int:
        if self._vs is None:
            return 0
        try:
            prefix = situation[:60].replace(".", "").strip()
            return self._vs.interactions.count_documents(
                {
                    "action_type": "situation_analysis",
                    "context.situation": {"$regex": prefix[:30], "$options": "i"},
                }
            )
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


def _mongo_chunks_to_chunks(mongo_docs: list) -> List[Chunk]:
    """Convert raw MongoDB documents into Chunk objects for ReasoningEngine."""
    result = []
    for doc in mongo_docs:
        try:
            result.append(
                Chunk(
                    chunk_id=doc["chunk_id"],
                    document_id=doc.get("doc_id", "unknown"),
                    chunk_type=doc.get("chunk_type", "text"),
                    content=doc["content"],
                    confidence=min(float(doc.get("vector_score", 0.5)), 1.0),
                    canonical_refs=doc.get("canonical_refs", []),
                )
            )
        except Exception as exc:
            logger.debug("Skipping malformed chunk doc: %s", exc)
    return result


def _build_bundle(query_id: str, seed_chunks: List[Chunk]) -> EvidenceBundle:
    if not seed_chunks:
        return empty_bundle(
            query_id,
            "Chưa có văn bản luật nào trong hệ thống. Upload tài liệu để cải thiện gợi ý.",
        )
    chunk_set = ChunkSet(
        document_id="situation_search",
        chunks=seed_chunks,
        total_chunks=len(seed_chunks),
    )
    return assemble_evidence_bundle(
        query_id=query_id,
        seed_chunks=seed_chunks,
        expansion=None,
        chunk_set=chunk_set,
    )


def _build_law_recommendations(
    mongo_docs: list, user_role: str
) -> List[LawRecommendation]:
    recs = []
    for doc in mongo_docs[:8]:
        refs = doc.get("canonical_refs", [])
        law_ref = refs[0] if refs else doc.get("law_type", "Văn bản pháp luật")
        content = doc.get("content", "")
        recs.append(
            LawRecommendation(
                chunk_id=doc["chunk_id"],
                content=content[:600],
                law_reference=law_ref,
                relevance_score=round(float(doc.get("vector_score", 0.5)), 3),
                applicability=_applicability_hint(content, user_role),
            )
        )
    return recs


def _applicability_hint(content: str, user_role: str) -> str:
    """Generate a short hint about how this provision applies to the user."""
    lower = content.lower()
    if user_role == "nguyen_don":
        if any(w in lower for w in ["quyền", "được hưởng", "có quyền"]):
            return "Điều khoản này xác lập quyền lợi của bạn với tư cách nguyên đơn."
        if any(w in lower for w in ["vi phạm", "nghĩa vụ", "trách nhiệm"]):
            return "Điều khoản này xác định vi phạm của bên kia — có thể dùng làm căn cứ khởi kiện."
        return "Điều khoản liên quan — cần xem xét trong bối cảnh vụ việc cụ thể."
    elif user_role == "bi_don":
        if any(w in lower for w in ["miễn trách", "trường hợp bất khả kháng", "giới hạn"]):
            return "Điều khoản này có thể giúp giảm hoặc loại trừ trách nhiệm pháp lý của bạn."
        return "Điều khoản liên quan — cần phân tích để xây dựng lập luận bào chữa."
    else:
        return "Điều khoản cần nghiên cứu kỹ trước khi tư vấn cho khách hàng."


def _classify_position(
    support_status: str, confidence: float, user_role: str, num_laws_found: int
) -> tuple[str, float]:
    """Map evidence quality + role to a position strength label."""
    if support_status == "SUPPORTED" and confidence >= 0.65 and num_laws_found >= 3:
        return "Mạnh", confidence
    if support_status in ("SUPPORTED", "PARTIALLY_SUPPORTED") and confidence >= 0.4:
        return "Trung bình", max(confidence, 0.4)
    if num_laws_found >= 1:
        return "Yếu — cần bổ sung bằng chứng", max(confidence, 0.2)
    return "Chưa xác định — thiếu dữ liệu luật", 0.1


def _extract_recommended_actions(
    answer: str, user_role: str, law_type: Optional[str]
) -> List[str]:
    """
    Return a practical action list.
    Combines a general action based on role + domain-specific steps.
    """
    domain_actions = {
        "dat_dai": [
            "Thu thập và công chứng sổ đỏ / giấy chứng nhận quyền sử dụng đất.",
            "Thuê cơ quan đo đạc độc lập xác định mốc ranh giới đất.",
            "Gửi đơn đề nghị hòa giải tại UBND cấp xã/phường (bắt buộc trước khi khởi kiện về tranh chấp đất đai).",
            "Nếu hòa giải không thành, nộp đơn khởi kiện tại TAND cấp huyện.",
            "Kiểm tra thời hiệu khởi kiện: 3 năm kể từ khi biết hoặc phải biết quyền bị xâm phạm.",
        ],
        "hop_dong": [
            "Rà soát toàn bộ điều khoản hợp đồng, đặc biệt điều khoản phạt vi phạm và giải quyết tranh chấp.",
            "Thu thập bằng chứng vi phạm: email, tin nhắn, biên bản giao nhận, hóa đơn.",
            "Gửi thông báo vi phạm hợp đồng bằng văn bản có xác nhận nhận.",
            "Yêu cầu thực hiện hợp đồng hoặc bồi thường thiệt hại theo điều khoản đã ký.",
            "Thời hiệu khởi kiện tranh chấp hợp đồng thương mại: 2 năm.",
        ],
        "lao_dong": [
            "Thu thập hợp đồng lao động, bảng lương, quyết định sa thải / kỷ luật.",
            "Nộp đơn khiếu nại lên Phòng Lao động — Thương binh và Xã hội.",
            "Yêu cầu hòa giải qua Hội đồng hòa giải lao động cơ sở.",
            "Khởi kiện tại TAND nếu hòa giải không thành.",
            "Thời hiệu: 1 năm kể từ ngày phát sinh tranh chấp.",
        ],
        "doanh_nghiep": [
            "Kiểm tra điều lệ công ty và biên bản họp HĐQT / HĐTV liên quan.",
            "Thu thập bằng chứng vi phạm nghĩa vụ của cổ đông / thành viên.",
            "Gửi yêu cầu triệu tập cuộc họp bất thường nếu cần thiết.",
            "Khởi kiện tại Tòa kinh tế TAND nếu tranh chấp nội bộ không giải quyết được.",
        ],
    }
    base_actions = [
        "Thu thập và bảo quản tất cả tài liệu, bằng chứng liên quan (bản gốc + bản sao công chứng).",
        "Ghi chép chi tiết diễn biến sự việc với mốc thời gian cụ thể.",
        "Tham khảo ý kiến luật sư chuyên ngành để được tư vấn phù hợp với tình huống cụ thể.",
        "Xem xét phương án thương lượng / hòa giải trước khi đưa vụ việc ra tòa.",
    ]

    specific = domain_actions.get(law_type or "", [])
    return specific + [a for a in base_actions if a not in specific]


def _summarise(situation: str, max_len: int = 200) -> str:
    s = situation.strip()
    if len(s) <= max_len:
        return s
    return s[:max_len].rsplit(" ", 1)[0] + "…"
