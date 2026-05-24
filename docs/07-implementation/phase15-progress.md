# Phase 15 Progress

## Scope
Phase 15 focuses on production-readiness improvements that reduce runtime fragility without changing product behavior:
- local persistence for lightweight user state when MongoDB is unavailable
- frontend route code splitting
- preserving tenant isolation while supporting demo/browser identity

## Implemented
| Capability | File | Status |
| --- | --- | --- |
| SQLite checklist progress table | `src/runtime/storage.py` | Implemented |
| Checklist progress SQLite fallback | `src/api/recommendation_routes.py` | Implemented |
| Route-level frontend lazy loading | `frontend/src/App.tsx` | Implemented |
| Storage regression tests | `tests/runtime/test_phase10_runtime.py` | Implemented |
| API fallback regression test | `tests/api/test_phase14_api.py` | Implemented |

## Details
- Checklist progress no longer requires MongoDB. If `app.state.vector_storage` exists, progress is saved there; otherwise the API falls back to `StorageLayer`.
- `StorageLayer.save_checklist_progress()` deduplicates item keys while preserving order.
- Frontend pages and admin pages are now loaded with `React.lazy()` and `Suspense`, keeping the shell responsive and reducing the initial JavaScript payload.

## Validation
```bash
python -m pytest tests\runtime\test_phase10_runtime.py tests\api\test_phase14_api.py -q
npm run lint
npm run build
```

Latest local result:
- runtime/API subset: `33 passed`
- frontend typecheck: passed
- frontend build: passed
- Vite large chunk warning: resolved by route splitting

## Build Size Change
Before route splitting:
- main JS bundle: about `1,057 kB`

After route splitting:
- main JS bundle: about `298 kB`
- largest lazy chunks: `CategoricalChart` about `316 kB`, `Analyze` about `143 kB`

## Remaining Phase Candidates
1. Add real production auth mode with JWT/session tokens while keeping demo mode explicit.
2. Add service-worker or IndexedDB-backed offline cache for checklist/document UI state.
3. Normalize remaining mojibake in docs and source-facing Vietnamese strings.
4. Add browser smoke tests for the highest-traffic frontend flows.
