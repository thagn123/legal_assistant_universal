from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.deps import require_user
from src.services.action_planner_service import ActionPlannerService

guidance_router = APIRouter(prefix="/guidance", tags=["guidance"])

_planner = ActionPlannerService()


# ── Pydantic models ──────────────────────────────────────────────────────────


class ActionRequest(BaseModel):
    situation: str
    facts: List[str] = []
    domain_hint: Optional[str] = None


class ActionItemOut(BaseModel):
    step: str
    priority: str
    reason: str
    deadline: str
    category: str


class ActionPlanResponse(BaseModel):
    request_id: str
    feature: str = "action_planner"
    domain: str
    stage: str
    stage_label: str
    immediate_actions: List[ActionItemOut]
    important_actions: List[ActionItemOut]
    optional_actions: List[ActionItemOut]
    total_actions: int
    urgency: str
    summary: str


# ── Endpoint ─────────────────────────────────────────────────────────────────


def _item_out(item) -> ActionItemOut:
    return ActionItemOut(
        step=item.step,
        priority=item.priority,
        reason=item.reason,
        deadline=item.deadline,
        category=item.category,
    )


@guidance_router.post("/actions", response_model=ActionPlanResponse)
def get_action_plan(
    body: ActionRequest,
    user_id: str = Depends(require_user),
) -> ActionPlanResponse:
    """
    Sinh kế hoạch hành động pháp lý ưu tiên theo giai đoạn vụ việc,
    lĩnh vực pháp lý, và khoảng trống chứng cứ hiện có.
    """
    result = _planner.plan(
        situation=body.situation,
        facts=body.facts,
        domain_hint=body.domain_hint,
    )
    return ActionPlanResponse(
        request_id="act_" + str(uuid.uuid4())[:8],
        domain=result.domain,
        stage=result.stage,
        stage_label=result.stage_label,
        immediate_actions=[_item_out(a) for a in result.immediate_actions],
        important_actions=[_item_out(a) for a in result.important_actions],
        optional_actions=[_item_out(a) for a in result.optional_actions],
        total_actions=result.total_actions,
        urgency=result.urgency,
        summary=result.summary,
    )
