# Phase 22 - Goal-Aware Recommendation Engine Plan

Date: 2026-05-25

## Product Goal

Make the recommendation engine feel closer to the user's actual legal need, not just the detected legal domain.

For the demo, the highest-value behavior is:

- infer what the user is trying to achieve;
- infer the user's practical position/role;
- recommend the next module with a personalized explanation;
- ask the next best question that would materially improve the legal assessment;
- show a short legal journey that feels like a case strategy.

## Scope

### Backend

Extend `src/recommenders/next_best_action.py`:

1. Detect user goals from the situation text:
   - divorce and child custody;
   - asset protection/division;
   - debt recovery;
   - employment termination;
   - land/real-estate dispute;
   - contract enforcement;
   - complaint/lawsuit preparation;
   - risk avoidance.

2. Detect practical role signals:
   - parent seeking custody;
   - employee;
   - employer/company;
   - buyer/seller;
   - claimant/complainant;
   - debtor/creditor;
   - general user.

3. Produce goal-aware metadata for each recommendation:
   - `detected_goals`;
   - `user_position`;
   - `next_questions`;
   - `journey_steps`;
   - richer `reason` text.

4. Use goal signals to adjust ranking:
   - custody/asset goals boost evidence, action plan, risk, timeline;
   - deadline/urgent signals boost timeline/action plan;
   - contract goals boost contract review;
   - weak evidence boosts evidence gap and law search;
   - prior behavior feedback remains a secondary nudge.

### API

Extend `NextBestActionOut` so frontend can render:

- `detected_goals`;
- `user_position`;
- `next_questions`;
- `journey_steps`.

This applies to:

- `POST /recommendations/next-best-actions`;
- `POST /intelligence/analyze` embedded `next_best_actions`.

### Frontend

Update `frontend/src/pages/Analyze.tsx`:

1. Show a compact “Hiểu nhu cầu của bạn” strip above recommendation cards:
   - user position;
   - detected goals.

2. Show “Câu hỏi nên bổ sung” under the recommendation section:
   - 2-4 questions;
   - phrased as practical legal intake questions.

3. Show “Lộ trình đề xuất”:
   - 3-5 steps;
   - based on the detected goals and recommended modules.

4. Keep the existing feedback controls:
   - useful;
   - not useful;
   - dismiss.

## Acceptance Criteria

- A divorce/custody/asset question should produce goals like `child_custody`, `asset_division`, `divorce`.
- Recommendations should include next questions about:
  - who the children live with;
  - income/care conditions;
  - whether assets are common or separate.
- The UI should make it obvious why a recommendation is being shown.
- Existing next-best-action tests continue to pass.
- New tests cover goal-aware metadata and ranking.

## Implementation Steps

1. Add goal/role detection helpers.
2. Extend `NextBestAction` dataclass with metadata fields.
3. Add goal-aware score boosts and reason enrichment.
4. Extend API response model.
5. Extend frontend type and rendering.
6. Add tests.
7. Run:

```bash
python -m pytest tests\recommenders\test_next_best_action.py tests\api\test_recommendation_next_best_action_api.py -q
python -m pytest -q
cd frontend
npm run lint
npm run build
```

## Demo Example

Input:

```text
Tôi muốn ly hôn, có hai con, muốn nuôi con và giữ tài sản.
```

Expected recommendation behavior:

- detected goals:
  - divorce;
  - child custody;
  - asset division/protection.
- user position:
  - parent seeking custody.
- top recommendations:
  - action plan;
  - evidence gap;
  - risk review;
  - timeline.
- next questions:
  - Hai con hiện đang sống với ai?
  - Tài sản muốn giữ là tài sản chung hay riêng?
  - Bạn có chứng cứ về thu nhập, nơi ở, thời gian chăm sóc con không?

## Implementation Result

Completed on 2026-05-25.

### Backend

Implemented in `src/recommenders/next_best_action.py`:

- Added `GoalProfile`.
- Added goal detection from normalized Vietnamese text.
- Added role/position detection.
- Added next-question generation.
- Added journey-step generation.
- Added bounded goal-aware score boosts.
- Extended `NextBestAction` with:
  - `detected_goals`;
  - `user_position`;
  - `next_questions`;
  - `journey_steps`.

Implemented in `src/api/recommendation_routes.py`:

- Extended `NextBestActionOut` with the same goal-aware metadata.

### Frontend

Implemented in `frontend/src/lib/api.ts`:

- Extended `NextBestAction` type with optional goal-aware metadata fields.

Implemented in `frontend/src/pages/Analyze.tsx`:

- Added “Hiểu nhu cầu của bạn”.
- Added detected goal chips.
- Added user-position label.
- Added “Câu hỏi nên bổ sung”.
- Added “Lộ trình đề xuất”.
- Kept existing useful/not-useful/dismiss feedback controls.

### Tests

Updated:

- `tests/recommenders/test_next_best_action.py`
- `tests/api/test_recommendation_next_best_action_api.py`

Coverage added for:

- divorce/custody/asset goal detection;
- Vietnamese phrase `nhận nuôi` mapped to `child_custody`;
- `parent_seeking_custody` position;
- next questions;
- journey steps;
- API response metadata.

## Validation

Completed on 2026-05-25:

```bash
python -m pytest tests\recommenders\test_next_best_action.py tests\api\test_recommendation_next_best_action_api.py -q
# 7 passed, 1 warning

python -m pytest -q
# 144 passed, 4 warnings

cd frontend
npm run lint
# passed

npm run build
# passed
```
