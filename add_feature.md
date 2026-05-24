# LexAI / ULKA — Nhật ký triển khai tính năng

> Ghi lại những gì đã được implement thực tế vào repo, tính đến **2026-05-24**.
> Phase hiện tại: **Phase 13** — Cross-Session User Memory + ReflectionAgent + Personalization UI

---

## Tổng quan trạng thái

| # | Tính năng | Backend | Frontend | Ghi chú |
|---|---|---|---|---|
| 1 | Legal Situation Classifier | ✅ | — | `src/services/situation_classifier.py` |
| 2 | 7-Stage Intelligence Pipeline | ✅ | — | `src/engine/orchestrator.py` |
| 3 | Legal Retrieval Engine (vector + BM25 + graph + behavior) | ✅ | ✅ | `LawSearch.tsx` |
| 4 | Similar Case Explorer | ✅ | ✅ | `SimilarCases.tsx` |
| 5 | Clause Similarity Search | ✅ | ✅ | `ClauseSearch.tsx` |
| 6 | Evidence Gap Detector | ✅ | ✅ | `EvidenceGap.tsx` |
| 7 | Legal Action Planner | ✅ | ✅ | `Actions.tsx` |
| 8 | Risk Analysis Engine | ✅ | ✅ | `Risks.tsx` |
| 9 | Behavioral Recommender | ✅ | — | `src/recommenders/behavior_recommender.py` |
| 10 | Recommendation Ranker (6-signal) | ✅ | — | `src/engine/recommendation_ranker.py` |
| 11 | Standalone Rank API | ✅ | — | `POST /recommendations/rank` |
| 12 | Legal Timeline Tracker | ✅ | ✅ | `Timeline.tsx` |
| 13 | Contract Clause Coach | ✅ | ✅ | `ClauseCoach.tsx` |
| 14 | Compliance Radar | ✅ | ✅ | `ComplianceRadar.tsx` |
| 15 | GraphRAG Context Retriever | ✅ | — | `src/graphrag/` |
| 16 | Reasoning Trace Generator | ✅ | — | `src/engine/reasoning_trace.py` |
| 17 | Session Memory (24h TTL) | ✅ | — | `src/memory/session_store.py` |
| 18 | Cross-Session User Memory (no TTL) | ✅ | ✅ | `Profile.tsx` — "AI ghi nhớ về bạn" |
| 19 | ReflectionAgent (2-tier extraction) | ✅ | — | `src/memory/reflection_agent.py` |
| 20 | Admin Upload Infrastructure | ✅ | ✅ | `/admin/*` — is_global docs |
| 21 | Legal Journey Mode | ✅ | ✅ | `Journey.tsx` |
| 22 | Contract Analysis | ✅ | ✅ | `Contract.tsx` |
| 23 | Template Recommender | ✅ | ✅ | `Templates.tsx` |
| 24 | Checklist Recommender | ✅ | ✅ | `Checklists.tsx` |

---

## Chi tiết theo từng phase

---

### Phase 1–4 — Document Ingestion Pipeline

**Mục tiêu:** Ingest văn bản pháp lý từ PDF/DOCX/HTML → chunk → embed → lưu MongoDB.

**Đã làm:**
- `src/pipeline/extractor.py` — Stage 1: trích text từ PDF, DOCX, DOC, HTML (python-docx, pdfplumber, BeautifulSoup)
- `src/pipeline/profiler.py` — Stage 2: phát hiện layout (TOC, bảng, danh sách)
- `src/pipeline/cleaner.py` — Stage 3: chuẩn hóa OCR, sửa lỗi dấu tiếng Việt, loại bỏ nhiễu
- `src/pipeline/structurer.py` — Stage 4: canonical schema (title, articles, sections, metadata)
- `src/pipeline/chunker.py` — Stage 5: legal chunking theo điều/khoản/mục, overlap 50 chars
- `src/pipeline/graph_builder.py` — Stage 6: xây graph nodes/edges (CITES, AMENDS, REQUIRES...)
- `src/pipeline/retrieval_stage.py` — Stage 7: index chunk vào MongoDB `law_chunks`
- `src/pipeline/embedding_stage.py` — embed text → 384-dim vector (sentence-transformers), `is_global` param

**Collections tạo ra:**
- `law_chunks` — `{ chunk_id, doc_id, user_id, is_global, content, law_reference, embedding[], law_type }`
- `legal_cases` — `{ case_id, title, situation_summary, outcome, key_laws, embedding[] }`

