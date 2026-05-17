# LexAI / ULKA — Standalone Build Prompt

> Paste this entire document into a new AI session to continue building the Universal Legal Knowledge Assistant.
> Last updated: 2026-05-17. Phase 12 — Admin Upload + Frontend Wiring.

---

## What This Project Is

A full-stack Vietnamese legal AI web application called **LexAI / ULKA** (Universal Legal Knowledge Assistant).

- **Backend**: Python 3.11 · FastAPI · MongoDB · sentence-transformers (384-dim) · OpenAI API
- **Frontend**: React 19 · TypeScript · Vite · Tailwind CSS · React Router v7
- **Working directory**: `c:\Users\Admin\OneDrive\Máy tính\Universal Legal Knowledge Assistant`
- **Frontend folder**: `lexai-–-trợ-lý-pháp-lý-thông-minh UI\` (inside the root)
- **Backend runs on**: `http://localhost:8000`
- **Frontend runs on**: `http://localhost:5173`
- **OS**: Windows 11 · PowerShell · Anaconda Python environment

---

## Architecture Overview

```
ADMIN (X-Admin-Key header)              USER (X-User-ID header)
    │                                        │
    ▼                                        ▼
POST /admin/documents/upload          POST /intelligence/analyze
    │                                  POST /recommendations/*
    ▼
8-stage pipeline (extract → chunk → embed)
    │
    ▼
MongoDB: {user_id: "admin", is_global: true, embedding: [...]}
    │
    ▼  (all user queries include)
    {$or: [{user_id: <current_user>}, {is_global: true}]}
```

### Backend Key Modules

| Module | Location | Role |
|--------|----------|------|
| FastAPI app | `src/api/app.py` | Registers all routers |
| Admin routes | `src/api/admin_routes.py` | `/admin/*` endpoints |
| Core routes | `src/api/routes.py` | Document upload, job status |
| Recommendation routes | `src/api/recommendation_routes.py` | All `/recommendations/*` and `/intelligence/*` |
| Admin auth | `src/api/deps.py` | `require_admin` dep (X-Admin-Key header) |
| SQLite storage | `src/runtime/storage.py` | Document/job metadata + `is_global` column |
| MongoDB storage | `src/mongodb/mongo_storage.py` | Vector search + `is_global` filter |
| Embedding stage | `src/pipeline/embedding_stage.py` | `embed_chunks_into_mongo(is_global=)` |
| Processor | `src/runtime/processor.py` | Auto-detects `is_global = user_id == "admin"` |
| 7-stage pipeline | `src/engine/orchestrator.py` | LegalIntelligenceOrchestrator |

### Frontend Key Files

| File | Role |
|------|------|
| `src/App.tsx` | Routes — `/admin/*` separate from user routes |
| `src/lib/api.ts` | API client — `adminFetch()`, `getUserId()`, all endpoints |
| `src/lib/adminAuth.ts` | `getAdminKey/setAdminKey/isAdminAuthenticated` via localStorage |
| `src/components/admin/AdminLayout.tsx` | Admin shell with auth guard + Outlet |
| `src/pages/admin/AdminLogin.tsx` | Admin key login page |
| `src/pages/admin/AdminDocuments.tsx` | Upload + document management table |
| `src/pages/admin/AdminJobs.tsx` | Job history with polling |
| `src/pages/admin/AdminStats.tsx` | Stats cards + Recharts charts |
| `src/pages/Analyze.tsx` | Legal analysis chat — sessions in localStorage |

---

## What Has Been Built (Complete)

### Phase 12 Backend
- [x] `src/api/admin_routes.py` — full admin CRUD + upload + stats
- [x] `src/api/deps.py` — `require_admin` dependency (X-Admin-Key)
- [x] `src/runtime/storage.py` — `is_global` column, `create_global_document()`, `get_all_documents()`, `list_all_jobs()`
- [x] `src/mongodb/mongo_storage.py` — `is_global` in `upsert_chunk_vector`, `{$or}` filter in searches, `delete_chunks_by_doc()`, `get_stats()`
- [x] `src/pipeline/embedding_stage.py` — `is_global` param propagated
- [x] `src/runtime/processor.py` — `is_global = user_id == "admin"` auto-detection
- [x] `src/api/routes.py` — `/documents/upload-file` multipart endpoint
- [x] `src/api/app.py` — `admin_router` registered

