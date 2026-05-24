# CLAUDE.md — AI Legal Intelligence Infrastructure

> Auto-loaded by Claude Code at the start of every session.
> Keep this file up-to-date after each major architectural change.

---

## Project Identity

**Name:** Universal Legal Knowledge Assistant (LexAI / ULKA)
**Stack:** Python 3.11 · FastAPI · MongoDB Atlas · sentence-transformers · OpenAI API · React 19 + TypeScript + Vite + Tailwind
**Language:** Vietnamese legal domain (UI + domain vocabulary), codebase in English
**Phase:** 15 — Extended Save/History + Search + UX Improvements (current)
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
src/                                  # Python backend
├── api/
│   ├── app.py                        # FastAPI factory — registers all routers
│   ├── routes.py                     # Core document/job/query routes + upload-file endpoint
│   ├── admin_routes.py               # ★ NEW — Admin router (prefix /admin, require_admin dep)
│   ├── recommendation_routes.py      # rec_router, interact_router, agent_router,
│   │                                 #   behavior_router, intelligence_router
│   ├── deps.py                       # require_user + require_admin dependencies
│   └── models.py                     # Pydantic request/response models
│
├── engine/                           # ★ 7-Stage Orchestration Pipeline
│   ├── orchestrator.py               # LegalIntelligenceOrchestrator (main coordinator)
│   ├── query_planner.py              # Stage 1 — deterministic domain/entity/strategy
│   ├── retrieval_fusion.py           # Stage 3 — hybrid vector+BM25+graph+behavior
│   ├── recommendation_ranker.py      # Stage 6 — 6-signal reranking
│   └── reasoning_trace.py            # StageTrace / ReasoningTrace / TraceBuilder
│
├── memory/
│   ├── session_store.py              # MongoDB-backed 24h TTL conversation memory
│   ├── user_memory_store.py          # ★ NEW — Persistent cross-session memory (no TTL)
│   │                                 #   PersonalInfo + SituationRecord dataclasses
│   │                                 #   UserMemoryStore CRUD + get_context_for_prompt()
│   └── reflection_agent.py           # ★ NEW — Two-tier post-turn extraction (daemon thread)
│                                     #   Tier 1: regex (name/age/occupation/location, <1ms)
│                                     #   Tier 2: LLM async, rate-limited 1 call/60s/user
│
├── observability/
│   └── tracer.py                     # ExecutionTracer singleton (structured JSON logs)
│
├── agents/
│   ├── legal_agent.py                # LegalAgent — delegates to orchestrator, fallback to LLM
│   └── tools.py                      # OpenAI tool definitions (retrieve_*, draft_*)
│
├── graphrag/
│   ├── traversal.py                  # BFS graph traversal with edge weights
│   ├── evidence_bundle.py            # EvidenceBundle construction
│   ├── reasoning.py                  # Legal reasoning chains
│   ├── legal_ontology.py             # Node/edge type definitions
│   └── query_intent.py               # Intent classification
│
├── pipeline/                         # 8-Stage Document Ingestion
│   ├── orchestrator.py               # Pipeline coordinator
│   ├── extractor.py                  # Stage 1 — PDF/DOCX/HTML extraction
│   ├── profiler.py                   # Stage 2 — layout profiling
│   ├── cleaner.py                    # Stage 3 — OCR cleanup
│   ├── structurer.py                 # Stage 4 — canonical schema
│   ├── chunker.py                    # Stage 5 — legal chunking
│   ├── graph_builder.py              # Stage 6 — graph construction
│   ├── retrieval_stage.py            # Stage 7 — indexing
│   ├── embedding_stage.py            # embed_chunks_into_mongo() — is_global param added
│   └── stages.py                     # Stage interfaces
│
├── recommenders/
│   ├── behavior_recommender.py       # Collaborative filter + bigram pattern mining
│   ├── situation_analyzer.py         # Vector-based situation analysis
│   ├── document_recommender.py       # Hybrid vector + collab filter docs
│   ├── template_recommender.py       # Contract template recommendations
│   ├── risk_recommender.py           # Legal risk recommendations
│   └── checklist_recommender.py      # Compliance checklists
│
├── mongodb/
│   ├── client.py                     # get_db(), ping()
│   ├── mongo_storage.py              # VectorStorage — all MongoDB operations (is_global support)
│   └── seed_data.py                  # Seed templates/risks/checklists (idempotent)
│
├── llm/
│   ├── client.py                     # LLMClient — OpenAI wrapper with is_available()
│   ├── tool_calling.py               # OpenAI tool-calling loop (max 4 rounds)
│   └── prompts.py                    # Prompt templates
│
├── retrieval/
│   ├── retrieval_engine.py           # Legacy retrieval engine
│   ├── canonical_references.py       # Law reference normalization
│   ├── legal_aliases.py              # Cross-language alias mapping
│   ├── language_detector.py          # Vi/En detection
│   └── query_normalizer.py           # Query preprocessing
│
├── actions/
│   ├── action_engine.py              # Action dispatch (draft, compare, assess)
│   ├── action_schema.py              # Action type definitions
│   └── workflows.py                  # Multi-step action workflows
│
├── contract/
│   └── clause_extractor.py           # Contract clause extraction + risk flagging
│
├── runtime/
│   ├── processor.py                  # build_document_processor() — auto-detects is_global
│   ├── job_runner.py                 # Background job queue (JobRunner)
│   ├── storage.py                    # SQLite StorageLayer — is_global column added
│   ├── auth.py                       # AuthLayer
│   ├── audit.py                      # AuditLayer
│   └── index_store.py                # DocumentIndexStore
│
├── schemas/
│   ├── graph.py                      # NODE_TYPES, EDGE_TYPES, SEMANTIC_EDGES, STRUCTURAL_EDGES
│   ├── chunk.py                      # Chunk schema
│   ├── document.py                   # Document schema
│   └── evaluation.py                 # Evaluation metrics schema
│
└── evaluation/
    ├── metrics.py                    # Evaluation metrics
    ├── checks.py                     # Quality checks
    ├── multilingual_metrics.py       # Vi/En multilingual checks
    └── reports.py                    # Report generation