---

### Phase 5–8 — Retrieval + GraphRAG + Reasoning

**Đã làm:**
- `src/mongodb/mongo_storage.py` — `VectorStorage` class: tất cả MongoDB operations
  - `vector_search_chunks()` — `$vectorSearch` 384-dim cosine, filter `{$or: [user_id, is_global]}`
  - `vector_search_cases()` — similar case retrieval
  - `vector_search_similar_clauses()` — clause similarity search
  - `keyword_search_chunks()`, `keyword_search_cases()` — BM25-like fallback
- `src/graphrag/traversal.py` — BFS graph traversal, edge weight decay 0.10/level
- `src/graphrag/evidence_bundle.py` — EvidenceBundle từ graph nodes
- `src/graphrag/reasoning.py` — legal reasoning chains
- `src/retrieval/retrieval_engine.py` — legacy retrieval engine
- `src/llm/client.py` — OpenAI wrapper, `is_available()` check

---

### Phase 9 — Action Engine

**Đã làm:**
- `src/actions/action_engine.py` — dispatch: draft, compare, assess
- `src/actions/action_schema.py` — action type definitions
- `src/actions/workflows.py` — multi-step action workflows

**API:**
- `POST /agent/analyze` — full agentic analysis
- `POST /agent/contract` — contract clause analysis

---

### Phase 10 — Product Runtime

**Đã làm:**
- `src/runtime/storage.py` — SQLite `StorageLayer`: documents + jobs tables, `is_global` column
- `src/runtime/job_runner.py` — background job queue `JobRunner`
- `src/runtime/auth.py`, `src/runtime/audit.py` — auth + audit layers
- `src/api/routes.py` — document upload/list/status endpoints
- `src/api/app.py` — FastAPI factory, registers all routers, MongoDB init on startup

**Endpoints:**
```
POST /documents/upload-file    multipart upload (users)
GET  /documents                list user docs
GET  /documents/{id}/status    job status
```

---

### Phase 11 — AI Legal Intelligence Infrastructure

**Đây là phase lớn nhất. Đã làm:**

#### Backend engine

- `src/engine/query_planner.py` — Stage 1: deterministic domain/entity/strategy, <10ms, no LLM
- `src/engine/retrieval_fusion.py` — Stage 3: hybrid vector(0.45) + BM25(0.20) + graph(0.25) + behavior(0.10)
  - `FusedResult`, `FusedResultSet` dataclasses
  - min-max normalize → weighted sum
- `src/engine/recommendation_ranker.py` — Stage 6: 6-signal reranking
  - semantic(0.35), behavior(0.15), graph(0.20), freshness(0.15), popularity(0.10), accepted(0.05)
  - `_freshness_score()`: `exp(-ln(2)/180 * days)`, half-life 180 ngày
  - `RankedItem`, `RankingResult` dataclasses, Vietnamese explanation per item
- `src/engine/orchestrator.py` — `LegalIntelligenceOrchestrator` kết nối 7 stages
- `src/engine/reasoning_trace.py` — `StageTrace`, `ReasoningTrace`, `TraceBuilder`

#### Recommenders

- `src/recommenders/situation_analyzer.py` — vector-based situation analysis
- `src/recommenders/document_recommender.py` — hybrid vector + collab filter docs
- `src/recommenders/behavior_recommender.py` — collaborative filter + bigram pattern mining
  - `recommend_proactive()`, `recommend_next_action()`, `recommend_from_peers()`
  - `get_daily_digest()` — dashboard widget
- `src/recommenders/template_recommender.py` — contract template suggestions
- `src/recommenders/risk_recommender.py` — legal risk recommendations
- `src/recommenders/checklist_recommender.py` — compliance checklists

#### Services (deterministic, <30ms, no LLM)

- `src/services/situation_classifier.py` — `SituationClassifier`, `SituationProfile`
  - detect domain, stage, urgency, user_role từ keyword scoring
