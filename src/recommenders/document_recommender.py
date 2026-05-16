"""
Document Recommender — hybrid (vector + collaborative filtering).

Recommends relevant legal documents based on:
  1. MongoDB $vectorSearch: semantic similarity to the user's query / profile
  2. MongoDB Aggregation Pipeline: collaborative filtering
     ("users who interacted with X also interacted with Y")

The two signals are merged with a weighted blend:
  final_score = 0.6 * vector_score + 0.4 * collab_score (normalised)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from src.mongodb.mongo_storage import VectorStorage
from src.pipeline.embedding_stage import embed_text

logger = logging.getLogger(__name__)


@dataclass
class DocumentRecommendation:
    doc_id: str
    law_type: str
    snippet: str                # short excerpt of most relevant chunk
    vector_score: float         # semantic similarity
    collab_score: float         # collaborative filter score (normalised 0-1)
    final_score: float
    reason: str                 # human-readable explanation


class DocumentRecommender:
    """
    Returns ranked document recommendations for a user.

    Usage:
        rec = DocumentRecommender(vector_storage)
        results = rec.recommend(user_id="u_1", query="tranh chấp đất đai")
    """

    def __init__(self, vector_storage: VectorStorage) -> None:
        self._vs = vector_storage

    def recommend(
        self,
        user_id: str,
        query: str = "",
        law_type: Optional[str] = None,
        limit: int = 8,
    ) -> List[DocumentRecommendation]:
        """
        Return up to *limit* document recommendations.

        Args:
            user_id:  Caller's tenant ID.
            query:    Free-text query / context (used for vector search).
            law_type: Domain filter (optional).
            limit:    Max results.
        """
        # ── 1. Vector search ────────────────────────────────────────────────
        vec_results: dict[str, dict] = {}
        query_text = query or " ".join(self._vs.get_user_law_types(user_id))
        if query_text:
            embedding = embed_text(query_text)
            if embedding:
                chunks = self._vs.vector_search_chunks(
                    query_vector=embedding,
                    law_type=law_type,
                    limit=limit * 2,
                )
                for c in chunks:
                    doc_id = c.get("doc_id", "")
                    if not doc_id or doc_id == "__situation__":
                        continue
                    if doc_id not in vec_results or c.get("vector_score", 0) > vec_results[doc_id]["vector_score"]:
                        vec_results[doc_id] = {
                            "doc_id": doc_id,
                            "law_type": c.get("law_type", "general"),
                            "snippet": c.get("content", "")[:250],
                            "vector_score": float(c.get("vector_score", 0)),
                        }

        # ── 2. Collaborative filtering ───────────────────────────────────────
        viewed = self._vs.get_user_viewed_docs(user_id)
        collab_raw = self._vs.collaborative_filter_docs(viewed, user_id, limit=limit * 2)
        max_collab = max((r["collab_score"] for r in collab_raw), default=1)
        collab_map: dict[str, float] = {
            r["doc_id"]: r["collab_score"] / max(max_collab, 1)
            for r in collab_raw
        }

        # ── 3. Merge scores ─────────────────────────────────────────────────
        all_doc_ids = set(vec_results) | set(collab_map)
        merged = []
        for doc_id in all_doc_ids:
            v_score = vec_results.get(doc_id, {}).get("vector_score", 0.0)
            c_score = collab_map.get(doc_id, 0.0)
            final = 0.6 * v_score + 0.4 * c_score

            snippet = vec_results.get(doc_id, {}).get("snippet", "")
            law_t = vec_results.get(doc_id, {}).get("law_type", "general")

            reason = _build_reason(v_score, c_score)
            merged.append(
                DocumentRecommendation(
                    doc_id=doc_id,
                    law_type=law_t,
                    snippet=snippet,
                    vector_score=round(v_score, 3),
                    collab_score=round(c_score, 3),
                    final_score=round(final, 3),
                    reason=reason,
                )
            )

        merged.sort(key=lambda r: r.final_score, reverse=True)

        # ── 4. Log interaction ───────────────────────────────────────────────
        self._vs.log_interaction(
            user_id=user_id,
            doc_id="__recommendation__",
            action_type="document_recommendation",
            context={"query": query[:200], "law_type": law_type},
        )

        return merged[:limit]


def _build_reason(v_score: float, c_score: float) -> str:
    if v_score >= 0.6 and c_score >= 0.3:
        return "Tài liệu liên quan ngữ nghĩa và được nhiều người dùng tương tự quan tâm."
    if v_score >= 0.6:
        return "Tài liệu có nội dung pháp lý phù hợp với truy vấn của bạn."
    if c_score >= 0.3:
        return "Người dùng có hồ sơ tương tự đã tìm hiểu tài liệu này."
    return "Tài liệu có liên quan theo ngữ cảnh pháp lý."
