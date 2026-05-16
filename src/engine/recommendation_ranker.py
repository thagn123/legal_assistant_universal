"""
RecommendationRanker — Stage 6 of the Legal Intelligence Pipeline.

Implements multi-signal reranking of fused retrieval candidates:

  final_score = (
      w_semantic   * semantic_score    +   # cosine similarity (from vector search)
      w_behavior   * behavior_score    +   # user interaction history (collab filter)
      w_graph      * graph_score       +   # graph traversal relevance
      w_freshness  * freshness_score   +   # recency of document (exponential decay)
      w_popularity * popularity_score  +   # peer interaction count (normalized)
      w_accepted   * accepted_weight       # save/download acceptance signal
  )

Default weights sum to 1.0. Configurable at construction.
Each RankedItem includes a human-readable explanation for UI display.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.engine.retrieval_fusion import FusedResult, FusedResultSet
from src.mongodb.mongo_storage import VectorStorage
from src.observability.tracer import get_tracer

logger = logging.getLogger(__name__)

# Half-life = 180 days → λ = ln(2)/180
_FRESHNESS_LAMBDA = math.log(2) / 180

_DEFAULT_WEIGHTS: Dict[str, float] = {
    "semantic":   0.35,
    "behavior":   0.15,
    "graph":      0.20,
    "freshness":  0.15,
    "popularity": 0.10,
    "accepted":   0.05,
}

_SIGNAL_LABELS_VI: Dict[str, str] = {
    "semantic":   "nội dung ngữ nghĩa phù hợp",
    "behavior":   "phù hợp thói quen của bạn",
    "graph":      "liên kết qua đồ thị pháp lý",
    "freshness":  "tài liệu còn mới",
    "popularity": "được nhiều người dùng quan tâm",
    "accepted":   "được người dùng tương tự lưu lại",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RankedItem:
    item_id: str
    item_type: str
    content: str
    law_type: str
    law_reference: str
    raw_data: Dict[str, Any]

    # Component scores (weighted contributions, not raw)
    semantic_contribution: float
    behavior_contribution: float
    graph_contribution: float
    freshness_contribution: float
    popularity_contribution: float
    accepted_contribution: float

    final_score: float
    rank: int
    sources: List[str]
    explanation: str            # Vietnamese explanation for UI
    score_components: Dict[str, float] = field(default_factory=dict)


@dataclass
class RankingResult:
    ranked: List[RankedItem]
    weights_used: Dict[str, float]
    ranking_duration_ms: float


# ---------------------------------------------------------------------------
# RecommendationRanker
# ---------------------------------------------------------------------------


class RecommendationRanker:
    """
    Stage 6: multi-signal reranking of fused retrieval candidates.

    Usage:
        ranker = RecommendationRanker(vector_storage)
        result = ranker.rank(fused_result_set, user_id="u_123", top_k=8)
    """

    def __init__(
        self,
        vector_storage: VectorStorage,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self._vs = vector_storage
        self._weights = weights or dict(_DEFAULT_WEIGHTS)
        self._tracer = get_tracer()
        # Validate weights
        total = sum(self._weights.values())
        if abs(total - 1.0) > 0.02:
            raise ValueError(
                f"RecommendationRanker weights must sum to 1.0, got {total:.3f}"
            )

    def rank(
        self,
        fused: FusedResultSet,
        user_id: str,
        top_k: int = 10,
        trace_id: str = "",
    ) -> RankingResult:
        t0 = time.perf_counter()
        candidates = fused.results
        if not candidates:
            return RankingResult(ranked=[], weights_used=self._weights, ranking_duration_ms=0)

        # Gather batch signals
        item_ids = [c.item_id for c in candidates]
        popularity_map = self._compute_popularity(item_ids)
        accepted_map = self._compute_acceptance(item_ids)

        w = self._weights
        scored: List[tuple] = []

        for cand in candidates:
            semantic = cand.vector_score
            behavior = cand.behavior_score
            graph = cand.graph_score
            freshness = _freshness_score(cand.raw_data.get("updated_at") or cand.raw_data.get("created_at"))
            popularity = popularity_map.get(cand.item_id, 0.0)
            accepted = accepted_map.get(cand.item_id, 0.0)

            contributions = {
                "semantic":   round(w["semantic"]   * semantic,   4),
                "behavior":   round(w["behavior"]   * behavior,   4),
                "graph":      round(w["graph"]      * graph,      4),
                "freshness":  round(w["freshness"]  * freshness,  4),
                "popularity": round(w["popularity"] * popularity, 4),
                "accepted":   round(w["accepted"]   * accepted,   4),
            }
            final = round(sum(contributions.values()), 4)
            scored.append((final, cand, contributions))

        scored.sort(key=lambda x: x[0], reverse=True)

        ranked: List[RankedItem] = []
        for rank_idx, (score, cand, contrib) in enumerate(scored[:top_k], 1):
            ranked.append(RankedItem(
                item_id=cand.item_id,
                item_type=cand.item_type,
                content=cand.content,
                law_type=cand.law_type,
                law_reference=cand.law_reference,
                raw_data=cand.raw_data,
                semantic_contribution=contrib["semantic"],
                behavior_contribution=contrib["behavior"],
                graph_contribution=contrib["graph"],
                freshness_contribution=contrib["freshness"],
                popularity_contribution=contrib["popularity"],
                accepted_contribution=contrib["accepted"],
                final_score=score,
                rank=rank_idx,
                sources=cand.sources,
                explanation=_build_explanation(contrib, cand.sources),
                score_components=contrib,
            ))

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)

        self._tracer.log_ranking(
            trace_id=trace_id,
            candidates_in=len(candidates),
            candidates_out=len(ranked),
            top_score=ranked[0].final_score if ranked else 0,
            top_explanation=ranked[0].explanation if ranked else "",
            weights=self._weights,
        )

        return RankingResult(
            ranked=ranked,
            weights_used=dict(self._weights),
            ranking_duration_ms=duration_ms,
        )

    # ── Signal computation ───────────────────────────────────────────────────

    def _compute_popularity(self, item_ids: List[str]) -> Dict[str, float]:
        """Normalize peer interaction counts for the given item_ids to [0, 1]."""
        if not item_ids:
            return {}
        try:
            pipeline = [
                {"$match": {"doc_id": {"$in": item_ids}}},
                {"$group": {"_id": "$doc_id", "count": {"$sum": 1}}},
            ]
            counts = {r["_id"]: r["count"] for r in self._vs.interactions.aggregate(pipeline)}
            max_c = max(counts.values(), default=1)
            return {doc_id: round(c / max_c, 4) for doc_id, c in counts.items()}
        except Exception as exc:
            logger.warning("_compute_popularity failed: %s", exc)
            return {}

    def _compute_acceptance(self, item_ids: List[str]) -> Dict[str, float]:
        """
        Acceptance signal: count 'save' and 'download' interactions per item_id
        across ALL users (community acceptance), normalized to [0, 1].
        """
        if not item_ids:
            return {}
        try:
            pipeline = [
                {
                    "$match": {
                        "doc_id": {"$in": item_ids},
                        "action_type": {"$in": ["save", "download"]},
                    }
                },
                {"$group": {"_id": "$doc_id", "count": {"$sum": 1}}},
            ]
            counts = {r["_id"]: r["count"] for r in self._vs.interactions.aggregate(pipeline)}
            max_c = max(counts.values(), default=1)
            return {doc_id: round(c / max_c, 4) for doc_id, c in counts.items()}
        except Exception as exc:
            logger.warning("_compute_acceptance failed: %s", exc)
            return {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _freshness_score(updated_at_iso: Optional[str]) -> float:
    """
    Exponential decay freshness: exp(-λ * days_since_update).
    λ = ln(2)/180 → half-life of 180 days.
    Returns 0.65 if no date available (neutral, slightly above average).
    """
    if not updated_at_iso:
        return 0.65
    try:
        dt = datetime.fromisoformat(updated_at_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400)
        return round(math.exp(-_FRESHNESS_LAMBDA * days), 4)
    except (ValueError, TypeError):
        return 0.65


def _build_explanation(
    contributions: Dict[str, float],
    sources: List[str],
) -> str:
    """Build a Vietnamese explanation highlighting the dominant ranking signal."""
    dominant = max(contributions, key=contributions.__getitem__)
    dominant_label = _SIGNAL_LABELS_VI.get(dominant, dominant)
    top_contrib = contributions[dominant]

    source_str = " + ".join(sources) if sources else "hybrid"
    return (
        f"Xếp hạng #{1} dựa trên {dominant_label} "
        f"(đóng góp {top_contrib:.0%} | nguồn: {source_str})"
    )