- `src/services/risk_analysis_service.py` — đánh giá điểm rủi ro, mạnh/yếu
- `src/services/compliance_service.py` — `ComplianceService.analyze()`, checklist tuân thủ
- `src/services/timeline_service.py` — `TimelineService.analyze()`: stage + deadlines + alerts
- `src/services/evidence_gap_service.py` — `EvidenceGapService.analyze()`: missing evidence by category
- `src/services/clause_coach_service.py` — **[Phase 12.5]** `ClauseCoachService.analyze()`
  - 10 risk patterns: unilateral termination, unlimited liability, excessive penalty, vague scope...
  - `ClauseRisk`, `SaferVersion`, `MissingClause`, `ClauseCoachResult` dataclasses

#### API endpoints

```
POST /recommendations/situation        luật liên quan theo tình huống
POST /recommendations/cases            similar cases
POST /recommendations/documents        hybrid doc recommendations
POST /recommendations/templates        template suggestions
POST /recommendations/risks            risk recommendations
POST /recommendations/checklists       compliance checklists
POST /recommendations/rank             standalone 6-signal reranker ← [Phase 13.5]
GET  /recommendations/behavior/profile user behavior profile
GET  /recommendations/behavior/proactive proactive recommendations
POST /recommendations/behavior/next-action next-action prediction
GET  /recommendations/behavior/peers   peer trending
GET  /recommendations/behavior/digest  daily digest
POST /interactions/log                 log interaction events
POST /intelligence/analyze             full 7-stage pipeline
GET  /intelligence/trace/{trace_id}   reasoning trace
GET  /intelligence/session/{session_id} conversation history
```

#### Observability

- `src/observability/tracer.py` — `ExecutionTracer` singleton, structured JSON logs
  - `log_ranking()`, `log_retrieval()`, `log_stage_timing()`

---

### Phase 12 — Admin Upload Infrastructure

**Đã làm:**

#### Backend

- `src/api/admin_routes.py` — `admin_router` prefix `/admin`, `require_admin` dep
  - `POST /admin/documents/upload` — multipart, multiple files, creates global docs
  - `GET /admin/documents` — all docs across all users
  - `DELETE /admin/documents/{id}` — xóa doc + MongoDB chunks + disk
  - `POST /admin/documents/{id}/reprocess` — re-queue job
  - `GET /admin/jobs` — job history
  - `GET /admin/stats` — collection counts, job stats
- `src/api/deps.py` — `require_user` + `require_admin` FastAPI dependencies
- `src/runtime/processor.py` — `build_document_processor()`, auto-detect `is_global = (user_id == "admin")`
- `src/pipeline/embedding_stage.py` — `embed_chunks_into_mongo(..., is_global=True)` param added
- `src/mongodb/seed_data.py` — seed templates/risks/checklists (idempotent)
- `scripts/seed_raw_data.py` — upload `raw_data/*.doc/.pdf` → admin API → global chunks

**is_global convention:**
```python
user_id == "admin"  →  is_global = True  (visible to all users)
else                →  is_global = False (visible only to that user)
# All queries: {$or: [{user_id: <user>}, {is_global: true}]}
```

#### Frontend Admin Panel

- `AdminLayout.tsx` — admin shell, auth guard, sidebar
- `AdminLogin.tsx` — key login form (`lexai-admin-secret`)
- `AdminDashboard.tsx` — quick links
- `AdminDocuments.tsx` — upload + document table
- `AdminJobs.tsx` — job history với polling
- `AdminStats.tsx` — stats cards + Recharts charts
- Route: `/admin/*` → `AdminLayout` (hoàn toàn tách khỏi user layout)

#### Frontend User

- `LawSearch.tsx` — tra cứu điều luật, vector search + domain filter
- `SimilarCases.tsx` — tìm vụ việc tương tự
- localStorage session persistence cho `Analyze.tsx` (max 20 sessions)

---

### Phase 13 — Cross-Session User Memory + ReflectionAgent + Personalization UI

**Đã làm:**

#### Backend Memory

- `src/mongodb/mongo_storage.py` — `user_memory` collection (no TTL), `vector_search_similar_clauses()`
- `src/memory/user_memory_store.py` — `UserMemoryStore`
  - `PersonalInfo` dataclass: name, age, occupation, location, notes
  - `SituationRecord` dataclass: session_id, date, domain, summary, resolved
  - `get()`, `update_personal_info()`, `upsert_situation_summary()`, `mark_situation_resolved()`
  - `get_context_for_prompt()` — format block cho LLM message
