"""
RetrievalFusionEngine — Stage 3 of the Legal Intelligence Pipeline.

Combines four independent retrieval signals into a single ranked candidate list:

  Signal 1 — Vector Search  (MongoDB $vectorSearch, cosine similarity, weight 0.45)
  Signal 2 — BM25 Keyword   (TF-based keyword density, weight 0.20)
  Signal 3 — Graph Expanded (law-reference keyword boost, weight 0.25)
  Signal 4 — Behavior Boost (collaborative filter from interaction history, weight 0.10)

Each signal is independently normalized to [0, 1] via min-max before fusion.
All candidates are deduplicated by chunk_id. Final score = weighted sum.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.engine.query_planner import QueryPlan
from src.mongodb.mongo_storage import VectorStorage
from src.observability.tracer import get_tracer
from src.pipeline.embedding_stage import embed_text

logger = logging.getLogger(__name__)

# Default fusion weights (must sum to 1.0)
_DEFAULT_WEIGHTS: Dict[str, float] = {
    "vector":   0.45,
    "bm25":     0.20,
    "graph":    0.25,
    "behavior": 0.10,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FusedResult:
    item_id: str             # chunk_id (primary key for deduplication)
    item_type: str           # "law_chunk" | "legal_case"
    content: str             # truncated to 500 chars
    law_type: str
    law_reference: str
    raw_data: Dict[str, Any] = field(default_factory=dict)

    # Per-signal scores (all in [0, 1])
    vector_score: float = 0.0
    bm25_score: float = 0.0
    graph_score: float = 0.0
    behavior_score: float = 0.0

    # Fused
    fusion_score: float = 0.0
    sources: List[str] = field(default_factory=list)   # which signals contributed
    fusion_reason: str = ""                             # e.g. "vector:0.82, graph:0.71"


@dataclass
class FusedResultSet:
    plan_id: str
    results: List[FusedResult]
    total_raw_hits: int       # pre-dedup total
    vector_hits: int
    bm25_hits: int
    graph_hits: int
    behavior_hits: int
    fusion_weights: Dict[str, float]
    fusion_duration_ms: float


# ---------------------------------------------------------------------------
# RetrievalFusionEngine
# ---------------------------------------------------------------------------


class RetrievalFusionEngine:
    """
    Hybrid retrieval fusion for legal content.

    Usage:
        fusion = RetrievalFusionEngine(vector_storage)
        result_set = fusion.fuse(plan, user_id="u_123", limit=15)
    """

    def __init__(
        self,
        vector_storage: VectorStorage,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self._vs = vector_storage
        self._weights = weights or dict(_DEFAULT_WEIGHTS)
        self._tracer = get_tracer()

    def fuse(
        self,
        plan: QueryPlan,
        user_id: str,
        limit: int = 15,
        trace_id: str = "",
    ) -> FusedResultSet:
        if self._vs is None:
            logger.warning("RetrievalFusionEngine.fuse: no vector storage, returning empty set")
            return FusedResultSet(
                plan_id=plan.query_variants[0][:60] if plan.query_variants else "",
                results=[],
                total_raw_hits=0, vector_hits=0, bm25_hits=0,
                graph_hits=0, behavior_hits=0,
                fusion_weights=dict(self._weights),
                fusion_duration_ms=0.0,
            )
        t0 = time.perf_counter()
        candidates: Dict[str, FusedResult] = {}

        # ── Signal 1: Vector search ──────────────────────────────────────────
        vector_hits = 0
        if "vector" in plan.retrieval_strategy:
            t_v = time.perf_counter()
            for variant in plan.query_variants[:2]:
                embedding = embed_text(variant)
                if not embedding:
                    continue
                chunks = self._vs.vector_search_chunks(
                    query_vector=embedding,
                    law_type=plan.detected_domain if plan.detected_domain != "general" else None,
                    limit=limit * 2,
                )
                for c in chunks:
                    cid = c.get("chunk_id", "")
                    if not cid or cid.startswith("__"):
                        continue
                    vscore = float(c.get("vector_score", 0))
                    # QA Risk Fix: Loại bỏ các kết quả nhiễu thấp hơn ngưỡng
                    if vscore < 0.55:
                        continue
                    if cid not in candidates:
                        candidates[cid] = _make_result(c, "law_chunk")
                        vector_hits += 1
                    # Take max vector score across variants
                    if vscore > candidates[cid].vector_score:
                        candidates[cid].vector_score = vscore
                    if "vector" not in candidates[cid].sources:
                        candidates[cid].sources.append("vector")
            self._tracer.log_retrieval(
                trace_id, "vector", vector_hits,
                max((c.vector_score for c in candidates.values()), default=0),
                plan.query_variants[0][:60],
                (time.perf_counter() - t_v) * 1000,
            )

        # ── Signal 2: BM25 keyword retrieval ────────────────────────────────
        bm25_hits = 0
        if "bm25" in plan.retrieval_strategy:
            t_b = time.perf_counter()
            keywords = _build_keywords(plan.original_query, plan.extracted_entities)
            if keywords:
                kw_chunks = self._vs.keyword_search_chunks(keywords, limit=limit)
                for c in kw_chunks:
                    cid = c.get("chunk_id", "")
                    if not cid:
                        continue
                    bscore = _bm25_score(plan.original_query, c.get("content", ""), keywords)
                    if cid not in candidates:
                        candidates[cid] = _make_result(c, "law_chunk")
                        bm25_hits += 1
                    candidates[cid].bm25_score = max(candidates[cid].bm25_score, bscore)
                    if "bm25" not in candidates[cid].sources:
                        candidates[cid].sources.append("bm25")
            self._tracer.log_retrieval(
                trace_id, "bm25", bm25_hits,
                max((c.bm25_score for c in candidates.values()), default=0),
                " ".join(keywords[:4]),
                (time.perf_counter() - t_b) * 1000,
            )

        # ── Signal 3: Graph-expanded keyword search ──────────────────────────
        graph_hits = 0
        if "graph" in plan.retrieval_strategy:
            t_g = time.perf_counter()
            law_refs = plan.extracted_entities.get("laws", [])[:3]
            if law_refs:
                graph_chunks = self._vs.keyword_search_chunks(law_refs, limit=limit)
                for c in graph_chunks:
                    cid = c.get("chunk_id", "")
                    if not cid:
                        continue
                    gscore = 0.75  # high fixed score for exact law-reference match
                    if cid not in candidates:
                        candidates[cid] = _make_result(c, "law_chunk")
                        graph_hits += 1
                    candidates[cid].graph_score = max(candidates[cid].graph_score, gscore)
                    if "graph" not in candidates[cid].sources:
                        candidates[cid].sources.append("graph")
            self._tracer.log_retrieval(
                trace_id, "graph", graph_hits,
                max((c.graph_score for c in candidates.values()), default=0),
                " ".join(law_refs[:2]),
                (time.perf_counter() - t_g) * 1000,
            )

        # ── Signal 4: Behavior boost ─────────────────────────────────────────
        behavior_hits = 0
        if "behavior" in plan.retrieval_strategy and candidates:
            t_bh = time.perf_counter()
            user_law_types = self._vs.get_user_law_types(user_id)
            domain_rank = (
                user_law_types.index(plan.detected_domain)
                if plan.detected_domain in user_law_types else -1
            )
            if domain_rank >= 0:
                boost = round(max(0.1, 1.0 - domain_rank * 0.2), 3)
                for cid, cand in candidates.items():
                    if cand.law_type == plan.detected_domain:
                        if cand.behavior_score == 0.0:
                            cand.behavior_score = boost
                            behavior_hits += 1
                            if "behavior" not in cand.sources:
                                cand.sources.append("behavior")
            self._tracer.log_retrieval(
                trace_id, "behavior", behavior_hits,
                max((c.behavior_score for c in candidates.values()), default=0),
                plan.detected_domain,
                (time.perf_counter() - t_bh) * 1000,
            )

        # ── Normalize scores per signal ──────────────────────────────────────
        _normalize_signal(candidates, "vector_score")
        _normalize_signal(candidates, "bm25_score")
        _normalize_signal(candidates, "graph_score")
        _normalize_signal(candidates, "behavior_score")

        # ── Compute fusion scores ────────────────────────────────────────────
        w = self._weights
        for cand in candidates.values():
            cand.fusion_score = round(
                w["vector"]   * cand.vector_score   +
                w["bm25"]     * cand.bm25_score     +
                w["graph"]    * cand.graph_score     +
                w["behavior"] * cand.behavior_score,
                4,
            )
            cand.fusion_reason = (
                f"vector:{cand.vector_score:.2f} "
                f"bm25:{cand.bm25_score:.2f} "
                f"graph:{cand.graph_score:.2f} "
                f"behavior:{cand.behavior_score:.2f}"
            )

        # ── Sort and trim ────────────────────────────────────────────────────
        ranked = sorted(candidates.values(), key=lambda c: c.fusion_score, reverse=True)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)

        return FusedResultSet(
            plan_id=plan.plan_id,
            results=ranked[:limit],
            total_raw_hits=len(candidates),
            vector_hits=vector_hits,
            bm25_hits=bm25_hits,
            graph_hits=graph_hits,
            behavior_hits=behavior_hits,
            fusion_weights=dict(self._weights),
            fusion_duration_ms=duration_ms,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_law_reference(chunk: Dict[str, Any]) -> str:
    """Extract a human-readable law reference from chunk data."""
    ref = chunk.get("law_reference") or chunk.get("canonical_ref") or ""
    if ref:
        return ref
    # Try canonical_refs array (join non-internal refs)
    canonical = chunk.get("canonical_refs") or []
    meaningful = [r for r in canonical if not r.startswith(("chapter_", "article_", "section_"))]
    if meaningful:
        return " | ".join(meaningful[:2])
    # Fall back: extract "Điều NNN" from content
    content = chunk.get("content", "")
    import re
    m = re.search(r"Điều\s+(\d+)[.\s]", content)
    if m:
        return f"Điều {m.group(1)}"
    return ""


def _make_result(chunk: Dict[str, Any], item_type: str) -> FusedResult:
    return FusedResult(
        item_id=chunk.get("chunk_id", ""),
        item_type=item_type,
        content=chunk.get("content", "")[:500],
        law_type=chunk.get("law_type", "general"),
        law_reference=_extract_law_reference(chunk),
        raw_data=chunk,
    )


def _build_keywords(query: str, entities: Dict[str, List[str]]) -> List[str]:
    """Extract BM25 search keywords: meaningful query words + law references."""
    # Words longer than 3 chars from query
    words = [w for w in query.split() if len(w) > 3][:8]
    # Add law references
    words += entities.get("laws", [])[:2]
    # Deduplicate preserving order
    return list(dict.fromkeys(words))


def _bm25_score(query: str, content: str, keywords: List[str]) -> float:
    """
    Approximate BM25 using term frequency only (no corpus IDF needed).
    Score = (sum of TF per keyword) normalized by keyword count.
    """
    if not content or not keywords:
        return 0.0
    content_lower = content.lower()
    words = content_lower.split()
    doc_len = max(len(words), 1)

    total_tf = 0.0
    for kw in keywords:
        kw_lower = kw.lower()
        count = content_lower.count(kw_lower)
        tf = count / doc_len
        total_tf += tf

    score = total_tf / max(len(keywords), 1)
    return round(min(1.0, score * 20), 4)   # scale up (raw TF is tiny)


def _normalize_signal(candidates: Dict[str, FusedResult], attr: str) -> None:
    """Min-max normalize a score attribute across all candidates in-place."""
    values = [getattr(c, attr) for c in candidates.values()]
    min_v, max_v = min(values, default=0), max(values, default=0)
    if max_v == min_v:
        return  # all equal — no normalization needed
    for cand in candidates.values():
        raw = getattr(cand, attr)
        setattr(cand, attr, round((raw - min_v) / (max_v - min_v), 4))
