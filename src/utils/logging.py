"""
Structured logging for the Legal Multimodal GraphRAG pipeline.

Matches the observability contract in docs/logging/observability.md.

Every log event is machine-readable (JSON) and human-readable.
Required fields per event: trace_id, document_id, module, stage, status, timestamp.

Log families:
- extraction | ocr | parser_qa | chunk | graph | retrieval | response | confidence | error
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Stage outcome → Python log severity mapping
# Separates stage outcome values (pass/fail/warning/skipped) from
# Python logging levels (info/error/warning/debug).
# ---------------------------------------------------------------------------

_SEVERITY_MAP: Dict[str, str] = {
    "pass": "info",
    "fail": "error",
    "skipped": "info",
    "warning": "warning",
    "info": "info",
    "error": "error",
    "debug": "debug",
}


# ---------------------------------------------------------------------------
# Internal log event record (machine-readable)
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_event(
    trace_id: str,
    module: str,
    stage: str,
    stage_status: str,
    severity: str,
    document_id: str = "",
    query_id: str = "",
    parent_event_id: str = "",
    reason_codes: Optional[List[str]] = None,
    input_refs: Optional[List[str]] = None,
    output_refs: Optional[List[str]] = None,
    confidence_summary: Optional[Dict[str, Any]] = None,
    thresholds: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a structured log event dict.

    Fields:
        stage_status — pipeline outcome: pass | fail | warning | skipped | info | error
        severity     — Python log level:  debug | info | warning | error

    These are separate concepts: a stage can produce a "warning" outcome (stage_status)
    while still being logged at "warning" severity, or a stage marked "pass" is logged
    at "info" severity. Keeping them as distinct fields lets downstream consumers filter
    by either dimension independently.
    """
    event: Dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "parent_event_id": parent_event_id,
        "document_id": document_id,
        "query_id": query_id,
        "module": module,
        "stage": stage,
        "stage_status": stage_status,
        "severity": severity,
        "timestamp": _now_iso(),
        "reason_codes": reason_codes or [],
        "input_refs": input_refs or [],
        "output_refs": output_refs or [],
        "confidence_summary": confidence_summary or {},
        "thresholds": thresholds or {},
        "error": error,
    }
    if extra:
        event.update(extra)
    return event


# ---------------------------------------------------------------------------
# PipelineLogger
# ---------------------------------------------------------------------------


class PipelineLogger:
    """
    Structured logger for the pipeline.

    Usage:
        logger = PipelineLogger("extraction", trace_id, document_id, output_dir)
        logger.stage_start("profiling")
        logger.info("text_layer detected", extra={"coverage": 0.92})
        logger.warning("low_ocr", reason_codes=["ocr_below_threshold"], confidence_summary={"ocr": 0.61})
        logger.stage_end("profiling", status="pass")
    """

    def __init__(
        self,
        module: str,
        trace_id: str,
        document_id: str = "",
        output_dir: Optional[Path] = None,
        level: str = "INFO",
    ) -> None:
        self.module = module
        self.trace_id = trace_id
        self.document_id = document_id
        self.output_dir = output_dir
        self._events: List[Dict[str, Any]] = []

        # Standard Python logger (human-readable console output)
        self._logger = logging.getLogger(f"legal_graphrag.{module}")
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter("[%(levelname)s] %(name)s — %(message)s")
            )
            self._logger.addHandler(handler)
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        self._logger.setLevel(numeric_level)

    # ------------------------------------------------------------------
    # Core emit
    # ------------------------------------------------------------------

    def _emit(self, level: str, stage: str, message: str, **kwargs: Any) -> None:
        severity = _SEVERITY_MAP.get(level.lower(), "info")
        event = _build_event(
            trace_id=self.trace_id,
            module=self.module,
            stage=stage,
            stage_status=level,     # pipeline outcome: pass/fail/warning/skipped/…
            severity=severity,      # python log level: info/warning/error/debug
            document_id=self.document_id,
            **kwargs,
        )
        event["message"] = message
        self._events.append(event)

        log_fn = getattr(self._logger, severity, self._logger.info)
        log_fn(
            f"[{stage}] {message} | doc={self.document_id or '-'} | trace={self.trace_id[:8]}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def stage_start(self, stage: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self._emit("info", stage, f"STAGE START: {stage}", extra=extra)

    def stage_end(
        self,
        stage: str,
        status: str = "pass",
        duration_seconds: float = 0.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        msg = f"STAGE END: {stage} [{status.upper()}] ({duration_seconds:.2f}s)"
        self._emit(status, stage, msg, extra={**(extra or {}), "duration_seconds": duration_seconds})

    def info(
        self,
        message: str,
        stage: str = "pipeline",
        extra: Optional[Dict[str, Any]] = None,
        output_refs: Optional[List[str]] = None,
        confidence_summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._emit("info", stage, message, extra=extra, output_refs=output_refs,
                   confidence_summary=confidence_summary)

    def warning(
        self,
        message: str,
        stage: str = "pipeline",
        reason_codes: Optional[List[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
        confidence_summary: Optional[Dict[str, Any]] = None,
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._emit("warning", stage, message, reason_codes=reason_codes, extra=extra,
                   confidence_summary=confidence_summary, thresholds=thresholds)

    def error(
        self,
        message: str,
        stage: str = "pipeline",
        error: Optional[str] = None,
        reason_codes: Optional[List[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._emit("error", stage, message, error=error, reason_codes=reason_codes, extra=extra)
        self._logger.error(f"[{stage}] ERROR: {message}" + (f" | {error}" if error else ""))

    def decision(
        self,
        stage: str,
        decision_type: str,
        value: Any,
        reason: str = "",
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a strategy or routing decision with its reason and threshold values."""
        self._emit(
            "info",
            stage,
            f"DECISION [{decision_type}] = {value} | reason: {reason}",
            thresholds=thresholds,
        )

    # ------------------------------------------------------------------
    # Flush
    # ------------------------------------------------------------------

    def flush_to_file(self, filename: Optional[str] = None) -> Optional[Path]:
        """Write all events to a JSONL log file in the output directory."""
        if not self.output_dir:
            return None
        self.output_dir.mkdir(parents=True, exist_ok=True)
        fname = filename or f"trace_{self.trace_id[:12]}_{self.module}.jsonl"
        log_path = self.output_dir / fname
        with open(log_path, "w", encoding="utf-8") as fh:
            for ev in self._events:
                fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return log_path

    def events(self) -> List[Dict[str, Any]]:
        return list(self._events)


# ---------------------------------------------------------------------------
# Module-level convenience factory
# ---------------------------------------------------------------------------


def get_logger(
    module: str,
    trace_id: str,
    document_id: str = "",
    output_dir: Optional[Path] = None,
    level: str = "INFO",
) -> PipelineLogger:
    return PipelineLogger(
        module=module,
        trace_id=trace_id,
        document_id=document_id,
        output_dir=output_dir,
        level=level,
    )
