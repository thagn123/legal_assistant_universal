"""
Pipeline stage re-export shim.

All stage implementations have been split into focused sub-modules:
  profiler.py       — stages 1 & 2 (input loading, document profiling)
  extractor.py      — stage 3 (extraction) + shared _read_doc_text
  structurer.py     — stage 4 (canonical structuring)
  cleaner.py        — stage 5 (cleaning & validation)
  chunker.py        — stage 6 (chunking)
  graph_builder.py  — stage 7 (graph building)
  retrieval_stage.py — stage 8 (retrieval smoke test)

This file re-exports the public stage functions so that any existing
import of `from src.pipeline.stages import stage_*` continues to work.
"""

from src.pipeline.profiler import (
    stage_input_loading,
    stage_document_profiling,
)
from src.pipeline.extractor import stage_extraction
from src.pipeline.structurer import stage_canonical_structuring
from src.pipeline.cleaner import stage_cleaning_validation
from src.pipeline.chunker import stage_chunking
from src.pipeline.graph_builder import stage_graph_building
from src.pipeline.retrieval_stage import stage_retrieval_smoke_test

__all__ = [
    "stage_input_loading",
    "stage_document_profiling",
    "stage_extraction",
    "stage_canonical_structuring",
    "stage_cleaning_validation",
    "stage_chunking",
    "stage_graph_building",
    "stage_retrieval_smoke_test",
]
