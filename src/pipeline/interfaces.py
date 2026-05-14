"""
Stage interface contracts.

Every pipeline stage is a callable that accepts a StageContext and returns a StageOutput.
This makes stages independently testable, swappable, and observable.

The interface is intentionally minimal: stages only need context + structured output.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from src.config import PipelineConfig
from src.schemas.evaluation import StageResult, STATUS_PASS, STATUS_FAIL, STATUS_WARNING
from src.utils.logging import PipelineLogger


@dataclass
class StageContext:
    """
    Shared input context passed into every pipeline stage.
    Stages read from context; they never mutate the config or logger.
    """

    trace_id: str
    document_id: str
    source_path: Path
    config: PipelineConfig
    logger: PipelineLogger

    # Shared state built up by prior stages
    # Each stage adds its output here so downstream stages can consume it.
    state: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def put(self, key: str, value: Any) -> None:
        self.state[key] = value


@dataclass
class StageOutput:
    """
    Return value from any pipeline stage.
    Wraps the stage result with timing and any produced artifacts.
    """

    stage_name: str
    status: str = STATUS_PASS
    summary: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    output_summary: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0

    def to_stage_result(self) -> StageResult:
        return StageResult(
            stage=self.stage_name,
            status=self.status,
            duration_seconds=self.duration_seconds,
            summary=self.summary,
            metrics=self.metrics,
            warnings=self.warnings,
            errors=self.errors,
            output_summary=self.output_summary,
        )


class PipelineStage(Protocol):
    """
    Protocol that all pipeline stages must satisfy.
    Stages are pure functions: (context) -> StageOutput.
    """

    name: str

    def run(self, ctx: StageContext) -> StageOutput:
        ...


def timed_run(stage_name: str, fn: Any, ctx: StageContext) -> StageOutput:
    """
    Run a stage function with timing and top-level error catching.
    Any uncaught exception becomes a STATUS_FAIL output (not a crash).
    """
    ctx.logger.stage_start(stage_name)
    t0 = time.perf_counter()
    try:
        output: StageOutput = fn(ctx)
        output.duration_seconds = time.perf_counter() - t0
        ctx.logger.stage_end(stage_name, status=output.status, duration_seconds=output.duration_seconds)
        return output
    except Exception as exc:
        duration = time.perf_counter() - t0
        ctx.logger.error(
            f"Stage {stage_name} raised an unhandled exception",
            stage=stage_name,
            error=str(exc),
        )
        return StageOutput(
            stage_name=stage_name,
            status=STATUS_FAIL,
            summary=f"Unhandled exception in stage {stage_name}",
            errors=[str(exc)],
            duration_seconds=duration,
        )
