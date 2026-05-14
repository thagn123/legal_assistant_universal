"""
Multilingual keyword retrieval engine over a ChunkSet.

This engine supports cross-language retrieval: a query in English will match
chunks from a Vietnamese document (and vice versa) by going through canonical
reference IDs and expanded alias sets.

Embedding-based retrieval (BGE-M3, multilingual-e5, jina) is supported via
a pluggable embedding backend interface. When no embedding backend is
configured, the engine falls back to keyword-only matching (always available,
no external dependencies).

Retrieval pipeline (in order):
  1. Parse query → canonical ref ID (if it is a structure reference)
  2. Search chunks by canonical_refs match (cross-language, exact)
  3. Search chunks by expanded keyword aliases (cross-language, keyword)
  4. Search chunks by raw keyword match in content (monolingual fallback)
  5. If embedding backend present: semantic similarity search
  6. Return ranked results

Design rules:
  - Never returns invented content; only chunks with real content.
  - Debug logging records every retrieval decision.
  - Missing/empty results are surfaced as empty list, never faked.
  - All results carry a retrieval_score and a list of matched_signals.

Usage:
    from src.retrieval.retrieval_engine import RetrievalEngine, RetrievalResult
    from src.schemas.chunk import ChunkSet

    engine = RetrievalEngine(chunk_set, debug=True)
    results = engine.search("Article 1")
    results = engine.search("Điều 1")          # finds same chunks as above
    results = engine.search("payment terms")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.schemas.chunk import Chunk, ChunkSet
from src.retrieval.query_normalizer import normalize_query, query_to_search_terms, extract_refs
from src.retrieval.legal_aliases import expand_query_terms, canonical_term


# ---------------------------------------------------------------------------
# Result objects
# ---------------------------------------------------------------------------


@dataclass
class RetrievalResult:
    """
    A single chunk returned by the retrieval engine.

    Attributes:
        chunk:           The matched Chunk object.
        retrieval_score: Composite score 0.0–1.0.
        matched_signals: Human-readable list of signals that contributed to the match.
        match_type:      How the chunk was found: "canonical_ref" | "alias_keyword"
                         | "keyword" | "semantic"
    """
    chunk: Chunk
    retrieval_score: float
    matched_signals: List[str] = field(default_factory=list)
    match_type: str = "keyword"


@dataclass
class RetrievalDebugLog:
    """Debug record for a single retrieval call."""
    query: str
    normalized_query: str
    canonical_ref: Optional[str]
    search_terms: List[str]
    expanded_aliases: List[str]
    canonical_hits: int
    alias_hits: int
    keyword_hits: int
    semantic_hits: int
    total_returned: int
    log_entries: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Embedding backend protocol
# ---------------------------------------------------------------------------


# An embedding backend is any callable that takes a string and returns a vector.
# The engine accepts an optional embedding backend at construction time.
EmbeddingBackendFn = Callable[[str], List[float]]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two equal-length vectors."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# RetrievalEngine
# ---------------------------------------------------------------------------


class RetrievalEngine:
    """
    Multilingual keyword retrieval engine over a ChunkSet.

    Args:
        chunk_set:          The ChunkSet to search over.
        debug:              If True, collect detailed retrieval logs.
        embedding_backend:  Optional callable: str → List[float].
                            If provided, semantic similarity is used as a
                            fourth retrieval pass.
        semantic_threshold: Minimum cosine similarity to include a semantic hit
                            (default 0.65).
        max_results:        Maximum chunks to return per query (default 20).
    """

    def __init__(
        self,
        chunk_set: ChunkSet,
        debug: bool = False,
        embedding_backend: Optional[EmbeddingBackendFn] = None,
        semantic_threshold: float = 0.65,
        max_results: int = 20,
    ) -> None:
        self.chunk_set = chunk_set
        self.debug = debug
        self.embedding_backend = embedding_backend
        self.semantic_threshold = semantic_threshold
        self.max_results = max_results

        # Build search indices at construction time
        self._canonical_index: Dict[str, List[Chunk]] = {}   # canonical_ref → chunks
        self._build_index()

        # Debug log for most recent search
        self.last_debug_log: Optional[RetrievalDebugLog] = None

    # ── Index construction ───────────────────────────────────────────────

    def _build_index(self) -> None:
        """Build the canonical reference index from the chunk set."""
        for chunk in self.chunk_set.chunks:
            canonical_refs = getattr(chunk, "canonical_refs", []) or []
            for ref in canonical_refs:
                if ref not in self._canonical_index:
                    self._canonical_index[ref] = []
                self._canonical_index[ref].append(chunk)

    # ── Internal search passes ───────────────────────────────────────────

    def _search_canonical(self, canonical_ref: str) -> List[Chunk]:
        """Pass 1: Exact canonical reference match (cross-language)."""
        return self._canonical_index.get(canonical_ref, [])

    def _search_aliases(self, expanded_terms: List[str]) -> List[tuple[Chunk, str]]:
        """
        Pass 2: Search chunk content for any expanded alias term.
        Returns list of (chunk, matched_term).
        """
        results: List[tuple[Chunk, str]] = []
        seen_ids: set[str] = set()
        for chunk in self.chunk_set.chunks:
            content_lower = chunk.content.lower()
            for term in expanded_terms:
                if term and term in content_lower:
                    if chunk.chunk_id not in seen_ids:
                        results.append((chunk, term))
                        seen_ids.add(chunk.chunk_id)
                    break
        return results

    def _search_keywords(self, terms: List[str]) -> List[tuple[Chunk, str]]:
        """
        Pass 3: Plain keyword search in chunk content.
        Returns list of (chunk, matched_term).
        """
        results: List[tuple[Chunk, str]] = []
        seen_ids: set[str] = set()
        for chunk in self.chunk_set.chunks:
            content_lower = chunk.content.lower()
            for term in terms:
                if term and len(term) >= 2 and term in content_lower:
                    if chunk.chunk_id not in seen_ids:
                        results.append((chunk, term))
                        seen_ids.add(chunk.chunk_id)
                    break
        return results

    def _search_semantic(
        self,
        query: str,
        already_found_ids: set[str],
    ) -> List[tuple[Chunk, float]]:
        """
        Pass 4: Semantic similarity search using embedding backend.
        Only runs if an embedding_backend is configured.
        Skips chunks already returned by earlier passes.
        """
        if not self.embedding_backend:
            return []
        try:
            query_vec = self.embedding_backend(query)
        except Exception:
            return []

        results: List[tuple[Chunk, float]] = []
        for chunk in self.chunk_set.chunks:
            if chunk.chunk_id in already_found_ids:
                continue
            try:
                chunk_vec = self.embedding_backend(chunk.content[:1000])
                sim = _cosine_similarity(query_vec, chunk_vec)
                if sim >= self.semantic_threshold:
                    results.append((chunk, sim))
            except Exception:
                continue

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    # ── Scoring ──────────────────────────────────────────────────────────

    def _score(
        self,
        chunk: Chunk,
        match_type: str,
        matched_signal: str,
        query_terms: List[str],
    ) -> float:
        """
        Compute a retrieval score for a chunk.

        Scoring factors:
        - Match type weight: canonical_ref (1.0) > alias_keyword (0.75) > keyword (0.5)
        - Chunk confidence penalty for degraded chunks
        - Term frequency: how many times query terms appear (not just whether they appear)
        - Length penalty: shorter chunks with a match score higher than giant catch-all chunks
        """
        base_scores = {
            "canonical_ref": 1.0,
            "alias_keyword": 0.75,
            "keyword": 0.5,
            "semantic": 0.6,
        }
        score = base_scores.get(match_type, 0.5)

        # Penalise degraded chunks
        if chunk.degraded:
            score *= 0.7

        # Apply chunk's own confidence
        score *= max(chunk.confidence, 0.3)

        content_lower = chunk.content.lower()
        effective_terms = [t for t in query_terms if t and len(t) >= 2]

        # Term frequency bonus: count total occurrences, not just presence.
        # Capped at 3 occurrences per term to avoid gaming by repetition.
        if effective_terms:
            tf_total = sum(
                min(content_lower.count(t), 3)
                for t in effective_terms
            )
            tf_bonus = min(tf_total / (len(effective_terms) * 3), 1.0) * 0.25
            score = min(score + tf_bonus, 1.0)

        # Length penalty: a very large chunk that matches by accident should score
        # lower than a targeted small chunk. Penalty kicks in above 500 tokens.
        token_estimate = len(chunk.content) // 4
        if token_estimate > 500:
            # Logarithmic penalty: 0 at 500 tokens, ~0.15 at 50,000 tokens
            import math
            penalty = min(math.log10(token_estimate / 500) * 0.075, 0.15)
            score = max(score - penalty, 0.0)

        return round(score, 4)

    # ── Public search API ────────────────────────────────────────────────

    def search(self, query: str) -> List[RetrievalResult]:
        """
        Search the chunk set for the given query string.

        Tries canonical ref match, alias expansion, and keyword match in order.
        Optionally adds semantic search if an embedding backend is configured.
        Results are sorted by retrieval_score descending, limited to max_results.

        Args:
            query: The user's query string (any language).

        Returns:
            List of RetrievalResult objects, sorted by score descending.
        """
        log_entries: List[str] = []

        # ── Step 1: Parse query ──────────────────────────────────────────
        normalized = normalize_query(query)
        search_terms = query_to_search_terms(query)
        log_entries.append(f"query={query!r} normalized={normalized!r} terms={search_terms}")

        # Canonical reference (if query looks like a structure reference)
        canonical_ref: Optional[str] = None
        if re.match(r"^[a-z]+_\d", normalized):
            # normalized is itself a canonical ID
            canonical_ref = normalized
        else:
            refs = extract_refs(query)
            if refs:
                canonical_ref = refs[0]

        # Expand aliases (multilingual cross-reference)
        expanded_aliases = list(expand_query_terms(search_terms))
        log_entries.append(f"canonical_ref={canonical_ref} expanded_aliases={expanded_aliases[:10]}")

        # ── Step 2: Canonical reference match ────────────────────────────
        results: List[RetrievalResult] = []
        seen_ids: set[str] = set()
        canonical_hits = 0

        if canonical_ref:
            for chunk in self._search_canonical(canonical_ref):
                if chunk.chunk_id not in seen_ids:
                    score = self._score(chunk, "canonical_ref", canonical_ref, search_terms)
                    results.append(RetrievalResult(
                        chunk=chunk,
                        retrieval_score=score,
                        matched_signals=[f"canonical_ref:{canonical_ref}"],
                        match_type="canonical_ref",
                    ))
                    seen_ids.add(chunk.chunk_id)
                    canonical_hits += 1
            log_entries.append(f"canonical_hits={canonical_hits}")

        # ── Step 3: Alias keyword match ───────────────────────────────────
        alias_hits = 0
        for chunk, term in self._search_aliases(expanded_aliases):
            if chunk.chunk_id not in seen_ids:
                score = self._score(chunk, "alias_keyword", term, search_terms)
                results.append(RetrievalResult(
                    chunk=chunk,
                    retrieval_score=score,
                    matched_signals=[f"alias:{term}"],
                    match_type="alias_keyword",
                ))
                seen_ids.add(chunk.chunk_id)
                alias_hits += 1
        log_entries.append(f"alias_hits={alias_hits}")

        # ── Step 4: Plain keyword match ────────────────────────────────────
        keyword_hits = 0
        for chunk, term in self._search_keywords(search_terms):
            if chunk.chunk_id not in seen_ids:
                score = self._score(chunk, "keyword", term, search_terms)
                results.append(RetrievalResult(
                    chunk=chunk,
                    retrieval_score=score,
                    matched_signals=[f"keyword:{term}"],
                    match_type="keyword",
                ))
                seen_ids.add(chunk.chunk_id)
                keyword_hits += 1
        log_entries.append(f"keyword_hits={keyword_hits}")

        # ── Step 5: Semantic match (optional) ─────────────────────────────
        semantic_hits = 0
        for chunk, sim in self._search_semantic(query, seen_ids):
            results.append(RetrievalResult(
                chunk=chunk,
                retrieval_score=round(sim * 0.9, 4),
                matched_signals=[f"semantic:{sim:.3f}"],
                match_type="semantic",
            ))
            seen_ids.add(chunk.chunk_id)
            semantic_hits += 1
        log_entries.append(f"semantic_hits={semantic_hits}")

        # ── Rank and trim ─────────────────────────────────────────────────
        results.sort(key=lambda r: r.retrieval_score, reverse=True)
        results = results[: self.max_results]
        log_entries.append(f"total_returned={len(results)}")

        # ── Debug log ─────────────────────────────────────────────────────
        if self.debug:
            self.last_debug_log = RetrievalDebugLog(
                query=query,
                normalized_query=normalized,
                canonical_ref=canonical_ref,
                search_terms=search_terms,
                expanded_aliases=expanded_aliases,
                canonical_hits=canonical_hits,
                alias_hits=alias_hits,
                keyword_hits=keyword_hits,
                semantic_hits=semantic_hits,
                total_returned=len(results),
                log_entries=log_entries,
            )

        return results

    def search_many(self, queries: List[str]) -> Dict[str, List[RetrievalResult]]:
        """
        Run search for multiple queries. Returns a dict query → results.

        Args:
            queries: List of query strings.

        Returns:
            Dict mapping each query string to its result list.
        """
        return {q: self.search(q) for q in queries}

    def hit_rate(self, queries: List[str], min_results: int = 1) -> float:
        """
        Compute the fraction of queries that return at least `min_results` chunks.

        Args:
            queries:     List of query strings to test.
            min_results: Minimum number of results to count as a "hit".

        Returns:
            Float 0.0–1.0.
        """
        if not queries:
            return 0.0
        hits = sum(
            1 for q in queries if len(self.search(q)) >= min_results
        )
        return hits / len(queries)
