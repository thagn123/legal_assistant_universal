"""
ReasoningTrace — Structured explainability trace for the Legal Intelligence Pipeline.

Every orchestration run produces a ReasoningTrace that:
  - Documents each stage's inputs, outputs, and timing (ms)
  - Is fully JSON-serializable for UI visualization and competition demos
  - Is stored in MongoDB reasoning_traces collection via SessionStore
  - Enables debugging of retrieval quality, ranking decisions, and LLM behavior

Structure:
  trace_id    → unique ID, links to GET /intelligence/trace/{trace_id}
  session_id  → conversation session this trace belongs to
  stages      → ordered list of StageTrace (one per pipeline stage)
  final_result_summary → compact result snapshot for dashboard display
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Stage trace
# ---------------------------------------------------------------------------


@dataclass
class StageTrace:
    stage_id: int           # 1-7
    stage_name: str
    started_at: str         # ISO 8601
    completed_at: str       # ISO 8601
    duration_ms: float
    input_summary: Dict[str, Any]    # key params passed in (not full data)
    output_summary: Dict[str, Any]   # key results (counts, top scores, etc.)
    warnings: List[str]
    error: Optional[str]             # exception message if stage failed


# ---------------------------------------------------------------------------
# Reasoning trace
# ---------------------------------------------------------------------------


@dataclass
class ReasoningTrace:
    """
    Complete trace for one orchestration run.
    Immutable after TraceBuilder.build() is called.
    """
    trace_id: str
    session_id: str
    user_id: str
    query: str                        # truncated to 300 chars
    stages: List[StageTrace]
    total_duration_ms: float
    final_result_summary: Dict[str, Any]
    created_at: str
    is_complete: bool                 # True if all stages completed without error
    used_fallback: bool               # True if orchestrator fell back to LegalAgent

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "query": self.query,
            "created_at": self.created_at,
            "total_duration_ms": self.total_duration_ms,
            "is_complete": self.is_complete,
            "used_fallback": self.used_fallback,
            "stages": [
                {
                    "stage_id":      st.stage_id,
                    "stage_name":    st.stage_name,
                    "started_at":    st.started_at,
                    "completed_at":  st.completed_at,
                    "duration_ms":   st.duration_ms,
                    "input_summary": st.input_summary,
                    "output_summary": st.output_summary,
                    "warnings":      st.warnings,
                    "error":         st.error,
                }
                for st in self.stages
            ],
            "final_result_summary": self.final_result_summary,
        }


# ---------------------------------------------------------------------------
# TraceBuilder — fluent, incremental builder
# ---------------------------------------------------------------------------


class TraceBuilder:
    """
    Fluent builder for assembling a ReasoningTrace across 7 pipeline stages.
    Not thread-safe; create one instance per request.

    Usage:
        builder = TraceBuilder(session_id, user_id, query)
        builder.begin_stage(1, "query_planning", {"query_len": 42})
        # ... run stage logic ...
        builder.end_stage({"domain": "dat_dai", "confidence": 0.91})
        # ...
        trace = builder.build(final_result_summary={...})
    """

    def __init__(self, session_id: str, user_id: str, query: str) -> None:
        self._trace_id = str(uuid.uuid4())
        self._session_id = session_id
        self._user_id = user_id
        self._query = query[:300]
        self._created_at = _now()
        self._t_global = time.perf_counter()
        self._stages: List[StageTrace] = []

        # Per-stage state
        self._current_stage_id: Optional[int] = None
        self._current_stage_name: Optional[str] = None
        self._current_input: Optional[Dict[str, Any]] = None
        self._current_t: Optional[float] = None
        self._current_started_at: Optional[str] = None

    @property
    def trace_id(self) -> str:
        return self._trace_id

    def begin_stage(
        self,
        stage_id: int,
        stage_name: str,
        input_summary: Dict[str, Any],
    ) -> "TraceBuilder":
        """Record stage start. Must be followed by end_stage()."""
        self._current_stage_id = stage_id
        self._current_stage_name = stage_name
        self._current_input = input_summary
        self._current_t = time.perf_counter()
        self._current_started_at = _now()
        return self

    def end_stage(
        self,
        output_summary: Dict[str, Any],
        warnings: Optional[List[str]] = None,
        error: Optional[str] = None,
    ) -> StageTrace:
        """Compute duration and commit the stage. Returns the recorded StageTrace."""
        if self._current_t is None:
            raise RuntimeError("end_stage() called without begin_stage()")

        duration_ms = round((time.perf_counter() - self._current_t) * 1000, 2)
        stage = StageTrace(
            stage_id=self._current_stage_id or 0,
            stage_name=self._current_stage_name or "unknown",
            started_at=self._current_started_at or _now(),
            completed_at=_now(),
            duration_ms=duration_ms,
            input_summary=self._current_input or {},
            output_summary=output_summary,
            warnings=warnings or [],
            error=error,
        )
        self._stages.append(stage)

        # Reset current stage state
        self._current_stage_id = None
        self._current_stage_name = None
        self._current_input = None
        self._current_t = None
        self._current_started_at = None

        return stage

    def build(
        self,
        final_result_summary: Dict[str, Any],
        used_fallback: bool = False,
    ) -> ReasoningTrace:
        """Finalize and return the immutable ReasoningTrace."""
        total_ms = round((time.perf_counter() - self._t_global) * 1000, 2)
        is_complete = (
            len(self._stages) >= 5
            and all(st.error is None for st in self._stages)
        )
        return ReasoningTrace(
            trace_id=self._trace_id,
            session_id=self._session_id,
            user_id=self._user_id,
            query=self._query,
            stages=list(self._stages),
            total_duration_ms=total_ms,
            final_result_summary=final_result_summary,
            created_at=self._created_at,
            is_complete=is_complete,
            used_fallback=used_fallback,
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
