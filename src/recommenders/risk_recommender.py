"""
Risk Recommender — surfaces legal risks based on:
  1. MongoDB $vectorSearch on risks.embedding (situation-to-risk semantic match)
  2. MongoDB Aggregation Pipeline: risks derived from user's interaction history
     (if user has viewed many "dat_dai" docs, surface land-related risks)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from src.mongodb.mongo_storage import VectorStorage
from src.pipeline.embedding_stage import embed_text

logger = logging.getLogger(__name__)


@dataclass
class RiskRecommendation:
    risk_id: str
    name: str
    severity: str               # "cao" | "trung_binh" | "thap"
    description: str
    indicators: List[str]       # warning signs to watch for
    mitigation: List[str]       # how to reduce this risk
    related_law_types: List[str]
    source: str                 # "vector_search" | "history_analysis"
    score: float


class RiskRecommender:
    """
    Identifies legal risks relevant to the user's situation or history.

    Usage:
        rec = RiskRecommender(vector_storage)
        # From a specific situation:
        results = rec.recommend_from_situation("đang thuê nhà không có hợp đồng viết tay")
        # From user history:
        results = rec.recommend_from_history("u_123")
    """

    def __init__(self, vector_storage: VectorStorage) -> None:
        self._vs = vector_storage

    def recommend_from_situation(
        self,
        situation: str,
        user_id: Optional[str] = None,
        limit: int = 6,
    ) -> List[RiskRecommendation]:
        """
        Recommend risks semantically related to the described situation
        using MongoDB $vectorSearch.
        """
        results: List[RiskRecommendation] = []
        embedding = embed_text(situation)
        if embedding:
            raw = self._vs.vector_search_risks(query_vector=embedding, limit=limit)
            results = [_to_recommendation(r, "vector_search") for r in raw]

        if not results:
            # Keyword fallback: find risks where description contains key words
            keywords = [w for w in situation.split() if len(w) > 3][:6]
            if keywords:
                pattern = "|".join(keywords)
                try:
                    raw = list(
                        self._vs.risks.find(
                            {"description": {"$regex": pattern, "$options": "i"}},
                            {"_id": 0, "embedding": 0},
                        ).limit(limit)
                    )
                    results = [_to_recommendation(r, "keyword_search") for r in raw]
                except Exception as exc:
                    logger.warning("risk keyword fallback failed: %s", exc)

        if user_id:
            self._vs.log_interaction(
                user_id=user_id,
                doc_id="__risk__",
                action_type="risk_recommendation",
                context={"situation": situation[:200]},
            )

        return results[:limit]

    def recommend_from_history(
        self,
        user_id: str,
        limit: int = 6,
    ) -> List[RiskRecommendation]:
        """
        Recommend risks using MongoDB Aggregation Pipeline over interaction history.

        Pipeline logic:
          interactions → group by law_type → lookup risks.related_law_types → rank
        """
        raw = self._vs.get_risks_from_history(user_id, limit=limit)
        results = []
        for entry in raw:
            r = entry.get("risk", {})
            if not r:
                continue
            results.append(
                RiskRecommendation(
                    risk_id=r.get("risk_id", ""),
                    name=r.get("name", ""),
                    severity=r.get("severity", "trung_binh"),
                    description=r.get("description", ""),
                    indicators=r.get("indicators", []),
                    mitigation=r.get("mitigation", []),
                    related_law_types=r.get("related_law_types", []),
                    source="history_analysis",
                    score=round(min(entry.get("interaction_count", 1) / 10, 1.0), 3),
                )
            )
        return results


def _to_recommendation(doc: dict, source: str) -> RiskRecommendation:
    return RiskRecommendation(
        risk_id=doc.get("risk_id", ""),
        name=doc.get("name", ""),
        severity=doc.get("severity", "trung_binh"),
        description=doc.get("description", ""),
        indicators=doc.get("indicators", []),
        mitigation=doc.get("mitigation", []),
        related_law_types=doc.get("related_law_types", []),
        source=source,
        score=round(float(doc.get("vector_score", 0.5)), 3),
    )
