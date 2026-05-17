"""
Document Recommender — 4-signal hybrid recommendation engine.

Signals fused with weighted blend:
  1. MongoDB $vectorSearch           — semantic similarity to query    (weight 0.40)
  2. User-Item CF (aggregation)      — "users who viewed X viewed Y"  (weight 0.25)
  3. Item-based CF ($vectorSearch)   — similar to user's read history (weight 0.20)
  4. User-User CF ($vectorSearch)    — what similar-profile users read (weight 0.15)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.mongodb.mongo_storage import VectorStorage
from src.pipeline.embedding_stage import embed_text

logger = logging.getLogger(__name__)


@dataclass
class DocumentRecommendation:
    doc_id: str
    law_type: str
    snippet: str                # short excerpt of most relevant chunk
    vector_score: float         # semantic similarity              (weight 0.40)
    collab_score: float         # user-item CF score               (weight 0.25)
    item_cf_score: float        # item-based CF via $vectorSearch  (weight 0.20)
    user_user_score: float      # user-user CF via profile embeds  (weight 0.15)
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
        Return up to *limit* document recommendations using 4 signals:
          1. MongoDB $vectorSearch     — semantic similarity to query    (0.40)
          2. User-Item CF aggregation  — "viewers of X also viewed Y"   (0.25)
          3. Item-based CF             — $vectorSearch on read history   (0.20)
          4. User-User CF              — $vectorSearch on user profiles  (0.15)
        """
        # ── 1. Semantic vector search ────────────────────────────────────────
        vec_results: Dict[str, Dict[str, Any]] = {}
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

        # ── 2. User-Item Collaborative Filtering (weighted by action type) ───
        viewed = self._vs.get_user_viewed_docs(user_id)
        collab_raw = self._vs.collaborative_filter_docs(viewed, user_id, limit=limit * 2)
        max_collab = max((r["collab_score"] for r in collab_raw), default=1)
        collab_map: Dict[str, float] = {
            r["doc_id"]: r["collab_score"] / max(max_collab, 1)
            for r in collab_raw
        }

        # ── 3. Item-based CF via $vectorSearch ───────────────────────────────
        item_cf_raw = self._vs.get_item_based_cf_docs(
            user_id, exclude_doc_ids=viewed, limit=limit * 2
        )
        item_cf_map: Dict[str, float] = {r["doc_id"]: r["item_cf_score"] for r in item_cf_raw}
        item_cf_by_doc: Dict[str, Dict] = {r["doc_id"]: r for r in item_cf_raw}

        # ── 4. User-User CF via profile embedding $vectorSearch ──────────────
        self._vs.update_user_profile_embedding(user_id)
        similar_users = self._vs.vector_search_similar_users(user_id, limit=15)
        peer_docs: List[Dict[str, Any]] = []
        user_user_map: Dict[str, float] = {}
        if similar_users:
            peer_docs = self._vs.get_trending_content_for_peers(
                peer_user_ids=similar_users,
                exclude_doc_ids=viewed,
                days=30,
                limit=limit * 2,
            )
            if peer_docs:
                max_peer = max((d["peer_count"] for d in peer_docs), default=1)
                user_user_map = {
                    d["doc_id"]: d["peer_count"] / max(max_peer, 1)
                    for d in peer_docs
                }
        peer_by_doc: Dict[str, Dict] = {d["doc_id"]: d for d in peer_docs}

        # ── 5. Fuse 4 signals ────────────────────────────────────────────────
        all_doc_ids = set(vec_results) | set(collab_map) | set(item_cf_map) | set(user_user_map)
        merged = []
        for doc_id in all_doc_ids:
            v_score = vec_results.get(doc_id, {}).get("vector_score", 0.0)
            c_score = collab_map.get(doc_id, 0.0)
            i_score = item_cf_map.get(doc_id, 0.0)
            u_score = user_user_map.get(doc_id, 0.0)
            final = 0.40 * v_score + 0.25 * c_score + 0.20 * i_score + 0.15 * u_score

            snippet = vec_results.get(doc_id, {}).get("snippet", "")
            law_t = (
                vec_results.get(doc_id, {}).get("law_type")
                or item_cf_by_doc.get(doc_id, {}).get("law_type")
                or peer_by_doc.get(doc_id, {}).get("law_type")
                or "general"
            )

            merged.append(
                DocumentRecommendation(
                    doc_id=doc_id,
                    law_type=law_t,
                    snippet=snippet,
                    vector_score=round(v_score, 3),
                    collab_score=round(c_score, 3),
                    item_cf_score=round(i_score, 3),
                    user_user_score=round(u_score, 3),
                    final_score=round(final, 3),
                    reason=_build_reason(v_score, c_score, i_score, u_score),
                )
            )

        merged.sort(key=lambda r: r.final_score, reverse=True)

        # ── 6. Log interaction ───────────────────────────────────────────────
        self._vs.log_interaction(
            user_id=user_id,
            doc_id="__recommendation__",
            action_type="document_recommendation",
            context={"query": query[:200], "law_type": law_type},
        )

        return merged[:limit]


def _build_reason(v_score: float, c_score: float, i_score: float, u_score: float) -> str:
    signals = []
    if v_score >= 0.5:
        signals.append("nội dung phù hợp ngữ nghĩa")
    if c_score >= 0.3:
        signals.append("người dùng tương tự đã xem")
    if i_score >= 0.3:
        signals.append("tương tự tài liệu bạn đã nghiên cứu")
    if u_score >= 0.2:
        signals.append("phổ biến trong nhóm hồ sơ tương tự")
    if signals:
        return "Gợi ý dựa trên: " + ", ".join(signals) + "."
    return "Tài liệu có liên quan theo ngữ cảnh pháp lý."
