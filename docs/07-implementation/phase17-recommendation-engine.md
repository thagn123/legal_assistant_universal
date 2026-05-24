# Phase 17 - Recommendation Engine Push

Date: 2026-05-24

## Goal

Strengthen the MVP recommendation layer so the legal analysis result does not only show static related modules. The system should rank the next best actions based on the actual analysis context:

- legal domain
- position score
- domain confidence
- citations
- warnings
- generated action list
- risk assessment

## What Changed

### Next-best-action engine

Added:

```text
src/recommenders/next_best_action.py
```

The engine is deterministic and does not require MongoDB or vector search. This keeps MVP guidance available even when the larger recommendation stack is offline.

It ranks follow-up actions such as:

- evidence gap check
- law search
- action planning
- risk review
- timeline/deadline check
- similar cases
- contract review
- compliance checklist
- legal journey view

Each recommendation includes:

- action id
- title and description
- target module and URL
- category
- priority
- score
- reason
- supporting citations
- prefill context
- blocking gaps

### API endpoint

Added:

```text
POST /recommendations/next-best-actions
```

This endpoint works without MongoDB. It accepts analysis context and returns ranked next actions.

### Intelligence integration

Updated:

```text
POST /intelligence/analyze
```

The response now includes:

```text
next_best_actions
```

These actions are generated after the orchestrator completes, using the final domain, score, citations, warnings, recommendations and risks.

### Frontend integration

Updated:

```text
frontend/src/lib/api.ts
frontend/src/pages/Analyze.tsx
```

The analysis result card now renders dynamic next-best-action recommendations from the backend. If the backend does not provide them, the UI falls back to a small static set.

Each card navigates to the target module and passes the same analysis context forward, so specialized modules can continue from the MVP analysis result.

## Why This Matters

Before this phase, related modules were available but static. The user still had to decide which module mattered most.

After this phase, the recommendation engine actively answers:

```text
What should I do next, and why?
```

This makes the MVP flow stronger:

```text
Legal analysis
-> evaluation and citations
-> ranked next best actions
-> prefilled specialized module
```

## Validation Added

Added tests:

```text
tests/recommenders/test_next_best_action.py
tests/api/test_recommendation_next_best_action_api.py
```

Covered behavior:

- weak evidence prioritizes evidence-gap and law-search recommendations
- contract situations promote contract review
- API endpoint works without MongoDB
- API output is ranked and route-ready

## Validation Run

Backend:

```bash
python -m pytest tests\recommenders\test_next_best_action.py tests\api\test_recommendation_next_best_action_api.py -q
python -m pytest tests\api\test_phase10_api.py tests\api\test_phase14_api.py tests\api\test_recommendation_next_best_action_api.py tests\recommenders\test_next_best_action.py -q
```

Result:

```text
3 passed
32 passed
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Result:

```text
TypeScript passed
Production build passed
```

## Remaining Recommendations

1. Add user-behavior personalization into the next-best-action score once interaction data is available.
2. Add acceptance feedback so users can mark recommendations useful/not useful.
3. Display blocking gaps more prominently in the UI.
4. Store recommendation impressions and clicks for later ranking improvements.
