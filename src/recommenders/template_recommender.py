"""
Template Recommender — suggests contract templates by industry / context.

Uses:
  1. MongoDB $vectorSearch on templates.embedding (semantic match)
  2. Fallback: tag-based lookup by industry + contract_type

Seed templates are loaded from src/mongodb/seed_data.py on first startup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from src.mongodb.mongo_storage import VectorStorage
from src.pipeline.embedding_stage import embed_text

logger = logging.getLogger(__name__)


@dataclass
class TemplateRecommendation:
    template_id: str
    name: str
    industry: str
    contract_type: str
    description: str
    key_clauses: List[str]
    related_laws: List[str]
    vector_score: float
    download_hint: str          # e.g. "Dùng cho thuê nhà dân dụng dưới 1 năm"


class TemplateRecommender:
    """
    Recommends mẫu hợp đồng (contract templates) based on user context.

    Usage:
        rec = TemplateRecommender(vector_storage)
        results = rec.recommend(
            context="tôi muốn thuê văn phòng 2 năm ở Hà Nội",
            industry="bat_dong_san",
        )
    """

    def __init__(self, vector_storage: VectorStorage) -> None:
        self._vs = vector_storage

    def recommend(
        self,
        context: str,
        industry: Optional[str] = None,
        contract_type: Optional[str] = None,
        limit: int = 5,
        user_id: Optional[str] = None,
    ) -> List[TemplateRecommendation]:
        """
        Return template recommendations matching the given context.

        Args:
            context:       Free-text description of what the user needs.
            industry:      Industry filter (e.g. "bat_dong_san", "lao_dong").
            contract_type: Type filter (e.g. "thue_nha", "lao_dong").
            limit:         Max results.
            user_id:       Caller ID for interaction logging.
        """
        raw_docs = []

        # 1. Try vector search
        embedding = embed_text(context)
        if embedding:
            raw_docs = self._vs.vector_search_templates(
                query_vector=embedding,
                industry=industry,
                contract_type=contract_type,
                limit=limit,
            )

        # 2. Fallback to tag-based if vector search returned nothing
        if not raw_docs:
            raw_docs = self._vs.get_templates_by_profile(
                industry=industry,
                contract_type=contract_type,
                limit=limit,
            )

        # Log interaction
        if user_id:
            self._vs.log_interaction(
                user_id=user_id,
                doc_id="__template__",
                action_type="template_recommendation",
                context={
                    "context": context[:200],
                    "industry": industry,
                    "contract_type": contract_type,
                    "law_type": industry,
                },
            )

        return [_to_recommendation(d) for d in raw_docs[:limit]]


def _to_recommendation(doc: dict) -> TemplateRecommendation:
    return TemplateRecommendation(
        template_id=doc.get("template_id", ""),
        name=doc.get("name", ""),
        industry=doc.get("industry", "general"),
        contract_type=doc.get("contract_type", ""),
        description=doc.get("description", ""),
        key_clauses=doc.get("key_clauses", []),
        related_laws=doc.get("related_laws", []),
        vector_score=round(float(doc.get("vector_score", 0.0)), 3),
        download_hint=doc.get("download_hint", ""),
    )
