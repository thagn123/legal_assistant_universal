# Phase 16 Progress

## Scope
Phase 16 adds a production safety switch around demo identity behavior.

The app still supports the browser/demo flow with `X-User-ID`, but deployments
can now disable implicit fallback to `demo_user_001`.

## Implemented
| Capability | File | Status |
| --- | --- | --- |
| Demo-auth feature flag | `src/api/deps.py` | Implemented |
| Strict missing-identity behavior | `src/api/deps.py` | Implemented |
| Env example | `.env.example` | Implemented |
| Render deployment default | `render.yaml` | Implemented |
| Docker Compose local default | `docker-compose.yml` | Implemented |
| API regression tests | `tests/api/test_phase10_api.py` | Implemented |

## Behavior
Default local/demo behavior:
```text
LEXAI_DEMO_AUTH unset or true
missing X-API-Key and X-User-ID -> demo_user_001
```

Production-style strict behavior:
```text
LEXAI_DEMO_AUTH=false
missing X-API-Key and X-User-ID -> HTTP 422
```

Explicit identities still work in strict mode:
- `X-API-Key`: verified against `AuthLayer`
- `X-User-ID`: accepted for browser/demo identity handoff

## Validation
```bash
python -m pytest tests\api\test_phase10_api.py -q
python -m pytest -q
```

## Remaining Auth Work
1. Replace raw `X-User-ID` with signed session/JWT identity for production.
2. Add role/permission checks beyond admin key validation.
3. Replace admin shared-key auth with scoped admin sessions.
