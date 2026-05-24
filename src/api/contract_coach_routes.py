from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.deps import require_user
from src.services.clause_coach_service import ClauseCoachService

coach_router = APIRouter(prefix="/contracts", tags=["contracts"])
_coach_service = ClauseCoachService()


# ── Pydantic models ──────────────────────────────────────────────────────────


class CoachRequest(BaseModel):
    clause_text: str = Field(..., min_length=10, max_length=5000)
    contract_type: Optional[str] = None


class ClauseRiskOut(BaseModel):
    id: str
    type: str
    description: str
    severity: str
    law_basis: str
    matched_phrase: str


class SaferVersionOut(BaseModel):
    original_phrase: str
    suggested_phrase: str
    reason: str


class MissingClauseOut(BaseModel):
    clause_type: str
    importance: str
    template: str
    law_basis: str


class CoachResponse(BaseModel):
    request_id: str
    feature: str = "clause_coach"
    clause_text: str
    clause_type: str
    clause_type_label: str
    risks: List[ClauseRiskOut]
    safer_versions: List[SaferVersionOut]
    missing_clauses: List[MissingClauseOut]
    risk_score: float
    risk_level: str
    summary: str


@coach_router.post("/coach", response_model=CoachResponse)
def coach_clause(body: CoachRequest, user_id: str = Depends(require_user)):
    result = _coach_service.analyze(
        clause_text=body.clause_text,
        contract_type=body.contract_type,
    )
    return CoachResponse(
        request_id="cch_" + uuid.uuid4().hex[:8],
        clause_text=result.clause_text,
        clause_type=result.clause_type,
        clause_type_label=result.clause_type_label,
        risks=[ClauseRiskOut(**vars(r)) for r in result.risks],
        safer_versions=[SaferVersionOut(**vars(sv)) for sv in result.safer_versions],
        missing_clauses=[MissingClauseOut(**vars(mc)) for mc in result.missing_clauses],
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        summary=result.summary,
    )
