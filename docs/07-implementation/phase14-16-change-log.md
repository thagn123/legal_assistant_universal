# Phase 14-16 Change Log

Date: 2026-05-24

This document records the implementation work completed after reviewing the existing repository documentation and current phase state. The repository had already progressed beyond the original Phase 0-10 roadmap; `add_feature.md` indicated Phase 13/13.5, and the codebase already contained early Phase 14 functionality. The work below stabilizes Phase 14 and continues through Phase 15 and Phase 16.

## Starting Point

Key documents reviewed:
- `README.md`
- `add_feature.md`
- `MULTILINGUAL_UPGRADE_LOG.md`
- `docs/00-overview/repository-state.md`
- `docs/07-implementation/implementation-roadmap.md`
- `docs/07-implementation/development-pipeline.md`
- `docs/ai/implementation-readiness-review.md`
- Phase tests under `tests/api`, `tests/runtime`, `tests/graphrag`, and `tests/actions`

Important finding:
- Original roadmap says Phase 1 should be next, but the codebase already includes Phase 8-13/13.5 features.
- Phase 14 was partially present in code and frontend comments.
- Existing backend tests initially failed because auth fallback broke tenant isolation for API-key-based tests.

## Phase 14: Product Surface Stabilization

### Goal

Make document viewer, evidence upload, checklist progress, and reasoning trace surfaces testable and safe.

### Backend Changes

#### `src/api/deps.py`

Added proper identity resolution:
- `X-API-Key` is verified through `AuthLayer` and maps to the stored tenant `user_id`.
- `X-User-ID` remains supported for browser/demo flows.
- Missing identity can still fall back to `demo_user_001` when demo auth is enabled.
- Added `require_explicit_user()` for routes that must not silently fall back to demo identity.

Why:
- API tests were failing because requests using different API keys were all being treated as the same demo user.
- This broke tenant isolation for documents, jobs, and audit records.

#### `src/api/routes.py`

Changed these routes to require explicit identity:
- `POST /queries`
- `POST /actions`
- `GET /audit`

Also updated session evidence upload:
- `POST /sessions/{session_id}/evidence` now receives `Request`.
- It can use an injected `app.state.session_store` in tests.
- If no injected store exists, it falls back to `SessionStore()`.

Why:
- Query/action/audit are sensitive operations and should not silently run as a demo user.
- Evidence upload needed to be testable without MongoDB.

#### `src/api/app.py`

Changed MongoDB startup behavior:
- If a deterministic `bundle_provider` is injected, MongoDB startup is skipped.

Why:
- In-process API tests should stay fast and isolated.
- Tests had been attempting MongoDB connection and vector index setup even when they did not need it.

### Tests Added

#### `tests/api/test_phase14_api.py`

Added coverage for:
- document content returns extracted chunks
- cross-tenant document content is blocked
- global document content is visible to normal users
- original file download serves bytes from registered upload path
- session evidence upload extracts and attaches text
- unsupported evidence file types are rejected
- checklist progress round-trips per user/checklist
- checklist progress works through SQLite fallback when vector storage is unavailable

### Documentation Added

#### `docs/07-implementation/phase14-progress.md`

Documents:
- Phase 14 scope
- implemented backend endpoints
- auth stabilization
- regression coverage
- validation commands and results
- next phase candidates

## Phase 15: Runtime Resilience And Frontend Bundle Splitting

### Goal

Reduce runtime fragility and frontend bundle size without changing product behavior.

### Backend Changes

#### `src/runtime/storage.py`

Added SQLite table:

```sql
CREATE TABLE IF NOT EXISTS checklist_progress (
    user_id       TEXT NOT NULL,
    checklist_id  TEXT NOT NULL,
    checked_json  TEXT NOT NULL DEFAULT '[]',
    updated_at    TEXT NOT NULL,
    PRIMARY KEY (user_id, checklist_id)
);
```

Added methods:
- `get_checklist_progress(user_id, checklist_id)`
- `save_checklist_progress(user_id, checklist_id, checked_items)`

Behavior:
- progress is scoped by user and checklist
- duplicate checked item keys are deduplicated while preserving order
- malformed stored JSON safely returns an empty list

#### `src/api/recommendation_routes.py`

Updated checklist progress endpoints:
- If `app.state.vector_storage` exists, use MongoDB-backed progress.
- Otherwise fall back to `StorageLayer` SQLite progress.

Affected endpoints:
- `GET /recommendations/checklists/{checklist_id}/progress`
- `POST /recommendations/checklists/{checklist_id}/progress`

Why:
- Checklist progress is lightweight user state and should not require MongoDB just to function locally or in reduced deployments.

### Frontend Changes

#### `frontend/src/App.tsx`

Changed route loading to use:
- `React.lazy()`
- `Suspense`
- named-export lazy helper
- route-level fallback UI

