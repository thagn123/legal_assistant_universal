# Phase 23 - AI Task Breakdown

Date: 2026-05-28

This file is a concrete task plan for AI coding agents improving the repo into a demo-ready Personalized Community Intelligence MVP.

## Operating Rules For AI Agents

- Do not implement broad refactors.
- Preserve existing APIs unless a task explicitly extends them.
- Prefer existing modules:
  - `src/api/recommendation_routes.py`
  - `src/api/retrieval_routes.py`
  - `src/mongodb/mongo_storage.py`
  - `src/runtime/storage.py`
  - `src/recommenders/next_best_action.py`
  - `src/recommenders/behavior_recommender.py`
  - `frontend/src/lib/api.ts`
  - `frontend/src/pages/Analyze.tsx`
  - `frontend/src/pages/SimilarCases.tsx`
  - `frontend/src/pages/Dashboard.tsx`
- MongoDB is preferred when available; SQLite/local fallback must keep MVP working.
- Never store raw PII in community patterns.
- Every backend behavior change needs at least one targeted test.
- Every frontend route touched must pass `npm run lint` and `npm run build`.

## Epic 1 - Demo Persona Switching

### Task 1.1 - Frontend User Selector

Goal: allow demo/testing as 2-3 users without login complexity.

Files:

- `frontend/src/lib/api.ts`
- `frontend/src/components/layout/Header.tsx` or `frontend/src/pages/Profile.tsx`
- duplicate served UI folder if still used locally: `lexai-–-trợ-lý-pháp-lý-thông-minh UI/src/...`

Implementation:

- Reuse existing `setUserId(id)` and `getUserId()`.
- Add a compact selector:
  - `demo_user_family`
  - `demo_user_employee`
  - `demo_user_sme`
- On change:
  - call `setUserId`;
  - clear/reload page-level digest state;
  - show toast: "Đã chuyển hồ sơ demo".

Acceptance:

- Network requests include different `X-User-ID`.
- Dashboard and recommendations reload after switching.

### Task 1.2 - Backend Demo Persona Seed

Goal: create deterministic data so each persona feels different.

Files:

- `src/mongodb/seed_data.py`
- `src/runtime/storage.py` if SQLite fallback seed helper is needed
- new script optional: `scripts/seed_phase23_demo_personas.py`

Implementation:

- Seed interactions:
  - family: `similar_cases`, `evidence_gap`, `action_plan`, `child_custody`
  - employee: `law_search`, `timeline`, `labor_termination`
  - sme: `contract`, `clause_search`, `risk_review`
- Seed useful/not-useful feedback.
- Seed saved analyses if needed for dashboard.

Acceptance:

- `/recommendations/behavior/digest` differs by persona.
- `/recommendations/next-best-actions` differs by persona for at least one shared query.

## Epic 2 - Community Similar Cases

### Task 2.1 - Privacy Sanitizer

Goal: summarize user situations without private details.

Files:

- new: `src/privacy/anonymizer.py`
- tests: `tests/privacy/test_anonymizer.py`

Implementation:

- Redact:
  - emails;
  - phone numbers;
  - CCCD/CMND-like long numbers;
  - exact street/house-number patterns;
  - quoted names after phrases like "tôi tên", "vợ tôi tên", "ông/bà".
- Return:
  - `safe_summary`;
  - `redaction_count`;
  - `risk_flags`.
- Keep deterministic fallback summary based on domain/goal extraction.

Acceptance:

- Tests prove obvious PII is removed.
- Sanitizer never returns empty summary for valid input.

### Task 2.2 - Community Case Storage

Goal: store anonymized case patterns searchable by later users.

Files:

- `src/mongodb/mongo_storage.py`
- `src/runtime/storage.py`
- tests: `tests/runtime/test_community_case_patterns.py`

Implementation:

- Add methods:
  - `save_community_case_pattern(user_id, situation, analysis_result)`
  - `search_community_case_patterns(query, domain, limit)`
  - `increment_community_case_signal(pattern_id, signal)`
