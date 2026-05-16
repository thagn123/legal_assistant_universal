"""
ExecutionTracer — Structured observability for the Legal Intelligence Pipeline.

Emits one JSON log line per pipeline event. Thread-safe singleton.
Compatible with any log aggregation system (ELK, Datadog, CloudWatch, etc.).

Log format (each line is self-contained JSON):
  {
    "ts":          "2026-05-16T10:05:00.123Z",
    "trace_id":    "tr_abc123",
    "stage_id":    3,
    "stage_name":  "retrieval_fusion",
    "event":       "end",
    "duration_ms": 142.3,
    "data":        { ... stage-specific payload }
  }
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_log = logging.getLogger("legal_intelligence.tracer")


class ExecutionTracer:
    """
    Singleton execution tracer for the Legal Intelligence Pipeline.

    Usage:
        tracer = ExecutionTracer.get()
        tracer.log_stage(trace_id, 1, "query_planning", "end", {...}, 9.2)
    """

    _instance: Optional["ExecutionTracer"] = None
    _lock: threading.Lock = threading.Lock()

    # ── Singleton ────────────────────────────────────────────────────────────

    @classmethod
    def get(cls) -> "ExecutionTracer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Core logging ─────────────────────────────────────────────────────────

    def log_stage(
        self,
        trace_id: str,
        stage_id: int,
        stage_name: str,
        event: str,                    # "start" | "end" | "error" | "warning"
        data: Dict[str, Any],
        duration_ms: Optional[float] = None,
    ) -> None:
        record: Dict[str, Any] = {
            "ts": _now(),
            "trace_id": trace_id,
            "stage_id": stage_id,
            "stage_name": stage_name,
            "event": event,
            "data": data,
        }
        if duration_ms is not None:
            record["duration_ms"] = round(duration_ms, 2)
        level = logging.ERROR if event == "error" else logging.INFO
        _log.log(level, "[TRACE] %s", json.dumps(record, ensure_ascii=False, default=str))

    def log_fallback(
        self,
        trace_id: str,
        reason: str,
        fallback_to: str,
    ) -> None:
        _log.warning(
            "[FALLBACK] %s",
            json.dumps({
                "ts": _now(),
                "trace_id": trace_id,
                "event": "fallback",
                "reason": reason[:200],
                "fallback_to": fallback_to,
            }, ensure_ascii=False),
        )

    # ── Convenience methods for common events ────────────────────────────────

    def log_retrieval(
        self,
        trace_id: str,
        signal: str,
        hits: int,
        top_score: float,
        query_variant: str,
        duration_ms: float,
    ) -> None:
        self.log_stage(trace_id, 3, "retrieval_fusion", f"signal_{signal}", {
            "signal": signal,
            "hits": hits,
            "top_score": round(top_score, 4),
            "query": query_variant[:80],
        }, duration_ms=duration_ms)

    def log_ranking(
        self,
        trace_id: str,
        candidates_in: int,
        candidates_out: int,
        top_score: float,
        top_explanation: str,
        weights: Dict[str, float],
    ) -> None:
        self.log_stage(trace_id, 6, "recommendation_ranker", "ranking_complete", {
            "candidates_in": candidates_in,
            "candidates_out": candidates_out,
            "top_score": round(top_score, 4),
            "top_explanation": top_explanation,
            "weights": weights,
        })

    def log_tool_call(
        self,
        trace_id: str,
        tool_name: str,
        args: Dict[str, Any],
        result_summary: str,
        duration_ms: float,
    ) -> None:
        self.log_stage(trace_id, 5, "tool_executor", "tool_call", {
            "tool": tool_name,
            "args": {k: str(v)[:50] for k, v in args.items()},
            "result": result_summary[:100],
        }, duration_ms=duration_ms)

    def log_graph_traversal(
        self,
        trace_id: str,
        seed_nodes: int,
        expanded_nodes: int,
        depth_reached: int,
        duration_ms: float,
    ) -> None:
        self.log_stage(trace_id, 4, "graph_expansion", "traversal_complete", {
            "seed_nodes": seed_nodes,
            "expanded_nodes": expanded_nodes,
            "depth_reached": depth_reached,
        }, duration_ms=duration_ms)


def get_tracer() -> ExecutionTracer:
    """Module-level convenience accessor for the singleton tracer."""
    return ExecutionTracer.get()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
