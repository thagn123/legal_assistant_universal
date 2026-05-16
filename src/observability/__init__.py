"""Observability — structured tracing and logging for the Legal Intelligence Pipeline."""
from src.observability.tracer import ExecutionTracer, get_tracer

__all__ = ["ExecutionTracer", "get_tracer"]
