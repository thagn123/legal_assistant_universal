# CLAUDE.md — AI Legal Intelligence Infrastructure

> Auto-loaded by Claude Code at the start of every session.
> Keep this file up-to-date after each major architectural change.

---

## Project Identity

**Name:** Universal Legal Knowledge Assistant (LexAI / ULKA)
**Stack:** Python 3.11 · FastAPI · MongoDB Atlas · sentence-transformers · OpenAI API
**Language:** Vietnamese legal domain (UI + domain vocabulary), codebase in English
**Phase:** 11/12 — AI Legal Intelligence Infrastructure (current)
**Repo branch:** `main`

---

## Vision

Transform from a RAG chatbot into a **staged AI Legal Intelligence Infrastructure** that:
- Parses, chunks, and graphs Vietnamese legal documents
- Fuses multiple retrieval signals (vector + BM25 + graph + behavior)
- Reasons over evidence with LLM tool-calling (fallback: deterministic)
- Reranks results using 6 personalization signals
- Maintains conversation memory across turns
- Produces explainable, citation-grounded legal assessments

---

## Module Map

```
src/
├── api/
│   ├── app.py                     # FastAPI factory — registers all routers
│   ├── routes.py                  # Core document/job/query routes
│   ├── recommendation_routes.py   # rec_router, interact_router, agent_router,
│   │                              #   behavior_router, intelligence_router
│   ├── deps.py                    # require_user dependency
│   └── models.py                  # Pydantic request/response models
│
├── engine/                        # ★ 7-Stage Orchestration Pipeline
│   ├── orchestrator.py            # LegalIntelligenceOrchestrator (main coordinator)
│   ├── query_planner.py           # Stage 1 — deterministic domain/entity/strategy
│   ├── retrieval_fusion.py        # Stage 3 — hybrid vector+BM25+graph+behavior
│   ├── recommendation_ranker.py   # Stage 6 — 6-signal reranking
│   └── reasoning_trace.py         # StageTrace / ReasoningTrace / TraceBuilder
│
├── memory/
│   └── session_store.py           # MongoDB-backed 24h TTL conversation memory
│
├── observability/
│   └── tracer.py                  # ExecutionTracer singleton (structured JSON logs)
│
├── agents/
│   ├── legal_agent.py             # LegalAgent — delegates to orchestrator, fallback to LLM
│   └── tools.py                   # OpenAI tool definitions (retrieve_*, draft_*)
│
├── graphrag/
│   ├── traversal.py               # BFS graph traversal with edge weights
│   ├── evidence_bundle.py         # EvidenceBundle construction
│   ├── reasoning.py               # Legal reasoning chains
│   ├── legal_ontology.py          # Node/edge type definitions
│   └── query_intent.py            # Intent classification
│
├── pipeline/                      # 8-Stage Document Ingestion
│   ├── orchestrator.py            # Pipeline coordinator
│   ├── extractor.py               # Stage 1 — PDF/DOCX/HTML extraction
│   ├── profiler.py                # Stage 2 — layout profiling
│   ├── cleaner.py                 # Stage 3 — OCR cleanup
│   ├── structurer.py              # Stage 4 — canonical schema
│   ├── chunker.py                 # Stage 5 — legal chunking
│   ├── graph_builder.py           # Stage 6 — graph construction
│   ├── retrieval_stage.py         # Stage 7 — indexing
│   ├── embedding_stage.py         # embed_text() shared utility
│   └── stages.py                  # Stage interfaces
│
├── recommenders/
│   ├── behavior_recommender.py    # Collaborative filter + bigram pattern mining
│   ├── situation_analyzer.py      # Vector-based situation analysis
│   ├── document_recommender.py    # Hybrid vector + collab filter docs
│   ├── template_recommender.py    # Contract template recommendations
│   ├── risk_recommender.py        # Legal risk recommendations
│   └── checklist_recommender.py   # Compliance checklists
│
├── mongodb/
│   ├── client.py                  # get_db(), ping()
│   ├── mongo_storage.py           # VectorStorage — all MongoDB operations
│   └── seed_data.py               # Seed templates/risks/checklists (idempotent)
│
├── llm/
│   ├── client.py                  # LLMClient — OpenAI wrapper with is_available()
│   ├── tool_calling.py            # OpenAI tool-calling loop (max 4 rounds)
│   └── prompts.py                 # Prompt templates
│
├── retrieval/
│   ├── retrieval_engine.py        # Legacy retrieval engine
│   ├── canonical_references.py    # Law reference normalization
│   ├── legal_aliases.py           # Cross-language alias mapping
│   ├── language_detector.py       # Vi/En detection
│   └── query_normalizer.py        # Query preprocessing
│
├── actions/
│   ├── action_engine.py           # Action dispatch (draft, compare, assess)
│   ├── action_schema.py           # Action type definitions
│   └── workflows.py               # Multi-step action workflows
│
├── contract/
│   └── clause_extractor.py        # Contract clause extraction + risk flagging
│
├── runtime/
│   ├── processor.py               # build_document_processor() — wires 8-stage pipeline
│   ├── job_runner.py              # Background job queue (JobRunner)
│   ├── storage.py                 # SQLite StorageLayer
│   ├── auth.py                    # AuthLayer
│   ├── audit.py                   # AuditLayer
│   └── index_store.py             # DocumentIndexStore
│
├── schemas/
│   ├── graph.py                   # NODE_TYPES, EDGE_TYPES, SEMANTIC_EDGES, STRUCTURAL_EDGES
│   ├── chunk.py                   # Chunk schema
│   ├── document.py                # Document schema
│   └── evaluation.py              # Evaluation metrics schema
│
└── evaluation/
    ├── metrics.py                 # Evaluation metrics
    ├── checks.py                  # Quality checks
    ├── multilingual_metrics.py    # Vi/En multilingual checks
    └── reports.py                 # Report generation
```