### Phase 12 Frontend
- [x] `src/lib/adminAuth.ts` — localStorage admin key utils
- [x] `src/lib/api.ts` — adminFetch, dynamic user ID, all admin endpoint functions
- [x] `src/components/admin/AdminLayout.tsx` — admin shell + auth guard
- [x] `src/pages/admin/AdminLogin.tsx` — login form
- [x] `src/pages/admin/AdminDashboard.tsx` — quick links
- [x] `src/pages/admin/AdminDocuments.tsx` — upload + management table
- [x] `src/pages/admin/AdminJobs.tsx` — jobs table with polling
- [x] `src/pages/admin/AdminStats.tsx` — stats + Recharts
- [x] `src/App.tsx` — admin routes wired
- [x] `src/pages/Analyze.tsx` — hardcoded sessions removed, localStorage-backed

---

## What Still Needs to Be Done

### Immediate (verify + seed data)
1. **Test the full stack** — start backend + frontend, navigate to `/admin/login`, upload a `.doc` file, confirm job completes, confirm `/intelligence/analyze` returns results
2. **Seed raw data** — 6 `.doc` files exist in `raw_data/` folder. Upload them via admin panel or build `scripts/seed_raw_data.py`

### Known issues to investigate
- MongoDB `$vectorSearch` requires Atlas Search index to be configured — if using local MongoDB, fall back to `$search` or regular query
- `sentence-transformers` model `paraphrase-multilingual-MiniLM-L12-v2` downloads on first run — ensure internet access or pre-cache
- Windows Anaconda: always use `python -m uvicorn` not `uvicorn` directly

### Phase 13 candidates
- **Evaluation harness**: offline eval with Vietnamese legal QA pairs
- **Deployment**: Dockerfile + docker-compose wiring both backend and frontend
- **User auth**: replace demo `X-User-ID` header with real JWT auth
- **Document viewer**: in-app PDF/DOCX preview in Documents page
- **Export**: PDF export of analysis results
- **Admin bulk seed script**: `scripts/seed_raw_data.py` — POST all `raw_data/*.doc` files to `/admin/documents/upload`

---

## Running the Project

```powershell
# Terminal 1 — Backend
cd "c:\Users\Admin\OneDrive\Máy tính\Universal Legal Knowledge Assistant"
docker compose up -d          # start MongoDB
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd "c:\Users\Admin\OneDrive\Máy tính\Universal Legal Knowledge Assistant\lexai-–-trợ-lý-pháp-lý-thông-minh UI"
npm run dev
```

URLs:
- User app: `http://localhost:5173`
- Admin panel: `http://localhost:5173/admin/login` → key: `lexai-admin-secret`
- API docs: `http://localhost:8000/docs`

Environment variables (create `.env` in project root):
```
MONGODB_URI=mongodb://localhost:27017
OPENAI_API_KEY=sk-...       # optional — system falls back to deterministic
ADMIN_API_KEY=lexai-admin-secret
```

---

## Admin API Quick Reference

```bash
# Upload document (multipart)
curl -X POST http://localhost:8000/admin/documents/upload \
  -H "X-Admin-Key: lexai-admin-secret" \
  -F "files=@raw_data/85_2025_QH15_651570.doc"

# List all documents
curl http://localhost:8000/admin/documents -H "X-Admin-Key: lexai-admin-secret"

# Check jobs
curl http://localhost:8000/admin/jobs -H "X-Admin-Key: lexai-admin-secret"

# System stats
curl http://localhost:8000/admin/stats -H "X-Admin-Key: lexai-admin-secret"

# Delete a document
curl -X DELETE http://localhost:8000/admin/documents/{doc_id} \
  -H "X-Admin-Key: lexai-admin-secret"
```

---

## User API Quick Reference