lexai-–-trợ-lý-pháp-lý-thông-minh UI/src/     # React frontend
├── lib/
│   ├── api.ts                        # API client — adminFetch, dynamic getUserId(), admin endpoints
│   │                                 #   UserMemory/UserMemoryInfo/SituationRecord types
│   │                                 #   getUserMemory() / updateUserMemory()
│   │                                 #   ★ Phase 14: BehaviorProfile type + getBehaviorProfile()
│   │                                 #   ★ Phase 14: AnalysisHistoryItem + saveAnalysis/loadHistory/deleteHistoryItem/clearHistory
│   │                                 #   API_BASE default: http://localhost:8001
│   ├── adminAuth.ts                  # getAdminKey/setAdminKey/isAdminAuthenticated
│   └── (vite-env.d.ts)               # ★ Phase 14 fix — /// <reference types="vite/client" />
│
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx               # User sidebar navigation
│   │   └── Header.tsx                # User header — ★ NEW: shows displayName from UserMemory
│   └── admin/
│       └── AdminLayout.tsx           # ★ NEW — Admin shell (sidebar + auth guard + Outlet)
│
├── pages/
│   ├── Dashboard.tsx                 # User dashboard — digest + proactive + personalized feed + behavior chart (real API)
│   ├── Analyze.tsx                   # Legal analysis chat (sessions from localStorage)
│   ├── Journey.tsx                   # Legal journey mode
│   ├── Actions.tsx                   # Action planner
│   ├── Timeline.tsx                  # Timeline tracker + Save button → localStorage history
│   ├── LawSearch.tsx                 # Law retrieval
│   ├── SimilarCases.tsx              # Similar case explorer
│   ├── Contract.tsx                  # Contract analysis
│   ├── ClauseCoach.tsx               # Clause coach + Save button
│   ├── ClauseSearch.tsx              # Clause similarity search
│   ├── EvidenceGap.tsx               # Evidence gap detector + Save button
│   ├── ComplianceRadar.tsx           # Compliance radar
│   ├── Documents.tsx                 # Document list
│   ├── Templates.tsx                 # Contract templates
│   ├── Risks.tsx                     # Legal risk panel
│   ├── Checklists.tsx                # Compliance checklists
│   ├── AnalysisHistory.tsx           # ★ Phase 14 — saved analyses (localStorage), filter by type
│   ├── Profile.tsx                   # User profile — "AI ghi nhớ về bạn" card
│   └── admin/
│       ├── AdminLogin.tsx            # ★ NEW — Admin key login form
│       ├── AdminDashboard.tsx        # ★ NEW — Admin home with quick links
│       ├── AdminDocuments.tsx        # ★ NEW — Upload + document management table
│       ├── AdminJobs.tsx             # ★ NEW — Job history table with polling
│       └── AdminStats.tsx            # ★ NEW — Stats cards + Recharts charts
│
└── App.tsx                           # Routes — /admin/* handled separately from user routes
```

---

## User Memory Infrastructure (Phase 13)

### Cross-Session Memory Flow

```
User Turn                              Background (daemon thread)
    │                                         │
    ▼ Stage 2b                                │