- MongoDB collection: `community_case_patterns`.
- SQLite fallback table with JSON fields.
- Store only sanitized summary/resolution.

Acceptance:

- Save and search works without MongoDB.
- Search excludes private raw text.

### Task 2.3 - Similar Cases API Extension

Goal: `/retrieval/similar-cases` returns official cases + community cases.

Files:

- `src/api/retrieval_routes.py`
- `frontend/src/lib/api.ts`
- tests: `tests/api/test_retrieval_similar_cases.py`

Implementation:

- Extend response with:
  - `official_cases`
  - `community_cases`
  - keep existing `similar_cases` for backward compatibility
  - `personalization_note`
  - `cross_language_used`
- After successful search, save anonymized pattern if input is valid and not duplicate.
- Add request flag optional:
  - `include_community: true`
  - `persist_anonymized: true`

Acceptance:

- Existing UI still works.
- New UI can render community section.
- API returns non-empty community results for seeded data.

### Task 2.4 - Similar Cases UI

Goal: make community patterns visible and useful.

Files:

- `frontend/src/pages/SimilarCases.tsx`

Implementation:

- Add section: "Vụ việc cộng đồng đã tìm".
- Card fields:
  - tóm tắt tình huống;
  - hướng giải quyết;
  - bước nên làm;
  - độ tương đồng;
  - tags.
- Add feedback actions:
  - useful;
  - not useful;
  - save.
- Log interactions for community case clicks.

Acceptance:

- User can search and see official + community patterns.
- Empty state explains how community data is anonymized.

## Epic 3 - Collaborative Intelligence

### Task 3.1 - MongoDB Aggregation Pipeline For Peer Recommendations

Goal: recommend content from users with similar behavior.

Files:

- `src/mongodb/mongo_storage.py`
- `src/recommenders/behavior_recommender.py`
- tests: `tests/recommenders/test_behavior_recommender.py`

Pipeline concept:

1. Match current user's recent interactions.
2. Group by `law_type`, `module`, `action_type`.
3. Find peers with overlapping signals.
4. Aggregate peer clicked/saved/read items.
5. Exclude dismissed/currently seen items.
6. Sort by peer score, useful rate, recency.

Acceptance:

- Works with seeded personas.
- Returns at least one recommendation for each demo persona.
- Does not recommend items the user dismissed repeatedly.

### Task 3.2 - Behavior Score Normalization

Goal: produce stable behavior scores for reranking.

Files:

- `src/api/recommendation_routes.py`
- `src/recommenders/next_best_action.py`

Implementation:

- Normalize interaction score to bounded range, e.g. `[-0.12, +0.18]`.
- Positive:
  - click;
  - save;
  - useful.
- Negative:
  - dismiss;
  - not useful.
- Impression should be tiny and only used for exposure tracking.

Acceptance:

- Legal relevance remains primary.
- Behavior can change order among close candidates.

## Epic 4 - Deep Personalization And Reranking

### Task 4.1 - Ranking Signal Explanation

Goal: show why two users get different results.

Files:

- `src/recommenders/next_best_action.py`
- `src/engine/recommendation_ranker.py`
- `src/api/recommendation_routes.py`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/Analyze.tsx`

Implementation:

- Add response fields:
  - `ranking_signals`
  - `behavior_score`
  - `personalization_reason`
- UI displays compact text:
  - "Ưu tiên vì bạn thường xem vụ việc tương tự"
  - "Được cộng điểm vì hồ sơ của bạn quan tâm lao động"

Acceptance:

- Same query for two personas shows visibly different reason/order.

### Task 4.2 - Six-Signal Reranking Consistency

Goal: align all recommendation endpoints around 6 signals.

Signals:

1. semantic similarity;
2. behavior score;
3. graph relevance;
4. freshness;
5. popularity;
6. accepted/useful rate.

Files:

- `src/engine/recommendation_ranker.py`
- `src/api/recommendation_routes.py`
- `src/api/retrieval_routes.py`

Acceptance:

- Tests cover signal contribution.
- Response can expose signal scores for demo/debug mode.

## Epic 5 - Cross-Language Retrieval

### Task 5.1 - Language Detection Metadata

Goal: API tells UI when cross-language retrieval was used.

Files:

- `src/retrieval/query_normalizer.py`
- `src/retrieval/retrieval_engine.py`
- `src/api/retrieval_routes.py`
- `frontend/src/pages/LawSearch.tsx`
- `frontend/src/pages/SimilarCases.tsx`

Implementation:

- Add `query_language`.
- Add `expanded_aliases`.
- Add `cross_language_used`.

Acceptance:

- English labor query can map to Vietnamese labor law result.
- UI shows a small cross-language note.

### Task 5.2 - MVP Alias Dictionary

Goal: support common demo terms.

Add alias pairs:

- divorce <-> ly hôn
- custody <-> quyền nuôi con
- asset division <-> chia tài sản
- termination <-> sa thải / chấm dứt hợp đồng lao động
- social insurance <-> bảo hiểm xã hội
- contract penalty <-> phạt vi phạm
- land dispute <-> tranh chấp đất

Acceptance:

- Alias expansion tested.

## Epic 6 - Cross-Session User Memory

### Task 6.1 - Memory Summary Injection

Goal: same user does not repeat context in later sessions.

Files:

- `src/api/recommendation_routes.py`
- `src/api/conversation_routes.py`
- `src/memory/user_memory.py` if present
- `frontend/src/pages/Analyze.tsx`
- `frontend/src/pages/Profile.tsx`

Implementation:

- Save legal context summaries, not raw private details, for prompt/recommendation context.
- Inject safe memory into next analysis.
- Add UI preview: "LexAI nhớ gì về hồ sơ này".

Acceptance:

- Memory is isolated by `X-User-ID`.
- User can clear memory.

## Epic 7 - GraphRAG

### Task 7.1 - Show Legal Graph Relations In Results

Goal: make GraphRAG visible enough for MVP.

Files:

- `src/graphrag/traversal.py`
- `src/engine/retrieval_fusion.py`
- `src/api/retrieval_routes.py`
- `frontend/src/pages/LawSearch.tsx`

Implementation:

- Include relation labels in retrieval result metadata.
- Only show graph relations with provenance.
- Do not invent relation if data is missing.

Acceptance:

- At least one seeded/demo result shows a relation label when data exists.

## Epic 8 - Deterministic Fallback

### Task 8.1 - AI Failure Smoke

Goal: product still works when OpenAI/tool-calling fails.

Files:

- `src/agents/legal_agent.py`
- `src/api/recommendation_routes.py`
- `src/api/retrieval_routes.py`
- `frontend/src/lib/api.ts`

Implementation:

- Add tests with missing/disabled AI config.
- Ensure deterministic analysis includes:
  - limitation note;
  - relevant laws if available;
  - next-best actions;
  - similar cases fallback.

Acceptance:

- No endpoint returns HTTP 500 for normal legal query when AI unavailable.

## Epic 9 - End-To-End Demo Test

### Task 9.1 - Local E2E Script

Goal: one command validates the MVP demo flow.

Files:

- new: `scripts/smoke_phase23_mvp.py`
- optional frontend browser test if Playwright is available.

Flow:

1. Set user `demo_user_family`.
2. Analyze shared query.
3. Read next-best-actions.
4. Search similar cases.
5. Mark a recommendation useful.
6. Repeat next-best-actions.
7. Switch user `demo_user_employee`.
8. Run same query.
9. Assert ranking differs.

Acceptance:

- Script exits 0 locally with `create_app(use_mongodb=False)`.
- Optional mode hits deployed URL via env var `LEXAI_DEPLOYED_BASE_URL`.

## Final MVP Definition Of Done

- Backend tests pass for:
  - privacy sanitizer;
  - community case pattern storage;
  - similar cases API;
  - persona personalization;
  - cross-language alias;
  - deterministic fallback.
- Frontend build passes.
- Demo personas are switchable.
- Same query differs by user.
- Community similar cases render.
- No private data is displayed in community patterns.
- Documentation updated with screenshots or route list after implementation.

