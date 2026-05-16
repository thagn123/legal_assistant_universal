# Project Context — AI Legal Intelligence Infrastructure

> Last updated: Phase 11/12
> Source of truth for vision, pipeline, domain vocabulary, and design rules.

---

## Problem

Legal documents vary by jurisdiction, language, format, layout quality, and structural style.
Standard RAG pipelines flatten this variability into plain text, causing:
- Structural loss (hierarchy, tables, citations broken)
- Weak retrieval (keyword match without legal semantics)
- Broken citations (hallucinated article numbers)
- No personalization or session continuity
- No explainability (why was this law retrieved?)

---

## Vision

A **staged AI Legal Intelligence Infrastructure** for Vietnamese law that:

1. Ingests any legal document format (PDF, DOCX, HTML, scanned image)
2. Extracts → chunks → graphs → indexes with full provenance
3. Fuses 4 retrieval signals into ranked candidates
4. Reasons with LLM tool-calling over GraphRAG evidence
5. Reranks with 6 personalization signals including freshness and behavior
6. Maintains multi-turn conversation memory per user
7. Produces citation-grounded, explainable assessments in Vietnamese

---

## System Architecture

### Two Pipelines

**Pipeline A — Document Ingestion (8 stages, `src/pipeline/`)**
```
Upload → Profiler → Extractor → Cleaner → Structurer
       → Chunker → GraphBuilder → RetrievalStage → MongoDB Index
```

**Pipeline B — Query Intelligence (7 stages, `src/engine/`)**
```
Query → QueryPlanner → SessionMemory → RetrievalFusion
      → GraphRAG → LLM Reasoning → RecommendationRanker → Persist
```

---

## Query Intelligence Pipeline — Stage Detail

### Stage 1: QueryPlanner (`src/engine/query_planner.py`)
- **Zero LLM calls** — pure keyword scoring + regex, runs in <10ms
- Detects Vietnamese legal domain from 8-domain vocabulary (70+ keywords)
- Extracts: law references, parties, monetary amounts, dates, locations (regex)
- Classifies dispute type from 9 dispute patterns
- Selects retrieval strategy: `["vector", "bm25", "graph", "cases", "behavior"]`
- Generates 2–4 query variants (original + domain-enriched + law-ref focused + truncated)

### Stage 2: Session Memory (`src/memory/session_store.py`)
- MongoDB collections: `conversation_sessions`, `reasoning_traces`, `session_context`
- 24h TTL on `last_active` field via MongoDB TTL index
- Preserves: history (last 50 turns), law_type_preferences, last_query_plan
- Informs domain detection: if query is "general" but session has history → use session domain

### Stage 3: Retrieval Fusion (`src/engine/retrieval_fusion.py`)
| Signal | Weight | Method |
|---|---|---|
| Vector | 0.45 | MongoDB `$vectorSearch`, 384-dim cosine |
| BM25 | 0.20 | TF approximation × 20 scalar |
| Graph | 0.25 | Law-reference keyword expansion, fixed score 0.75 |
| Behavior | 0.10 | User domain rank → linear boost |

All signals min-max normalized before weighted sum.

### Stage 4: GraphRAG Traversal (`src/graphrag/traversal.py`)
BFS from law-reference seed nodes with edge weights:

| Edge | Weight | Meaning |
|---|---|---|
| OVERRIDES | 0.92 | Newer rule supersedes older |
| INVALIDATES | 0.90 | Amendment invalidates prior rule |
| CONFLICTS_WITH | 0.88 | Two rules in direct conflict |
| REQUIRES | 0.82 | Rule requires another to be satisfied |
| DEPENDS_ON | 0.78 | Logical dependency |
| AMENDS | 0.85 | Source unit amends target |
| CITES | 0.85 | Citation reference |
| CONTAINS | 0.90 | Hierarchy parent→child |

Depth penalty: −0.10 per BFS level.

### Stage 5: LLM Reasoning (`src/llm/tool_calling.py`)
- OpenAI tool-calling loop, max 4 rounds
- Tools: `retrieve_law_chunks`, `retrieve_similar_cases`, `get_graph_context`, `assess_legal_position`, `draft_legal_response`
- Graceful fallback to deterministic assessment if LLM unavailable or quota exceeded

### Stage 6: Recommendation Ranker (`src/engine/recommendation_ranker.py`)
| Signal | Weight | Source |
|---|---|---|
| semantic | 0.35 | cosine similarity from vector search |
| graph | 0.20 | BFS traversal relevance |
| behavior | 0.15 | user interaction history |
| freshness | 0.15 | exp(−ln(2)/180 × days) → half-life 180 days |
| popularity | 0.10 | peer interaction count, normalized |
| accepted | 0.05 | save+download community signal |

Output: `RankedItem` with Vietnamese explanation of dominant signal.