UserMemoryStore.get(user_id)                  │
  → PersonalInfo (name/age/occ/loc/notes)    │
  → SituationRecords[-3:]                     │
    → prepended to Stage 5 LLM message        │
    │                                         │
    ▼ Stage 7b (after response sent)          │
ReflectionAgent.reflect_async(...)            │
    │                                         ▼
    └─────────────────────────────────► _tier1_patterns()  [<1ms, always]
                                          regex: name/age/occupation/location
                                          → UserMemoryStore.update_personal_info()
                                        _tier2_llm()  [if rate allows, domain≠general]
                                          LLM → JSON {personal_info, situation_summary}
                                          → update_personal_info() + upsert_situation_summary()
```

### UserMemory Schema

```python
@dataclass
class PersonalInfo:
    name: Optional[str]         # extracted from "tên tôi là ..."
    age: Optional[int]          # extracted from "X tuổi"
    occupation: Optional[str]   # from job title keywords
    location: Optional[str]     # from major Vietnamese cities
    notes: Optional[str]        # free-form, user-edited via PUT /memory

@dataclass
class SituationRecord:
    session_id: str
    date: str           # YYYY-MM-DD
    domain: str         # law domain code
    summary: str        # 1-sentence ≤ 150 chars (LLM-generated)
    resolved: bool      # default False, settable via mark_situation_resolved()

# MongoDB document structure (collection: user_memory, no TTL)
{
  "user_id": "abc123",
  "personal_info": { "name": ..., "age": ..., "occupation": ..., "location": ..., "notes": ... },
  "situation_summaries": [ ...last 20... ],
  "updated_at": "2025-05-18T..."
}
```

### Profile Page — "AI ghi nhớ về bạn" Card

- Fetches `GET /recommendations/behavior/memory` on mount
- Displays PersonalInfo fields in a 2-column grid; empty fields show italic placeholder
- "Chỉnh sửa" button → all fields become inputs → "Lưu" calls `PUT /recommendations/behavior/memory`
- Notes field: free-form textarea for anything the user wants AI to remember
- Situation summaries: last 5, newest first — domain badge + resolved/pending status dot

### Header — Personalized Greeting

- `getUserMemory()` called on mount and on userId change
- If `personal_info.name` known: button shows real name; dropdown shows `"Xin chào, [name]"`
- Clears `displayName` and re-fetches when user switches to a different userId

---

## Admin Infrastructure (Phase 12)

### Global Document Flow

```
ADMIN                                  USER
  │                                      │
  ▼                                      ▼
POST /admin/documents/upload        POST /intelligence/analyze
  X-Admin-Key: lexai-admin-secret    X-User-ID: <user_id>
  multipart/form-data                     │
  │                                       │
  ▼                                       ▼
storage.create_global_document()    mongo_storage.vector_search_chunks(user_id)
  user_id = "admin"                   filter: {$or: [{user_id}, {is_global: true}]}
  is_global = True                         │
  │                                        │
  ▼                                        ▼
job_runner.submit("admin", doc_id)    → returns admin docs + user's own docs
  │
  ▼
processor detects: is_global = (user_id == "admin")
  │
  ▼
embed_chunks_into_mongo(..., is_global=True)
  │
  ▼