```bash
# Analyze a legal situation (all headers required)
curl -X POST http://localhost:8000/intelligence/analyze \
  -H "Content-Type: application/json" \
  -H "X-User-ID: demo_user_001" \
  -d '{"query": "tôi bị chủ nhà đơn phương chấm dứt hợp đồng thuê", "session_id": "sess_001"}'

# Get document recommendations
curl -X POST http://localhost:8000/recommendations/situation \
  -H "Content-Type: application/json" \
  -H "X-User-ID: demo_user_001" \
  -d '{"situation": "tranh chấp đất đai", "user_role": "bị đơn"}'
```

---

## Key Implementation Details

### is_global Mechanism
Admin-uploaded documents are globally visible to all users via a two-part convention:
1. Admin uploads create `user_id="admin"` in SQLite
2. `build_document_processor()` in `processor.py` detects `is_global = (user_id == "admin")`
3. `embed_chunks_into_mongo(..., is_global=True)` saves `is_global: true` in each MongoDB chunk
4. All search queries use `{$or: [{"user_id": user_id}, {"is_global": True}]}` as filter

### Admin Auth
- `src/api/deps.py`: `require_admin` dependency reads `X-Admin-Key` header
- Key stored in env `ADMIN_API_KEY`, default `"lexai-admin-secret"`
- Frontend: `src/lib/adminAuth.ts` wraps localStorage key `lexai_admin_key`
- `src/lib/api.ts`: `adminFetch()` adds `X-Admin-Key` header automatically

### Frontend Routing Split
`App.tsx` uses `useLocation()`:
- If `pathname.startsWith('/admin')` → renders `<AdminLayout>` tree (separate Sidebar + Header)
- Otherwise → renders user layout (Sidebar + Header + bottom mobile nav)

### Session History (Analyze.tsx)
- Removed hardcoded mock sessions
- Sessions stored in `localStorage['lexai_sessions']` as JSON array
- Max 20 sessions kept (oldest removed)
- Sessions auto-populated after each successful `/intelligence/analyze` call

---

## File Structure (relevant parts)

```
Universal Legal Knowledge Assistant/
├── CLAUDE.md                          # Auto-loaded project instructions
├── BUILD_PROMPT.md                    # This file
├── src/
│   ├── api/
│   │   ├── app.py
│   │   ├── admin_routes.py            # ★ Phase 12 new
│   │   ├── routes.py
│   │   ├── recommendation_routes.py
│   │   ├── deps.py                    # ★ require_admin added
│   │   └── models.py
│   ├── runtime/
│   │   ├── storage.py                 # ★ is_global column
│   │   └── processor.py               # ★ auto-detects is_global
│   ├── mongodb/
│   │   └── mongo_storage.py           # ★ is_global + {$or} filter
│   └── pipeline/
│       └── embedding_stage.py         # ★ is_global param
├── raw_data/                          # 6 Vietnamese law .doc files to seed
│   ├── 45_2019_QH14_333670 (1).doc
│   ├── 85_2025_QH15_651570.doc
│   ├── 86_2025_QH15_662377.doc
│   ├── 92_2015_QH13_296861.doc
│   ├── 99_2025_QH15_662829.doc
│   └── Khongso_215627.doc
└── lexai-–-trợ-lý-pháp-lý-thông-minh UI/
    └── src/
        ├── App.tsx                    # ★ admin routes added
        ├── lib/
        │   ├── api.ts                 # ★ adminFetch, dynamic user ID
        │   └── adminAuth.ts           # ★ Phase 12 new
        ├── components/admin/
        │   └── AdminLayout.tsx        # ★ Phase 12 new
        └── pages/
            ├── Analyze.tsx            # ★ localStorage sessions
            └── admin/
                ├── AdminLogin.tsx     # ★ Phase 12 new
                ├── AdminDashboard.tsx # ★ Phase 12 new
                ├── AdminDocuments.tsx # ★ Phase 12 new
                ├── AdminJobs.tsx      # ★ Phase 12 new
                └── AdminStats.tsx     # ★ Phase 12 new
```