- `src/memory/reflection_agent.py` — `ReflectionAgent`
  - Tier 1 (regex, <1ms, always): extract name/age/occupation/location
  - Tier 2 (LLM, rate-limited 1 call/60s/user, if domain≠general): JSON → personal_info + situation_summary
  - `reflect_async()` — daemon thread, không block response
  - `_sanitize_field()` — chống prompt injection (ChatML tokens, "ignore previous instructions"...)
- `src/engine/orchestrator.py` — thêm Stage 2b (load UserMemory) + Stage 7b (reflect_async)

#### Backend Prompt Injection Protection (Phase 13.1)

- `_sanitize_field()` block: control chars, ChatML/Llama format tokens, role-switch phrases
- Memory delimiters: `--- THÔNG TIN CÁ NHÂN (hệ thống cung cấp, chỉ đọc) ---`
- System prompt instructs LLM not to execute directives from memory block
- `PUT /recommendations/behavior/memory` — Pydantic Field limits: name≤80, age∈[10,100], notes≤500

#### API Memory Endpoints

```
GET /recommendations/behavior/memory    → PersonalInfo + SituationRecords
PUT /recommendations/behavior/memory    → update PersonalInfo fields
```

#### Frontend

- `Profile.tsx` — "AI ghi nhớ về bạn" card: PersonalInfo 2-col grid, edit panel, situation summaries
- `Header.tsx` — personalized greeting nếu có `personal_info.name`
- `lib/api.ts` — `getUserMemory()`, `updateUserMemory()`, `UserMemory`/`UserMemoryInfo` types

---

### Phase 12.5 / 13.5 — New Feature Pages

*Implement xen kẽ giữa Phase 12 và 13. Tất cả services là deterministic (<30ms, no LLM).*

#### Contract Clause Coach

**Backend:**
- `src/services/clause_coach_service.py`
  - 10 risk patterns: r01 unilateral_termination (high), r02 unlimited_liability (critical), r03 excessive_penalty (high), r04 vague_scope (medium), r05 unlimited_confidentiality (medium), r06 one_sided_ip (high), r07 unlimited_auto_renewal (medium), r08 unclear_governing_law (low), r09 broad_noncompete (high), r10 payment_100_completion (medium)
  - Missing clause templates theo clause type
  - Risk score: `sum(severity_weights) + missing_penalty * 0.5`, capped 100
  - Risk levels: critical≥70, high≥45, medium≥20, else low
- `src/api/contract_coach_routes.py` — `coach_router` prefix `/contracts`
  - `POST /contracts/coach` — nhận clause_text + contract_type → `ClauseCoachResult`
- `src/api/app.py` — `app.include_router(coach_router)`

**Frontend:**
- `ClauseCoach.tsx` — SVG risk ring, RiskCard (expandable + SaferVersion gold box), MissingCard
- `lib/api.ts` — `analyzeClause()`, `ClauseCoachResult`, `ClauseRisk`, `SaferVersion`, `MissingClause` types

#### Clause Similarity Search

**Backend:**
- `src/api/retrieval_routes.py` — `POST /retrieval/clauses`
  - embed → `vs.vector_search_similar_clauses(embedding, clause_type, risk_level, limit)`
  - fallback: retry without filters nếu <2 results
  - keyword fallback: `keyword_search_chunks` → wrap as clause items

**Frontend:**
- `ClauseSearch.tsx` — SimilarityBar, ClauseCard expandable, 10 clause types + 6 risk levels filter
- `lib/api.ts` — `searchSimilarClauses()`, `ClauseSearchResult`, `ClauseItem` types

#### Evidence Gap

**Frontend** (backend đã có từ trước):
- `EvidenceGap.tsx` — CoverageBar, EvidenceRow theo priority, EvidenceStrengthSection collapsible
- Grouped by category, facts nhập mỗi dòng 1 mục

#### Legal Timeline Tracker

**Frontend** (backend đã có từ trước):
- `Timeline.tsx` — ProgressBar colored by %, DeadlineCard với urgency colors (≤7 red, ≤30 orange, ≤90 yellow)
- STAGE_COLORS map, SAMPLE_SITUATIONS 4 mẫu

#### Standalone Recommendation Ranker

**Backend:**
- `src/api/recommendation_routes.py` — `POST /recommendations/rank`
  - Input: list `RankCandidateIn` (item_id, vector_score, behavior_score, graph_score, updated_at)
  - Convert → `FusedResultSet` → `RecommendationRanker(vs).rank()`
  - Output: `RankResponse` với final_score, rank, explanation (VI), score_components breakdown