MongoDB chunk: {user_id: "admin", is_global: true, embedding: [...]}
```

### Admin Auth

- Header: `X-Admin-Key`
- Env var: `ADMIN_API_KEY` (default: `lexai-admin-secret` if not set)
- Dependency: `require_admin` in `src/api/deps.py` — raises HTTP 403 if key missing/wrong
- Frontend: key stored in `localStorage` key `lexai_admin_key`

### Admin API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/admin/documents/upload` | Multipart upload, multiple files, creates global docs |
| GET | `/admin/documents` | All docs (all user_ids), `?status=&limit=&offset=` |
| GET | `/admin/documents/{doc_id}` | Single doc detail |
| DELETE | `/admin/documents/{doc_id}` | Delete doc + MongoDB chunks + disk files |
| POST | `/admin/documents/{doc_id}/reprocess` | Re-queue failed/complete job |
| GET | `/admin/jobs` | All jobs, `?status=&limit=` |
| GET | `/admin/stats` | Collection counts, job stats, embedding counts |

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
    ▼ Stage 2b — UserMemoryStore.get_context_for_prompt()  ★ NEW
    │   Loads permanent cross-session UserMemory (no TTL)
    │   Builds context block: name · age · occupation · location · notes
    │   + last 3 SituationRecords — prepended to Stage 5 user message
    │
    ▼ Stage 3 — RetrievalFusionEngine.fuse()
    │   Signal 1: Vector search ($vectorSearch, 384-dim cosine, weight 0.45)
    │   Signal 2: BM25 keyword TF approximation (weight 0.20)
    │   Signal 3: Graph-expanded law-reference keyword (weight 0.25)
    │   Signal 4: Behavior boost from user interaction history (weight 0.10)
    │   → Min-max normalize each signal → weighted sum → FusedResultSet
    │   IMPORTANT: all queries include {$or: [{user_id}, {is_global: True}]}
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
    │   User message prefixed with UserMemory context block if available  ★ NEW
    │   Fallback: deterministic assessment if LLM unavailable
    │
    ▼ Stage 6 — RecommendationRanker.rank()
    │   semantic(0.35) · behavior(0.15) · graph(0.20) · freshness(0.15)
    │   · popularity(0.10) · accepted(0.05)
    │   Freshness: exp(-ln(2)/180 * days) → half-life 180 days
    │   Vietnamese explanation per item
    │
    ▼ Stage 7 — Persist
    │   save_trace() · save_context() · cache_retrieval_context() · log_interaction()
    │
    ▼ Stage 7b — ReflectionAgent.reflect_async()  ★ NEW
        Daemon thread — returns immediately, never blocks response
        Tier 1 (always): regex extracts name/age/occupation/location from query
        Tier 2 (if session_turns≥1 AND domain≠general AND rate OK):
          LLM call → JSON {personal_info, situation_summary}
          Upserts SituationRecord into user_memory collection
```

---

## 8-Stage Document Ingestion Pipeline (`src/pipeline/`)

```
Upload → Profiler → Extractor → Cleaner → Structurer
       → Chunker → GraphBuilder → RetrievalStage → Index
