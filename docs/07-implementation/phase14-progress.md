# Phase 14 Progress

## Scope
Phase 14 turns the Phase 10-13 runtime into a more usable product surface:
- document content viewer and original-file download
- session evidence upload
- checklist progress persistence
- reasoning trace access from the analysis UI
- tighter API identity handling for tenant isolation

## Implemented Backend
| Capability | Endpoint / File | Status |
| --- | --- | --- |
| Document content viewer | `GET /documents/{doc_id}/content` in `src/api/routes.py` | Implemented |
| Original file download | `GET /documents/{doc_id}/download` in `src/api/routes.py` | Implemented |
| Session evidence upload | `POST /sessions/{session_id}/evidence` in `src/api/routes.py` | Implemented |
| Checklist progress | `GET/POST /recommendations/checklists/{id}/progress` in `src/api/recommendation_routes.py` | Implemented |
| Trace retrieval | `GET /intelligence/trace/{trace_id}` | Implemented |
| Explicit auth for query/action/audit | `require_explicit_user` in `src/api/deps.py` | Implemented |

## Stabilization Completed
- `X-API-Key` now maps through `AuthLayer` to the stored tenant `user_id`.
- `X-User-ID` remains available for the browser/demo flow.
- Query, action, and audit endpoints now require an explicit identity header.
- Test apps with deterministic `bundle_provider` skip MongoDB startup, keeping API regression tests isolated and fast.
- Session evidence upload can use an injected `app.state.session_store`, which makes the endpoint testable without MongoDB.

## Regression Coverage
Added `tests/api/test_phase14_api.py` covering:
- document content returns extracted chunks
- cross-tenant document content is blocked
- global document content is visible to normal users
- original file download serves bytes from registered upload path
- session evidence upload extracts and attaches text
- unsupported evidence file types are rejected
- checklist progress round-trips per user/checklist

## Validation
```bash
python -m pytest -q
npm run lint
npm run build
```

Latest local result:
- backend: `124 passed`
- frontend typecheck: passed
- frontend build: passed, with Vite large chunk warning

## Next Phase Candidates
1. Phase 15: production auth hardening with JWT/session tokens and clear demo-mode boundaries.
2. Phase 15: split frontend routes with lazy loading to resolve the large bundle warning.
3. Phase 15: persist checklist progress without requiring MongoDB, or make the MongoDB dependency explicit in UI state.
4. Phase 15: normalize remaining mojibake in docs/source-facing Vietnamese strings.
