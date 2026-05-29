"""Deterministic evidence accuracy core."""

from src.evidence.evidence_gap_engine import (
    analyze_evidence_gap,
    filter_contradictory_recommendations,
)
from src.evidence.evidence_schemas import (
    CONTRADICTED,
    MISSING,
    PRESENT,
    UNCERTAIN,
    EvidenceAssessment,
    EvidenceFact,
    EvidenceSchema,
)

__all__ = [
    "CONTRADICTED",
    "MISSING",
    "PRESENT",
    "UNCERTAIN",
    "EvidenceAssessment",
    "EvidenceFact",
    "EvidenceSchema",
    "analyze_evidence_gap",
    "filter_contradictory_recommendations",
]