```

Each stage emits: `document_id`, `source_hash`, `processing_version`, `provenance`, `confidence`, `status`.

The processor (`src/runtime/processor.py`) auto-detects `is_global = (user_id == "admin")` and passes it through to `embed_chunks_into_mongo()`.

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

### Admin (require X-Admin-Key header)
| Method | Path | Description |
|---|---|---|
| POST | `/admin/documents/upload` | Multipart upload (PDF/DOCX/DOC/HTML/images) |
| GET | `/admin/documents` | List all documents across all users |
| GET | `/admin/documents/{doc_id}` | Document detail |
| DELETE | `/admin/documents/{doc_id}` | Delete doc + chunks + disk files |
| POST | `/admin/documents/{doc_id}/reprocess` | Re-queue job |
| GET | `/admin/jobs` | All jobs list |
| GET | `/admin/stats` | System statistics |

### Intelligence (full 7-stage pipeline)
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

### Documents
| Method | Path | Description |
|---|---|---|
| POST | `/documents/upload-file` | Multipart upload for regular users |
| POST | `/documents/upload` | Base64 upload (legacy) |
| GET | `/documents` | User's own documents |
| GET | `/documents/{doc_id}/status` | Job status |

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
| GET | `/recommendations/behavior/memory` | ★ NEW — Get user's cross-session memory |
| PUT | `/recommendations/behavior/memory` | ★ NEW — Update PersonalInfo fields |

### Interactions
| Method | Path | Description |
|---|---|---|
| POST | `/interactions/log` | Log view/save/download interaction |

---

## MongoDB Collections

| Collection | Purpose | TTL |
|---|---|---|
| `law_chunks` | Chunked legal documents with 384-dim embeddings + `is_global` field | — |
| `legal_cases` | Case law documents | — |
| `interactions` | User interaction events (view/save/download) | — |
| `conversation_sessions` | Multi-turn session context | 24h on `last_active` |
| `reasoning_traces` | Per-query structured reasoning traces | — |
| `session_context` | Retrieval cache per session | 24h via `expires_at` |
| `user_memory` | ★ NEW — Permanent cross-session user memory: PersonalInfo + SituationRecords (last 20) | **none** |

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
9. **is_global convention**: `user_id == "admin"` → `is_global = True` auto-detected in processor — no extra parameters needed. All users query `{$or: [{user_id}, {is_global: true}]}`.
10. **Admin key**: Simple header-based auth (`X-Admin-Key`), no JWT/session — intentional for simplicity. Admin panel is internal tooling only.
11. **Frontend admin routing**: `useLocation()` checks `/admin` prefix → renders completely separate layout tree (AdminLayout) vs user layout (Sidebar+Header). No shared state between admin and user sessions.
12. **Session persistence (Analyze)**: Conversation history stored in `localStorage` (max 20 sessions), not fetched from server per session — reduces latency for demo mode.
13. **UserMemory no TTL**: Unlike `conversation_sessions` (24h), `user_memory` collection never expires — stores personal facts that accumulate over a user's lifetime on the platform.
14. **Reflection non-blocking**: `ReflectionAgent.reflect_async()` spawns a `threading.Thread(daemon=True)` — never adds latency to the response path. Errors are silently swallowed.
15. **Reflection rate limit**: `_RateLimiter` (60s minimum interval per user) prevents LLM tier-2 from being called on every turn; tier-1 regex always runs regardless.
16. **Memory context placement**: UserMemory block is prepended to the LLM user message (before "Tình huống:"), not to the system prompt — keeps the strict 4-part system prompt intact.
17. **Graceful degradation for memory**: `orchestrator.__init__` wraps `UserMemoryStore()` init in try/except — if MongoDB is unavailable, `self._memory_store = None` and the pipeline runs without personalization.
18. **Prompt injection protection (Phase 13.1)**: All user-controlled memory fields pass through `_sanitize_field()` at both write time (`update_personal_info`) and read time (`get_context_for_prompt`). Blocks: control chars, ChatML/Llama format tokens, "ignore previous instructions" patterns, role-switch phrases.
19. **Structural memory delimiters**: `get_context_for_prompt()` wraps output in `--- THÔNG TIN CÁ NHÂN (hệ thống cung cấp, chỉ đọc) ---` delimiters. The `_SYSTEM_PROMPT` explicitly instructs the LLM to not execute any directives from that block.
20. **API input validation**: `PUT /recommendations/behavior/memory` enforces field limits via Pydantic `Field`: `name` ≤ 80 chars, `age` ∈ [10,100], `occupation`/`location` ≤ 100 chars, `notes` ≤ 500 chars.
21. **Defence-in-depth sanitization**: `ReflectionAgent` sanitizes regex-extracted values (tier-1) and LLM-extracted values (tier-2) before calling `update_personal_info`. `upsert_situation_summary` sanitizes LLM-generated summaries before MongoDB storage.
22. **PII log masking**: All reflection logger calls use `user_id[:8]` and log field *keys* only — never field values — to avoid name/age/occupation appearing in plaintext logs.

---

## SQLite Schema (StorageLayer)

```sql
CREATE TABLE documents (
  doc_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  filename TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  is_global INTEGER NOT NULL DEFAULT 0,   -- ★ Added Phase 12
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  metadata TEXT
);