Pages now lazy-loaded include:
- user pages: Dashboard, Analyze, Contract, Documents, Templates, Risks, Checklists, Profile, Journey, Actions, LawSearch, SimilarCases, ComplianceRadar, ClauseCoach, EvidenceGap, ClauseSearch, Timeline, AnalysisHistory
- admin pages: AdminLogin, AdminDashboard, AdminDocuments, AdminJobs, AdminStats

Why:
- Vite production build previously produced a main JS bundle around `1,057 kB` and emitted a large chunk warning.
- After route splitting, main JS is around `298 kB`, and the large initial bundle warning is gone.

### Tests Added

#### `tests/runtime/test_phase10_runtime.py`

Added `TestChecklistProgressStorage`:
- round-trip persistence
- user scoping
- duplicate item deduplication

#### `tests/api/test_phase14_api.py`

Added SQLite fallback API test:
- checklist progress works without `vector_storage`

### Documentation Added

#### `docs/07-implementation/phase15-progress.md`

Documents:
- SQLite checklist fallback
- frontend lazy loading
- regression tests
- validation results
- bundle size change
- remaining phase candidates

## Phase 16: Demo Auth Production Safety Switch

### Goal

Keep local/demo usage easy while preventing production deployments from silently using `demo_user_001`.

### Backend Changes

#### `src/api/deps.py`

Added environment flag:
- `LEXAI_DEMO_AUTH`

Behavior:

```text
LEXAI_DEMO_AUTH unset or true
missing X-API-Key and X-User-ID -> demo_user_001
```

```text
LEXAI_DEMO_AUTH=false
missing X-API-Key and X-User-ID -> HTTP 422
```

Explicit identities still work:
- `X-API-Key`: verified against `AuthLayer`
- `X-User-ID`: accepted for browser/demo identity handoff

### Deployment Config Changes

#### `.env.example`

Added:

```env
LEXAI_DEMO_AUTH=true
```

with comments explaining local/demo vs strict mode.

#### `docker-compose.yml`

Added:

```yaml
LEXAI_DEMO_AUTH: "true"
```

Why:
- Local Docker remains demo-friendly.

#### `render.yaml`

Added:

```yaml
- key: LEXAI_DEMO_AUTH
  value: "false"
```

Why:
- Render deployment should default to strict identity behavior.

### Tests Added

#### `tests/api/test_phase10_api.py`

Added:
- missing identity returns `422` when `LEXAI_DEMO_AUTH=false`
- explicit `X-User-ID` still works when demo auth is disabled

Adjusted upload tests to reflect current auth model:
- upload can still use default demo user when demo auth is enabled
- explicit `X-User-ID` is accepted

### Documentation Added

#### `docs/07-implementation/phase16-progress.md`

Documents:
- demo auth feature flag
- strict behavior
- deployment defaults
- remaining auth work

## Validation Run

Backend:

```bash
python -m pytest -q
```

Result:

```text
130 passed, 4 warnings
```

Focused API/runtime:

```bash
python -m pytest tests\api\test_phase10_api.py tests\runtime\test_phase10_runtime.py tests\api\test_phase14_api.py -q
```

Result:

```text
54 passed, 4 warnings
```

Frontend typecheck:

```bash
cd frontend
npm run lint
```

Result:

```text
passed
```

Frontend production build:

```bash
cd frontend
npm run build
```

Result:

```text
passed
```

Bundle outcome:
- before route splitting: main JS about `1,057 kB`
- after route splitting: main JS about `298 kB`
- Vite large initial bundle warning resolved

Dev server smoke:

```bash
cd frontend
npm run dev
```

Checked:
- `http://localhost:3000/` returned HTTP 200
- `http://localhost:3000/src/App.tsx` returned HTTP 200

The dev server was stopped after verification.

## Files Changed In This Work

Backend:
- `src/api/app.py`
- `src/api/deps.py`
- `src/api/routes.py`
- `src/api/recommendation_routes.py`
- `src/runtime/storage.py`

Frontend:
- `frontend/src/App.tsx`

Tests:
- `tests/api/test_phase10_api.py`
- `tests/api/test_phase14_api.py`
- `tests/runtime/test_phase10_runtime.py`

Deployment/config:
- `.env.example`
- `docker-compose.yml`
- `render.yaml`

Docs:
- `docs/07-implementation/phase14-progress.md`
- `docs/07-implementation/phase15-progress.md`
- `docs/07-implementation/phase16-progress.md`
- `docs/07-implementation/phase14-16-change-log.md`

## Known Warnings

Backend tests still show warnings from dependencies:
- `bson` uses deprecated `datetime.datetime.utcfromtimestamp()`
- `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning from Starlette/AnyIO path

These do not currently fail tests.

## Remaining Work

Recommended next phases:

1. Replace raw `X-User-ID` with signed session/JWT identity for production.
2. Add role/permission checks beyond admin shared key validation.
3. Add browser smoke tests for high-traffic flows.
4. Normalize remaining mojibake in docs and source-facing Vietnamese strings.
5. Consider lazy-loading heavy chart dependencies separately from admin/profile routes.
