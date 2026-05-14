"""
CLI entry point for the Legal Multimodal GraphRAG pipeline evaluator.

Usage:
    python -m src.run_pipeline_eval --input ./samples --output ./reports
    python -m src.run_pipeline_eval --input ./samples --no-graph --no-ocr
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config import PipelineConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_pipeline_eval",
        description=(
            "Legal Multimodal GraphRAG — end-to-end pipeline evaluation runner.\n\n"
            "Processes documents from --input, runs all pipeline stages, and writes\n"
            "a JSON + Markdown evaluation report to --output."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("./samples"),
        metavar="DIR_OR_FILE",
        help="Input folder or single file to process. Supports PDF, DOCX, HTML, and images.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./reports"),
        metavar="DIR",
        help="Output directory for evaluation reports and intermediate artifacts.",
    )
    parser.add_argument(
        "--document-type",
        type=str,
        default="",
        metavar="TYPE",
        help=(
            "Override document family for all inputs. "
            "Values: statute | contract | regulation | judgment | form | annex"
        ),
    )

    # Feature toggles
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR processing.")
    parser.add_argument(
        "--enable-ai-repair",
        action="store_true",
        help="Enable AI-assisted repair for low-confidence table and OCR regions.",
    )
    parser.add_argument("--no-graph", action="store_true", help="Skip graph building stage.")
    parser.add_argument(
        "--no-smoke-test", action="store_true", help="Skip retrieval smoke test stage."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict accuracy mode: AI verification for all tables and images.",
    )
    parser.add_argument(
        "--no-noise-cleanup",
        action="store_true",
        help="Disable parser-noise cleanup (duplicated lines, OCR garbage).",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log verbosity level.",
    )
    parser.add_argument(
        "--no-log-file",
        action="store_true",
        help="Print logs to stdout only; do not write a log file.",
    )

    return parser


def config_from_args(args: argparse.Namespace) -> PipelineConfig:
    """Convert parsed CLI args into a PipelineConfig."""
    return PipelineConfig(
        input_path=args.input,
        output_path=args.output,
        document_type_override=args.document_type,
        enable_ocr=not args.no_ocr,
        enable_ai_repair=args.enable_ai_repair,
        enable_graph_building=not args.no_graph,
        enable_retrieval_smoke_test=not args.no_smoke_test,
        strict_accuracy_mode=args.strict,
        parser_noise_cleanup=not args.no_noise_cleanup,
        log_level=args.log_level,
        log_to_file=not args.no_log_file,
    )


def parse_config() -> PipelineConfig:
    """Parse CLI args and return a ready PipelineConfig."""
    parser = build_parser()
    args = parser.parse_args()
    return config_from_args(args)