CREATE TABLE jobs (
  job_id TEXT PRIMARY KEY,
  doc_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  checkpoint TEXT,
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

---

## Frontend State / localStorage Keys

| Key | Value | Used by |
|---|---|---|
| `lexai_user_id` | string user ID | `api.ts` — `getUserId()`, `X-User-ID` header |
| `lexai_admin_key` | admin API key | `adminAuth.ts` — `getAdminKey()`, `X-Admin-Key` header |
| `lexai_sessions` | JSON array (max 20) | `Analyze.tsx` — conversation history |
| `lexai_analysis_history` | JSON array (max 30) | `api.ts` — `saveAnalysis()`/`loadHistory()` — 8 analysis types: Timeline/EvidenceGap/ClauseCoach/ClauseSearch/SimilarCases/Actions/ComplianceRadar/RiskAnalysis |

---

## Running Locally

```bash
# Install deps
pip install -r requirements.txt

# Run backend API (use python -m uvicorn — Windows Anaconda env)
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8001 --reload

# Seed ALL built-in knowledge (run once after backend starts; idempotent — safe to re-run)
python scripts/seed_raw_data.py
# Step 1: calls POST /admin/seed → templates, TT55 forms, risks, checklists into MongoDB
# Step 2: uploads all raw_data/*.doc/.pdf → 8-stage pipeline → global chunks in MongoDB
# Add new .doc/.docx/.pdf files to raw_data/ then re-run to pick them up.
# Duplicate downloads "(1).doc" and dataset dirs are auto-excluded.
# Flags: --skip-metadata (step 1 only), --skip-files (step 2 only), --dry-run, --force

# Run frontend
cd "lexai-–-trợ-lý-pháp-lý-thông-minh UI"
npm install
npm run dev
# → http://localhost:3000
# → http://localhost:3000/admin/login  (key: lexai-admin-secret)
# → http://localhost:3000/history      (saved analysis history)
# API_BASE default: http://localhost:8001 (override with VITE_API_URL env var)
```

Environment variables (`.env`):
- `MONGO_URI` — MongoDB Atlas connection string
- `MONGO_DB` — database name (default: `legal_knowledge_assistant`)
- `OPENAI_API_KEY` — for LLM reasoning (optional; system falls back to deterministic)
- `ADMIN_API_KEY` — admin key (default: `lexai-admin-secret`)

## Data Architecture

```
raw_data/           ← admin places legal .doc/.pdf files here
    *.doc           ← Vietnamese laws, decrees, circulars
    VNLegalText-main/   ← annotation dataset (excluded from seed)
    bm25_legal_corpus/  ← BM25 corpus (excluded from seed)

scripts/seed_raw_data.py  ← uploads raw_data/*.doc to admin API as is_global=True
                           ← idempotent: skips filenames already in MongoDB
                           ← skips "(1).doc" duplicate downloads automatically

data/uploads/       ← auto-created; stores uploaded file bytes per doc_id
data/lka.db         ← SQLite: documents, jobs, chunks, graphs
MongoDB Atlas:
  law_chunks        ← embedded chunks with is_global=True (visible to all users)
  user_memory       ← per-user cross-session memory (no TTL)
  conversation_sessions ← 24h TTL session context
```

**Data isolation model:**
- Admin uploads (`raw_data/` via seed script) → `is_global=True` → visible to **all users**
- User uploads (via web UI) → `is_global=False` → visible **only to that user**
- Retrieval always queries: `{$or: [{user_id: <user>}, {is_global: true}]}`

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
| 11 | AI Legal Intelligence Infrastructure: staged pipeline, retrieval fusion, reranking, session memory, observability, behavior recommender |
| 12 | Admin Upload Infrastructure + Frontend Wiring: admin API, is_global mechanism, React admin panel, localStorage session persistence |
| 13 | Cross-Session User Memory + ReflectionAgent + Personalization UI: UserMemoryStore (no TTL), two-tier ReflectionAgent, orchestrator Stage 2b/5/7b patches, behavior/memory API, Profile personal-info panel, Header name greeting |
| 12.5 | New Feature Pages: ClauseCoach (backend + frontend), EvidenceGap (frontend), ClauseSearch (backend + frontend), Timeline (frontend), Standalone POST /recommendations/rank |
| 14 | Analysis History + Dashboard Real Data + Bug Fixes: AnalysisHistory page (/history), localStorage save/load helpers in api.ts, Save button on Timeline/EvidenceGap/ClauseCoach, Dashboard chart wired to real behavior profile API, API_BASE default fixed to :8001, vite-env.d.ts added, AdminStats type conflict fixed |
| 15 | Extended Save/History + Search + UX Improvements (current): AnalysisType extended to 8 types (similar_cases/action_plan/compliance_radar/risk_analysis), Save buttons on ClauseSearch/SimilarCases/Actions/ComplianceRadar, AnalysisHistory text search box, formatted per-type preview cards (no raw JSON), filter tabs auto-hide types with 0 items |