---

## 7-Stage Intelligence Pipeline (`src/engine/orchestrator.py`)

```
User Query
    │
    ▼ Stage 1 — QueryPlanner (deterministic, <10ms, no LLM)
    │   Detects domain · extracts entities · classifies dispute
    │   Selects retrieval strategy · generates 2-4 query variants
    │
    ▼ Stage 2 — SessionStore.load_context()
    │   Loads 24h TTL MongoDB session (history, law_type_preferences)
    │   Creates new session if first turn
    │
    ▼ Stage 3 — RetrievalFusionEngine.fuse()
    │   Signal 1: Vector search ($vectorSearch, 384-dim cosine, weight 0.45)
    │   Signal 2: BM25 keyword TF approximation (weight 0.20)
    │   Signal 3: Graph-expanded law-reference keyword (weight 0.25)
    │   Signal 4: Behavior boost from user interaction history (weight 0.10)
    │   → Min-max normalize each signal → weighted sum → FusedResultSet
    │
    ▼ Stage 4 — GraphRAG traversal
    │   BFS from seeded law-reference nodes
    │   Edge weights: OVERRIDES(0.92) > INVALIDATES(0.90) > CONFLICTS_WITH(0.88)
    │   > REQUIRES(0.82) > DEPENDS_ON(0.78) > AMENDS(0.85) > CITES(0.85) ...
    │   Depth penalty: 0.10 per BFS level
    │
    ▼ Stage 5 — LLM Reasoning (OpenAI tool-calling, max 4 rounds)
    │   Tools: retrieve_law_chunks, retrieve_similar_cases,
    │          get_graph_context, assess_legal_position, draft_legal_response
    │   Fallback: deterministic assessment if LLM unavailable
    │
    ▼ Stage 6 — RecommendationRanker.rank()
    │   semantic(0.35) · behavior(0.15) · graph(0.20) · freshness(0.15)
    │   · popularity(0.10) · accepted(0.05)
    │   Freshness: exp(-ln(2)/180 * days) → half-life 180 days
    │   Vietnamese explanation per item
    │
    ▼ Stage 7 — Persist
        save_trace() · save_context() · cache_retrieval_context() · log_interaction()
```

---

## 8-Stage Document Ingestion Pipeline (`src/pipeline/`)

```
Upload → Profiler → Extractor → Cleaner → Structurer
       → Chunker → GraphBuilder → RetrievalStage → Index
```

Each stage emits: `document_id`, `source_hash`, `processing_version`, `provenance`, `confidence`, `status`.

---

## Legal Domains (Vietnamese)

| Code | Domain | Keywords (sample) |
|---|---|---|
| `dat_dai` | Land law | đất, sổ đỏ, quyền sử dụng đất, thu hồi, bồi thường |
| `hop_dong` | Contract law | hợp đồng, vi phạm, đơn phương chấm dứt, phạt |
| `lao_dong` | Labour law | lao động, sa thải, lương, bhxh, tai nạn lao động |
| `doanh_nghiep` | Corporate law | công ty, cổ đông, phá sản, vốn điều lệ |
| `dan_su` | Civil law | dân sự, thừa kế, di chúc, hôn nhân, bồi thường |
| `hinh_su` | Criminal law | hình sự, tội phạm, truy tố, phạt tù |
| `hanh_chinh` | Administrative law | khiếu nại, quyết định hành chính, ubnd |
| `gia_dinh` | Family law | hôn nhân, ly hôn, nuôi con, cấp dưỡng |
| `general` | Undetected | fallback |

---

## API Endpoints

