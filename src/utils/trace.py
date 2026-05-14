"""
Trace utilities.

Generates and propagates trace_id and document_id for end-to-end observability.
Every pipeline stage and derived artifact must carry the same trace_id.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def new_trace_id() -> str:
    """Generate a new unique trace ID for a pipeline run."""
    return str(uuid.uuid4())


def new_document_id(source_filename: str, source_hash: str) -> str:
    """
    Derive a stable document ID from filename + source hash.
    Same file content always produces the same document_id.
    """
    combined = f"{source_filename}::{source_hash}"
    return "doc_" + hashlib.sha256(combined.encode()).hexdigest()[:16]


def compute_source_hash(file_path: Path) -> str:
    """Compute a SHA-256 hash of the source file for provenance tracking."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def make_block_id(document_id: str, page_index: int, region_index: int, block_index: int) -> str:
    return f"{document_id}__p{page_index:04d}_r{region_index:03d}_b{block_index:04d}"


def make_page_id(document_id: str, page_index: int) -> str:
    return f"{document_id}__page_{page_index:04d}"


def make_region_id(page_id: str, region_index: int, region_type: str) -> str:
    return f"{page_id}__region_{region_index:03d}_{region_type}"


def make_table_id(document_id: str, page_index: int, table_index: int) -> str:
    return f"{document_id}__p{page_index:04d}_tbl{table_index:03d}"


def make_image_id(document_id: str, page_index: int, image_index: int) -> str:
    return f"{document_id}__p{page_index:04d}_img{image_index:03d}"


def make_section_id(document_id: str, section_index: int) -> str:
    return f"{document_id}__sec{section_index:04d}"


def make_article_id(document_id: str, article_index: int) -> str:
    return f"{document_id}__art{article_index:04d}"


def make_clause_id(document_id: str, clause_index: int) -> str:
    return f"{document_id}__cls{clause_index:04d}"


def make_chunk_id(document_id: str, chunk_index: int) -> str:
    return f"{document_id}__chunk{chunk_index:05d}"


def make_node_id(document_id: str, node_type: str, source_ref: str) -> str:
    key = f"{document_id}::{node_type}::{source_ref}"
    return "node_" + hashlib.sha256(key.encode()).hexdigest()[:16]


def make_edge_id(from_id: str, edge_type: str, to_id: str) -> str:
    key = f"{from_id}::{edge_type}::{to_id}"
    return "edge_" + hashlib.sha256(key.encode()).hexdigest()[:16]
