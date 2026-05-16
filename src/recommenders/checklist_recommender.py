"""
Checklist Recommender — suggests compliance checklists by business type / transaction type.

Logic: rule-based tag matching via MongoDB query.
No vector search needed — checklists are keyed by well-defined categories.

Seed checklists are loaded from src/mongodb/seed_data.py on first startup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from src.mongodb.mongo_storage import VectorStorage

logger = logging.getLogger(__name__)


@dataclass
class ChecklistItem:
    item_id: str
    category: str               # e.g. "Giấy tờ pháp lý", "Tài chính", "Nhân sự"
    description: str
    required: bool              # True = bắt buộc, False = khuyến nghị
    related_law: str            # e.g. "Luật Doanh nghiệp 2020 — Điều 22"
    deadline_note: str          # e.g. "Phải nộp trong 30 ngày kể từ ngày ký HĐ"


@dataclass
class ChecklistRecommendation:
    checklist_id: str
    name: str
    business_type: str
    transaction_type: str
    description: str
    items: List[ChecklistItem]
    related_laws: List[str]
    priority: int               # lower = more important


class ChecklistRecommender:
    """
    Recommends compliance checklists for business activities or transactions.

    Usage:
        rec = ChecklistRecommender(vector_storage)
        results = rec.recommend(
            business_type="tnhh_mot_thanh_vien",
            transaction_type="thanh_lap_cong_ty",
        )
    """

    def __init__(self, vector_storage: VectorStorage) -> None:
        self._vs = vector_storage

    def recommend(
        self,
        business_type: Optional[str] = None,
        transaction_type: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[ChecklistRecommendation]:
        """
        Return checklists matching the given business/transaction context.

        Args:
            business_type:    e.g. "tnhh", "co_phan", "ca_nhan", "ho_kinh_doanh"
            transaction_type: e.g. "thanh_lap_cong_ty", "mua_ban_dat", "thue_lao_dong"
            user_id:          Caller ID for interaction logging.
            limit:            Max checklists returned.
        """
        raw = self._vs.get_checklists(
            business_type=business_type,
            transaction_type=transaction_type,
            limit=limit,
        )

        if user_id:
            self._vs.log_interaction(
                user_id=user_id,
                doc_id="__checklist__",
                action_type="checklist_recommendation",
                context={
                    "business_type": business_type,
                    "transaction_type": transaction_type,
                    "law_type": transaction_type,
                },
            )

        return [_to_recommendation(d) for d in raw]


def _to_recommendation(doc: dict) -> ChecklistRecommendation:
    items = [
        ChecklistItem(
            item_id=it.get("item_id", ""),
            category=it.get("category", ""),
            description=it.get("description", ""),
            required=it.get("required", True),
            related_law=it.get("related_law", ""),
            deadline_note=it.get("deadline_note", ""),
        )
        for it in doc.get("items", [])
    ]
    return ChecklistRecommendation(
        checklist_id=doc.get("checklist_id", ""),
        name=doc.get("name", ""),
        business_type=doc.get("business_type", "general"),
        transaction_type=doc.get("transaction_type", ""),
        description=doc.get("description", ""),
        items=items,
        related_laws=doc.get("related_laws", []),
        priority=doc.get("priority", 99),
    )
