"""
Pipeline configuration dataclass.

Loaded from environment, CLI args, or a config file.
All thresholds reference their meaning in the docs — change here, not in pipeline stages.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Threshold constants (named so stages can reference them symbolically)
# ---------------------------------------------------------------------------

# text-layer coverage fraction above which local extraction is preferred
STRONG_TEXT_LAYER_THRESHOLD: float = 0.80

# text-layer coverage fraction below which OCR is mandatory
WEAK_TEXT_LAYER_THRESHOLD: float = 0.20

# page count / estimated token count above which long-document policy applies
LONG_DOCUMENT_PAGE_THRESHOLD: int = 30
LONG_DOCUMENT_TOKEN_THRESHOLD: int = 20_000

# table topology confidence: below this, deterministic parser is insufficient
TABLE_TOPOLOGY_THRESHOLD: float = 0.70

# OCR confidence: below this, output is considered unreliable for authority use
OCR_CONFIDENCE_THRESHOLD: float = 0.75

# minimum confidence for an extracted block to count as authoritative
EXTRACTION_CONFIDENCE_THRESHOLD: float = 0.65

# minimum confidence for a graph edge to be emitted
GRAPH_EDGE_CONFIDENCE_THRESHOLD: float = 0.60

# minimum confidence for a chunk to be eligible for authoritative answering
CHUNK_AUTHORITY_THRESHOLD: float = 0.65

# processing version used for provenance lineage
PROCESSING_VERSION: str = "0.1.0"

# canonical schema version
SCHEMA_VERSION: str = "1.0"


@dataclass
class PipelineConfig:
    """
    Central configuration object for the Legal Multimodal GraphRAG pipeline.

    Passed by the orchestrator into every stage; stages read from it but never mutate it.
    """

    # ------------------------------------------------------------------
    # I/O paths
    # ------------------------------------------------------------------
    input_path: Path = field(default_factory=lambda: Path("./samples"))
    output_path: Path = field(default_factory=lambda: Path("./reports"))

    # ------------------------------------------------------------------
    # Document type override
    # If set, skip profiling heuristics and treat all docs as this family.
    # Values: "statute", "contract", "regulation", "judgment", "form", "annex", or ""
    # ------------------------------------------------------------------
    document_type_override: str = ""

    # ------------------------------------------------------------------
    # Feature toggles
    # ------------------------------------------------------------------
    enable_ocr: bool = True
    enable_ai_repair: bool = False        # AI-assisted OCR / table repair
    enable_graph_building: bool = True
    enable_retrieval_smoke_test: bool = True
    strict_accuracy_mode: bool = False    # Forces AI verification on tables/images
    parser_noise_cleanup: bool = True

    # ------------------------------------------------------------------
    # Thresholds (exposed so callers can override per-run)
    # ------------------------------------------------------------------
    strong_text_layer_threshold: float = STRONG_TEXT_LAYER_THRESHOLD
    weak_text_layer_threshold: float = WEAK_TEXT_LAYER_THRESHOLD
    long_document_page_threshold: int = LONG_DOCUMENT_PAGE_THRESHOLD
    long_document_token_threshold: int = LONG_DOCUMENT_TOKEN_THRESHOLD
    table_topology_threshold: float = TABLE_TOPOLOGY_THRESHOLD
    ocr_confidence_threshold: float = OCR_CONFIDENCE_THRESHOLD
    extraction_confidence_threshold: float = EXTRACTION_CONFIDENCE_THRESHOLD
    graph_edge_confidence_threshold: float = GRAPH_EDGE_CONFIDENCE_THRESHOLD
    chunk_authority_threshold: float = CHUNK_AUTHORITY_THRESHOLD

    # ------------------------------------------------------------------
    # Processing metadata
    # ------------------------------------------------------------------
    processing_version: str = PROCESSING_VERSION
    schema_version: str = SCHEMA_VERSION

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_level: str = "INFO"   # DEBUG | INFO | WARNING | ERROR
    log_to_file: bool = True

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    # Sample queries for retrieval smoke test (populated at runtime or left empty)
    smoke_test_queries: list = field(default_factory=list)

    def ensure_output_dir(self) -> None:
        self.output_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Build a config from environment variables (useful for container deployments)."""
        return cls(
            input_path=Path(os.environ.get("PIPELINE_INPUT", "./samples")),
            output_path=Path(os.environ.get("PIPELINE_OUTPUT", "./reports")),
            enable_ocr=os.environ.get("ENABLE_OCR", "true").lower() == "true",
            enable_ai_repair=os.environ.get("ENABLE_AI_REPAIR", "false").lower() == "true",
            enable_graph_building=os.environ.get("ENABLE_GRAPH", "true").lower() == "true",
            enable_retrieval_smoke_test=os.environ.get("ENABLE_SMOKE_TEST", "true").lower() == "true",
            strict_accuracy_mode=os.environ.get("STRICT_MODE", "false").lower() == "true",
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )
