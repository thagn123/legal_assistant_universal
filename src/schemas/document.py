"""
Canonical document schema.

Every field name, type, and description matches the docs/schemas/document-schema.md contract.
Downstream modules (chunking, graph, retrieval) must not mutate these objects.

Uses Pydantic v2 for validation. Falls back to dataclasses if Pydantic is not installed,
but Pydantic is strongly recommended.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field
    _USE_PYDANTIC = True
except ImportError:
    from src.utils.compat import BaseModel  # type: ignore
    from dataclasses import field as Field  # type: ignore
    _USE_PYDANTIC = False


# ---------------------------------------------------------------------------
# Shared supporting types
# ---------------------------------------------------------------------------


class SourceOffsets(BaseModel):
    """Source span anchors that link derived data back to the raw extraction stream."""

    extraction_stream_id: str
    page_id: str
    region_id: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    bbox: Optional[Dict[str, float]] = None   # {x0, y0, x1, y1}
    line_refs: List[str] = []
    cell_ref: Optional[str] = None


class Confidence(BaseModel):
    """Bounded confidence scores for any canonical object."""

    overall: float = 1.0                # 0.0 – 1.0
    extraction: Optional[float] = None
    structure: Optional[float] = None
    ocr: Optional[float] = None
    topology: Optional[float] = None    # table cell topology
    linkage: Optional[float] = None     # citation / entity link
    degraded: bool = False
    reasons: List[str] = []             # reason codes for low confidence


class Traceability(BaseModel):
    """Provenance and processing lineage for any canonical object."""

    trace_id: str
    source_hash: str
    extractor: str
    extractor_version: str
    repair_methods: List[str] = []
    derived_from_refs: List[str] = []
    processing_version: str = "0.1.0"
    created_at: str = ""                # ISO-8601 timestamp


class RegionRef(BaseModel):
    """Reference to a typed page region."""

    region_id: str
    type: str                           # text | table | image | mixed
    bbox: Dict[str, float] = {}
    reading_order_index: int = 0
    confidence: float = 1.0


class DocumentMetadata(BaseModel):
    """Rich legal metadata extracted or supplied for a document."""

    title: str = ""
    document_family: str = ""           # statute | contract | regulation | judgment | annex | form
    document_type: str = ""
    jurisdiction: str = ""
    subjurisdiction: Optional[str] = None
    languages: List[str] = []
    version_label: Optional[str] = None
    issued_date: Optional[str] = None
    effective_date: Optional[str] = None
    authority: Optional[str] = None
    source_uri: Optional[str] = None
    tags: List[str] = []


class LanguageDetection(BaseModel):
    """
    Formal language detection result attached to a document or block.

    Carries the detected language code, jurisdiction best-guess, and
    confidence so that downstream retrieval can gate on quality.
    """

    language: str = "unknown"           # ISO 639-1: "vi", "en", "mixed", "unknown"
    confidence: float = 0.0             # 0.0–1.0
    jurisdiction: Optional[str] = None  # ISO 3166-1 alpha-2: "VN", "US", "GB", "EU", …
    script: str = "unknown"             # "latin_diacritics" | "ascii" | "mixed"
    signals: List[str] = []             # signal names that fired (debug)


class DocumentProfile(BaseModel):
    """
    Profile output from the Document Profiler stage.
    Drives routing decisions in the Complexity Router.
    """

    file_type: str = ""                     # pdf | docx | html | image | unknown
    text_layer_coverage: float = 0.0        # fraction 0.0–1.0
    scan_quality_score: float = 1.0
    layout_complexity_score: float = 0.0   # 0 = simple, 1 = very complex
    table_density: float = 0.0             # fraction of page area occupied by tables
    image_density: float = 0.0
    languages: List[str] = []
    page_count: int = 0
    estimated_token_count: int = 0
    extraction_strategy: str = ""           # simple_local | long_local | hybrid_region_precision | scan_recovery
    is_long_document: bool = False
    is_scan_heavy: bool = False
    has_tables: bool = False
    has_images: bool = False
    language_detection: Optional[LanguageDetection] = None  # formal detection result


# ---------------------------------------------------------------------------
# Core evidence objects
# ---------------------------------------------------------------------------


class Block(BaseModel):
    """
    Smallest canonical extracted content unit.
    Preserves raw text, cleaned text, source offsets, and hierarchy reference.
    """

    block_id: str
    page_id: str
    region_id: str
    block_type: str                         # heading | paragraph | list_item | footnote | citation | caption | table_ref
    order_index: int                        # global document order
    raw_text: str
    clean_text: str = ""
    html_fragment: Optional[str] = None
    markdown_fragment: Optional[str] = None
    language: Optional[str] = None
    parent_structure_id: Optional[str] = None   # section_id, article_id, or clause_id
    citations: List[str] = []
    source_offsets: List[SourceOffsets] = []
    bbox_refs: List[Dict[str, Any]] = []
    confidence: Confidence = Confidence()
    traceability: Optional[Traceability] = None


class TableCell(BaseModel):
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    text: str = ""
    raw_text: str = ""
    is_header: bool = False


class Table(BaseModel):
    """
    First-class table evidence object.
    Topology (headers, rows, cells, merged ranges) must be preserved intact.
    """

    table_id: str
    title: Optional[str] = None
    page_refs: List[str] = []
    bbox_refs: List[Dict[str, Any]] = []
    related_structure_id: Optional[str] = None
    row_count: int = 0
    column_count: int = 0
    headers: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    cells: List[TableCell] = []
    merged_ranges: List[Dict[str, Any]] = []
    continuation: Optional[Dict[str, Any]] = None   # multi-page table metadata
    html: Optional[str] = None
    markdown: Optional[str] = None
    projection_text: str = ""               # retrieval-oriented text projection
    confidence: Confidence = Confidence()
    traceability: Optional[Traceability] = None


class Image(BaseModel):
    """
    First-class image evidence object.
    OCR text, evidence status, and visual class are preserved.
    """

    image_id: str
    page_id: str
    bbox: Dict[str, float] = {}
    image_class: str = ""                   # scan_text | seal | stamp | signature | diagram | photo | mixed
    raw_ocr_text: str = ""
    clean_ocr_text: str = ""
    text_spans: List[Dict[str, Any]] = []
    ocr_confidence: Optional[float] = None
    evidence_status: str = "visual_only"    # textual | visual_only | mixed | unreadable
    related_structure_ids: List[str] = []
    confidence: Confidence = Confidence()
    traceability: Optional[Traceability] = None


# ---------------------------------------------------------------------------
# Structural hierarchy objects
# ---------------------------------------------------------------------------


class Section(BaseModel):
    """A chapter, part, title, schedule, or annex-level structural unit."""

    section_id: str
    section_kind: str = ""              # title | part | chapter | section | schedule | annex
    label: str = ""
    number: Optional[str] = None
    title: Optional[str] = None
    parent_section_id: Optional[str] = None
    child_section_ids: List[str] = []
    article_ids: List[str] = []
    block_ids: List[str] = []
    page_refs: List[str] = []
    source_offsets: List[SourceOffsets] = []
    confidence: Confidence = Confidence()
    traceability: Optional[Traceability] = None


class Article(BaseModel):
    """An article, regulation item, or equivalent operative legal unit."""

    article_id: str
    label: str = ""
    number: Optional[str] = None
    title: Optional[str] = None
    parent_section_id: Optional[str] = None
    clause_ids: List[str] = []
    block_ids: List[str] = []
    table_ids: List[str] = []
    image_ids: List[str] = []
    citations: List[str] = []
    page_refs: List[str] = []
    source_offsets: List[SourceOffsets] = []
    confidence: Confidence = Confidence()
    traceability: Optional[Traceability] = None


class Clause(BaseModel):
    """
    A subordinate legal unit: paragraph, subclause, item, point, definition, or exception.
    Clause number must never be stripped during chunking.
    """

    clause_id: str
    label: str = ""
    number: Optional[str] = None
    clause_kind: str = ""               # paragraph | subclause | item | point | definition | exception
    title: Optional[str] = None
    parent_article_id: Optional[str] = None
    parent_clause_id: Optional[str] = None
    child_clause_ids: List[str] = []
    block_ids: List[str] = []
    table_ids: List[str] = []
    image_ids: List[str] = []
    citations: List[str] = []
    defined_terms: List[str] = []
    page_refs: List[str] = []
    source_offsets: List[SourceOffsets] = []
    confidence: Confidence = Confidence()
    traceability: Optional[Traceability] = None


# ---------------------------------------------------------------------------
# Rendered outputs and validation summary
# ---------------------------------------------------------------------------


class RenderedOutputs(BaseModel):
    html: Optional[str] = None
    markdown: Optional[str] = None
    generation_status: str = "unavailable"   # complete | partial | unavailable


class ValidationSummary(BaseModel):
    coverage_score: float = 0.0
    unresolved_issues: List[str] = []
    warnings: List[str] = []
    validated_at: str = ""


# ---------------------------------------------------------------------------
# Root canonical document object
# ---------------------------------------------------------------------------


class CanonicalDocument(BaseModel):
    """
    Root object of the canonical document schema.
    This is the handoff contract between ingestion and retrieval / graph modules.
    Downstream modules read from this; they must never mutate source fields.
    """

    document_id: str
    schema_version: str = "1.0"
    source_filename: str = ""
    mime_type: str = ""
    file_type: str = ""                 # pdf | docx | image | html

    metadata: DocumentMetadata = DocumentMetadata()
    profile: DocumentProfile = DocumentProfile()

    # Physical structure
    pages: List[Dict[str, Any]] = []    # PageRef objects (lightweight for schema portability)
    blocks: List[Block] = []

    # Structural hierarchy (may be empty if hierarchy could not be detected)
    sections: List[Section] = []
    articles: List[Article] = []
    clauses: List[Clause] = []

    # Evidence objects
    tables: List[Table] = []
    images: List[Image] = []

    rendered_outputs: RenderedOutputs = RenderedOutputs()
    validation: ValidationSummary = ValidationSummary()
    confidence: Confidence = Confidence()
    traceability: Optional[Traceability] = None

    # ---------------------------------------------------------------------------
    # Convenience helpers (never mutate core data)
    # ---------------------------------------------------------------------------

    def block_count(self) -> int:
        return len(self.blocks)

    def table_count(self) -> int:
        return len(self.tables)

    def image_count(self) -> int:
        return len(self.images)

    def has_structure(self) -> bool:
        return bool(self.sections or self.articles or self.clauses)

    def degraded_block_count(self) -> int:
        return sum(1 for b in self.blocks if b.confidence.degraded)

    def low_confidence_blocks(self, threshold: float = 0.65) -> List[Block]:
        return [b for b in self.blocks if b.confidence.overall < threshold]