#### Sidebar + Routing

- `Sidebar.tsx` — thêm 4 menu items: Timeline (Clock), Kiểm tra chứng cứ (FileSearch), Tư vấn điều khoản (Gavel), Tìm điều khoản (FileSearch)
- `App.tsx` — thêm 4 routes: `/timeline`, `/evidence-gap`, `/clause-coach`, `/clause-search`

---

## Cấu trúc file quan trọng

### Backend (`src/`)

```
src/
├── api/
│   ├── app.py                   FastAPI factory, registers all routers
│   ├── routes.py                document upload/list/status
│   ├── admin_routes.py          /admin/* (require_admin)
│   ├── recommendation_routes.py /recommendations/*, /intelligence/*, /interactions/*, /agent/*
│   ├── retrieval_routes.py      /retrieval/laws, /similar-cases, /clauses
│   ├── analysis_routes.py       /analysis/evidence-gap, /timeline, /compliance
│   ├── contract_coach_routes.py /contracts/coach
│   └── deps.py                  require_user, require_admin
│
├── engine/
│   ├── orchestrator.py          7-stage pipeline coordinator
│   ├── query_planner.py         Stage 1 — deterministic, <10ms
│   ├── retrieval_fusion.py      Stage 3 — 4-signal fusion
│   ├── recommendation_ranker.py Stage 6 — 6-signal reranking
│   └── reasoning_trace.py       trace builder
│
├── memory/
│   ├── session_store.py         24h TTL MongoDB sessions
│   ├── user_memory_store.py     Permanent cross-session memory
│   └── reflection_agent.py      2-tier extraction daemon
│
├── services/
│   ├── situation_classifier.py
│   ├── timeline_service.py
│   ├── evidence_gap_service.py
│   ├── compliance_service.py
│   ├── risk_analysis_service.py
│   └── clause_coach_service.py
│
├── recommenders/
│   ├── behavior_recommender.py
│   ├── situation_analyzer.py
│   ├── document_recommender.py
│   ├── template_recommender.py
│   ├── risk_recommender.py
│   └── checklist_recommender.py
│
├── graphrag/
│   ├── traversal.py             BFS + edge weights
│   ├── evidence_bundle.py
│   ├── reasoning.py
│   ├── legal_ontology.py
│   └── query_intent.py
│
├── pipeline/
│   ├── extractor.py             PDF/DOCX/HTML extraction
│   ├── cleaner.py               OCR cleanup
│   ├── structurer.py            canonical schema
│   ├── chunker.py               legal chunking
│   ├── graph_builder.py         graph construction
│   └── embedding_stage.py       embed → MongoDB
│
├── mongodb/
│   ├── client.py                get_db(), ping()
│   ├── mongo_storage.py         VectorStorage — all MongoDB ops
│   └── seed_data.py             seed templates/risks/checklists
│
└── runtime/
    ├── storage.py               SQLite: documents + jobs
    ├── job_runner.py            background job queue
    └── processor.py             build_document_processor()
```

### Frontend (`lexai-.../src/`)

```
src/
├── lib/
│   ├── api.ts        API client, all types, all fetch functions
│   └── adminAuth.ts  admin key management
│
├── components/layout/
│   ├── Sidebar.tsx   17 menu items
│   └── Header.tsx    personalized greeting
│
├── pages/
│   ├── Dashboard.tsx
│   ├── Analyze.tsx         chat + localStorage sessions
│   ├── Journey.tsx         legal journey mode
│   ├── Actions.tsx         action planner
│   ├── LawSearch.tsx       law retrieval
│   ├── SimilarCases.tsx    similar case explorer
│   ├── Contract.tsx        contract analysis
│   ├── ClauseCoach.tsx     ← NEW clause coach
│   ├── ClauseSearch.tsx    ← NEW clause similarity search
│   ├── EvidenceGap.tsx     ← NEW evidence gap detector
│   ├── Timeline.tsx        ← NEW timeline tracker
│   ├── ComplianceRadar.tsx compliance radar
│   ├── Documents.tsx
│   ├── Templates.tsx
│   ├── Risks.tsx
│   ├── Checklists.tsx
│   └── Profile.tsx         "AI ghi nhớ về bạn"
│
└── pages/admin/
    ├── AdminLogin.tsx
    ├── AdminDashboard.tsx
    ├── AdminDocuments.tsx
    ├── AdminJobs.tsx
    └── AdminStats.tsx
```

