# Phase 20 - Demo Recommendation Feedback Loop

Date: 2026-05-25

## Goal

Prioritize product-value demo behavior instead of heavy ML infrastructure:

- show feedback controls directly on recommendation cards;
- persist impressions, clicks, useful/not-useful, and dismiss events;
- use those behavior signals to nudge next-best-action ranking on later analyses.

## Backend Changes

`src/recommenders/next_best_action.py`

- `NextBestActionRecommender.recommend()` now accepts optional `behavior_scores`.
- Behavior scores adjust recommendation score within a bounded range so legal-analysis quality remains the primary signal.
- Positive feedback can lift a module/action; dismiss or negative feedback can lower it.

`src/api/recommendation_routes.py`

- Added `_next_best_action_behavior_scores()`.
- Reads recent interaction history from MongoDB when available, otherwise SQLite fallback.
- Uses these action types:
  - `recommendation_impression`
  - `recommendation_click`
  - `recommendation_useful`
  - `recommendation_not_useful`
  - `recommendation_dismiss`
  - `recommendation_feedback`
- Applies behavior score in:
  - `POST /recommendations/next-best-actions`
  - `POST /intelligence/analyze` next-best-action output.

## Frontend Changes

`frontend/src/pages/Analyze.tsx`

- Recommendation cards now log impressions when shown.
- Clicks still navigate into the target module and are persisted with `action_id`, `module`, `law_type`, score, priority, and session id.
- Each recommendation now has compact controls:
  - useful;
  - not useful;
  - dismiss/hide.
- Dismiss hides the card immediately in the current result.
- Useful/not-useful visually marks the selected feedback and affects future ranking through the backend interaction log.

## Tests

`tests/recommenders/test_next_best_action.py`

- Added coverage proving behavior feedback can rerank next-best-action output.

`tests/api/test_recommendation_next_best_action_api.py`

- Added API coverage proving useful feedback stored through `/interactions/log` can influence `/recommendations/next-best-actions` without MongoDB.

## Validation

Completed on 2026-05-25:

```bash
python -m pytest tests\recommenders\test_next_best_action.py tests\api\test_recommendation_next_best_action_api.py -q
# 5 passed, 1 warning

python -m pytest -q
# 141 passed, 4 warnings

cd frontend
npm run lint
# passed

npm run build
# passed
```

## Demo Impact

The recommendation engine now feels adaptive in the core product flow:

1. User gets legal analysis.
2. The system shows ranked next-best-action cards.
3. User clicks, likes, dislikes, or hides a recommendation.
4. The interaction is stored.
5. Later recommendations are nudged by that behavior.

This is intentionally lightweight but product-visible, which is the right tradeoff for demo readiness.