### Intelligence (new — full 7-stage pipeline)
| Method | Path | Description |
|---|---|---|
| POST | `/intelligence/analyze` | Full pipeline analysis → `IntelligenceOut` |
| GET | `/intelligence/trace/{trace_id}` | Retrieve reasoning trace |
| GET | `/intelligence/session/{session_id}` | Retrieve conversation history |

### Agent (legacy — delegates to orchestrator internally)
| Method | Path | Description |
|---|---|---|
| POST | `/agent/analyze` | Full agentic legal analysis |
| POST | `/agent/contract` | Contract clause analysis |

### Recommendations
| Method | Path | Description |
|---|---|---|
| POST | `/recommendations/situation` | Law chunk recommendations |
| POST | `/recommendations/cases` | Similar case retrieval |
| POST | `/recommendations/documents` | Hybrid document recommendations |
| POST | `/recommendations/templates` | Contract template suggestions |
| POST | `/recommendations/risks` | Legal risk recommendations |
| POST | `/recommendations/checklists` | Compliance checklists |

### Behavior
| Method | Path | Description |
|---|---|---|
| GET | `/recommendations/behavior/profile` | User behavior profile |
| GET | `/recommendations/behavior/proactive` | Proactive recommendations |
| POST | `/recommendations/behavior/next-action` | Next-action prediction |
| GET | `/recommendations/behavior/peers` | Peer-based recommendations |
| GET | `/recommendations/behavior/digest` | Daily digest |

### Interactions
| Method | Path | Description |
|---|---|---|
| POST | `/interactions/log` | Log view/save/download interaction |

---

## MongoDB Collections

| Collection | Purpose | TTL |
|---|---|---|
| `law_chunks` | Chunked legal documents with 384-dim embeddings | — |
| `legal_cases` | Case law documents | — |
| `interactions` | User interaction events (view/save/download) | — |
| `conversation_sessions` | Multi-turn session context | 24h on `last_active` |
| `reasoning_traces` | Per-query structured reasoning traces | — |
| `session_context` | Retrieval cache per session | 24h via `expires_at` |

Vector index: `law_chunks.embedding` (384-dim cosine, `$vectorSearch`)

---

## Key Design Decisions

1. **Backward-compatible orchestrator delegation**: `legal_agent.py` tries orchestrator first via lazy import, falls back to LLM/deterministic on any error — zero breaking changes.
2. **No LLM at query planning (Stage 1)**: Pure keyword scoring + regex entity extraction, <10ms, reproducible.
3. **BM25 approximation**: TF-only (no corpus IDF needed), scaled ×20 to produce useful [0,1] range.
4. **Freshness half-life 180 days**: `exp(-ln(2)/180 * days)` — documents ~6 months old score ~0.5.
5. **Behavior decay rate 0.08**: `exp(-0.08 * days)` — half-life ~8.7 days for interaction recency.
6. **GraphRAG new edges**: OVERRIDES > INVALIDATES > CONFLICTS_WITH > REQUIRES > DEPENDS_ON (added Phase 11).
7. **Session TTL 24h**: MongoDB TTL index on `last_active` field, automatic cleanup.
8. **Weights validation**: `RecommendationRanker` raises `ValueError` if weights don't sum to 1.0 ±0.02.

---

## Running Locally

```bash
# Start MongoDB
docker compose up -d

# Install deps
pip install -r requirements.txt

# Run API
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

# Or with Docker
docker build -t ulka . && docker run -p 8000:8000 ulka
```

Environment variables required:
- `MONGODB_URI` — MongoDB connection string (default: `mongodb://localhost:27017`)
- `OPENAI_API_KEY` — for LLM reasoning (optional; system falls back to deterministic)

---

## Coding Conventions

- All new engine/memory/observability modules use `from __future__ import annotations`
- Dataclasses for DTOs, Pydantic only at API boundary
- Structured logging via `logging.getLogger(__name__)` — never `print()`
- `ExecutionTracer` singleton for cross-cutting timing/ranking/retrieval logs
- Lazy imports inside methods to avoid circular imports (especially orchestrator ↔ legal_agent)
- Vietnamese text in: explanations, domain labels, UI-facing strings
- English in: all code identifiers, log messages, docstrings

---

## Phase History

| Phase | Description |
|---|---|
| 1–4 | Document ingestion: extraction, profiling, OCR, canonical schema |
| 5–8 | Legal chunking, retrieval stabilization, GraphRAG, reasoning |
| 9 | Action Engine: drafting, compliance, risk, comparison |
| 10 | Product Runtime: API, SQLite storage, auth, audit, job orchestration |
| 11 | AI Legal Intelligence Infrastructure (current): staged pipeline, retrieval fusion, reranking, session memory, observability, behavior recommender |
| 12 | (Next) UI integration, evaluation harness, deployment hardening |