---

## API Endpoints toàn bộ

### Admin (X-Admin-Key header)
| Method | Path | Mô tả |
|---|---|---|
| POST | `/admin/documents/upload` | Upload files → global docs |
| GET | `/admin/documents` | Tất cả documents |
| DELETE | `/admin/documents/{id}` | Xóa doc |
| POST | `/admin/documents/{id}/reprocess` | Re-queue job |
| GET | `/admin/jobs` | Tất cả jobs |
| GET | `/admin/stats` | System statistics |

### Intelligence (7-stage pipeline)
| Method | Path | Mô tả |
|---|---|---|
| POST | `/intelligence/analyze` | Full pipeline → IntelligenceOut |
| GET | `/intelligence/trace/{id}` | Reasoning trace |
| GET | `/intelligence/session/{id}` | Conversation history |

### Retrieval
| Method | Path | Mô tả |
|---|---|---|
| POST | `/retrieval/laws` | Tìm điều luật (vector + keyword fallback) |
| POST | `/retrieval/similar-cases` | Tìm vụ việc tương tự |
| POST | `/retrieval/clauses` | Tìm điều khoản tương tự |

### Analysis
| Method | Path | Mô tả |
|---|---|---|
| POST | `/analysis/evidence-gap` | Phát hiện thiếu chứng cứ |
| POST | `/analysis/timeline` | Timeline + deadlines |
| POST | `/analysis/compliance` | Compliance checklist |

### Contracts
| Method | Path | Mô tả |
|---|---|---|
| POST | `/contracts/coach` | Phân tích + gợi ý điều khoản |

### Recommendations
| Method | Path | Mô tả |
|---|---|---|
| POST | `/recommendations/situation` | Luật theo tình huống |
| POST | `/recommendations/cases` | Similar cases |
| POST | `/recommendations/documents` | Hybrid doc rec |
| POST | `/recommendations/templates` | Template suggestions |
| POST | `/recommendations/risks` | Risk recommendations |
| POST | `/recommendations/checklists` | Compliance checklists |
| POST | `/recommendations/rank` | Standalone 6-signal ranker |

### Behavior
| Method | Path | Mô tả |
|---|---|---|
| GET | `/recommendations/behavior/profile` | User behavior profile |
| GET | `/recommendations/behavior/proactive` | Proactive recommendations |
| POST | `/recommendations/behavior/next-action` | Next-action prediction |
| GET | `/recommendations/behavior/peers` | Peer trending |
| GET | `/recommendations/behavior/digest` | Daily digest |
| GET | `/recommendations/behavior/memory` | Cross-session memory |
| PUT | `/recommendations/behavior/memory` | Update PersonalInfo |

### Documents & Interactions
| Method | Path | Mô tả |
|---|---|---|
| POST | `/documents/upload-file` | User upload |
| GET | `/documents` | User's docs |
| GET | `/documents/{id}/status` | Job status |
| POST | `/interactions/log` | Log interaction event |

---

## MongoDB Collections

| Collection | Mô tả | TTL |
|---|---|---|
| `law_chunks` | Chunks + 384-dim embeddings + `is_global` | — |
| `legal_cases` | Case law + embeddings | — |
| `contract_clauses` | Contract clauses + risk labels | — |
| `interactions` | User interaction events | — |
| `conversation_sessions` | Multi-turn session context | 24h |
| `reasoning_traces` | Per-query reasoning traces | — |
| `session_context` | Retrieval cache | 24h |
| `user_memory` | Permanent PersonalInfo + SituationRecords | **none** |

---

## Cách chạy local

```bash
# Backend
pip install -r requirements.txt
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8001 --reload

# Seed data (chạy 1 lần sau khi backend start)
python scripts/seed_raw_data.py

# Frontend
cd "lexai-–-trợ-lý-pháp-lý-thông-minh UI"
npm install
npm run dev
# → http://localhost:3000
# → http://localhost:3000/admin/login  (key: lexai-admin-secret)
```

**Environment variables** (`.env`):
- `MONGO_URI` — MongoDB Atlas connection string
- `MONGO_DB` — database name (default: `legal_knowledge_assistant`)
- `OPENAI_API_KEY` — optional; fallback to deterministic nếu không có
- `ADMIN_API_KEY` — default: `lexai-admin-secret`