### Stage 7: Persist
- `save_trace()` → `reasoning_traces` collection
- `save_context()` → `conversation_sessions` collection (upsert)
- `cache_retrieval_context()` → `session_context` collection (24h cache)
- `log_interaction()` → `interactions` collection

---

## Legal Domain Vocabulary

| Code | Vietnamese Name | Key Trigger Words |
|---|---|---|
| `dat_dai` | Đất đai | đất, sổ đỏ, quyền sử dụng đất, thu hồi, bồi thường đất |
| `hop_dong` | Hợp đồng | hợp đồng, điều khoản, vi phạm, phạt vi phạm |
| `lao_dong` | Lao động | lao động, sa thải, lương, bhxh, tai nạn lao động |
| `doanh_nghiep` | Doanh nghiệp | công ty, cổ đông, phá sản, vốn điều lệ |
| `dan_su` | Dân sự | thừa kế, di chúc, tài sản, hôn nhân, bồi thường |
| `hinh_su` | Hình sự | tội phạm, truy tố, xét xử, phạt tù |
| `hanh_chinh` | Hành chính | khiếu nại, quyết định hành chính, ubnd, xử phạt |
| `gia_dinh` | Gia đình | ly hôn, nuôi con, cấp dưỡng, vợ chồng |

---

## Graph Edge Types (`src/schemas/graph.py`)

**Structural edges** (hierarchy):
`CONTAINS`, `PRECEDES`, `HAS_TABLE`, `HAS_IMAGE`, `DERIVED_TO_CHUNK`

**Citation edges**:
`CITES`, `RESOLVES_TO`, `REFERS_TO`

**Semantic edges** (legal relationships):
`MENTIONS`, `DEFINES`, `APPLIES_TO`, `IMPOSES`, `QUALIFIED_BY`,
`EXCEPTED_BY`, `ENFORCED_BY`, `SUPPORTS`, `CONTRADICTS`, `AMENDS`,
`OVERRIDES`, `INVALIDATES`, `CONFLICTS_WITH`, `REQUIRES`, `DEPENDS_ON`

**Alias edges**:
`ALIAS_OF` (cross-language)

---

## Behavior Recommendation System (`src/recommenders/behavior_recommender.py`)

- **UserBehaviorProfile**: law_type_weights (recency-decayed), action_frequencies, active_hours, adjacent_domains
- **Decay rate**: 0.08 → half-life ≈ 8.7 days for interaction recency
- **Bigram pattern mining**: sequential `(action_A, action_B)` patterns from history
- **Collaborative filtering**: peer users = users with overlapping top law_types
- **5 recommendation types**: proactive, next-action, from-peers, daily-digest, domain-adjacent

---

## Design Principles

### Structure-first
Preserve hierarchy, numbering, citations during extraction. Chunks follow legal structure, not token windows.

### Evidence-first
Every answer grounded in retrieved source. Refusal preferred over unsupported completion.

### Observability-first
`ExecutionTracer` singleton emits structured JSON per stage. All timings logged. Reasoning traces persisted.

### Backward-compatible
`LegalAgent.analyze_situation()` delegates to orchestrator via lazy import, falls back on any error — no breaking changes to existing API consumers.

### Deterministic fallback
If OpenAI is unavailable, quota exceeded, or raises an error: system falls back to rule-based assessment. Zero hard dependency on external LLM at runtime.

---

## Non-Scope (do not implement)

- Direct legal advice without human review
- Autonomous filing or regulatory submission
- Guarantee of jurisdictional completeness
- Rewriting source text during extraction
- Injecting inferred text for missing content
- Merging conflicting legal authorities into a single synthetic rule

---

## Success Criteria

- Domain detection accuracy > 85% on Vietnamese legal queries
- Retrieval P@5 > 0.75 for single-domain queries
- LLM tool-calling: ≤ 4 rounds, graceful fallback on failure
- Session memory: correct law_type_preferences after 2+ turns
- Ranking: freshness signal correctly penalizes documents > 365 days old
- Graph traversal: OVERRIDES/INVALIDATES edges correctly demote superseded laws
- API latency: Stage 1 < 10ms; full pipeline < 5s with LLM, < 500ms deterministic

---

## Planned Next Steps (Phase 12)

- [ ] Frontend integration with the intelligence API (React / Stitch UI)
- [ ] Evaluation harness: automated P@5, MRR, hallucination rate measurement
- [ ] Docker production hardening (multi-stage build, secrets management)
- [ ] Ingest real Vietnamese law corpus (Luật Đất đai 2024, Bộ luật Dân sự 2015, ...)
- [ ] Temporal reasoning: effective dates, amendment supersession chains
- [ ] Human review workflow for low-confidence outputs
- [ ] Policy packs per jurisdiction
