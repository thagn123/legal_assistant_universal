# Phase 18 - Behavior Recommendation + Conversation Memory

Date: 2026-05-25

## Goal

Strengthen the recommendation engine beyond one-shot legal analysis by adding:

- recommendations from user habits and UI gestures;
- local SQLite fallback when MongoDB is unavailable;
- backend-persisted conversation history so analysis sessions survive browser storage;
- frontend hooks that log recommendation clicks and save complete chat sessions.

## What Changed

### Backend: behavior memory in SQLite

`src/runtime/storage.py`

- Added `interactions` table for user gestures:
  - `user_id`
  - `doc_id`
  - `action_type`
  - `context_json`
  - `chunk_id`
  - `timestamp`
- Added behavior helper methods used by `BehaviorRecommender`:
  - `log_interaction`
  - `get_user_interaction_history`
  - `get_user_action_frequency`
  - `get_user_active_hours`
  - `get_user_law_types_since`
  - `get_trending_law_types`
  - `get_user_action_bigrams`
  - `get_user_viewed_docs`
- Added safe fallback stubs for peer recommendations:
  - `find_peer_users`
  - `get_trending_content_for_peers`

This lets `/recommendations/behavior/*` run from SQLite during MVP/demo mode, instead of failing when MongoDB is absent.

### Backend: conversation history

`src/runtime/storage.py`

- Added `conversation_sessions` table.
- Added conversation session helpers:
  - `save_conversation_session`
  - `list_conversation_sessions`
  - `get_conversation_session`
  - `delete_conversation_session`
  - `clear_conversation_sessions`

`src/api/conversation_routes.py`

- Added API routes:
  - `POST /conversations`
  - `GET /conversations`
  - `GET /conversations/{session_id}`
  - `DELETE /conversations/{session_id}`
  - `DELETE /conversations`

`src/api/app.py`

- Registered `conversation_router`.

### Backend: behavior API fallback

`src/api/recommendation_routes.py`

- Added behavior source resolver:
  - prefer MongoDB `vector_storage` when available;
  - fall back to SQLite `StorageLayer`.
- Updated these endpoints to use the fallback source:
  - `POST /interactions/log`
  - `GET /recommendations/behavior/profile`
  - `GET /recommendations/behavior/proactive`
  - `POST /recommendations/behavior/next-action`
  - `GET /recommendations/behavior/peers`
  - `GET /recommendations/behavior/digest`
  - `GET /feed/personalized`
- Relaxed interaction logging so `doc_id` is optional. This is important because many useful gestures are not tied to a document, such as:
  - legal analysis submit;
  - recommendation click;
  - checklist open;
  - risk review;
  - module handoff.

### Frontend: saved conversations

`frontend/src/lib/api.ts`

- Added `ConversationTurn` and `ConversationSession` types.
- Added `saveConversationSession`.
- Added `loadConversationSessions`.
- Both functions keep localStorage as a fallback, but now sync with backend `/conversations`.

`frontend/src/pages/Analyze.tsx`

- Loads saved sessions from backend on mount.
- Saves full chat turns after:
  - chitchat replies;
  - legal analysis responses.
- Keeps local session list updated after each saved turn.

### Frontend: recommendation gestures

`frontend/src/pages/Analyze.tsx`

- Logs `recommendation_click` when the user chooses a backend-ranked next-best-action card.
- Sends context into the behavior layer:
  - module;
  - law type;
  - score;
  - priority;
  - session id.

This gives the recommendation engine a feedback loop: it can learn which modules the user actually follows after an analysis.

## Recommendation Signals Now Available

The MVP recommendation layer can now combine:

- current legal analysis result;
- citations and detected evidence gaps;
- action history frequency;
- repeated action sequences;
- top legal domains by recency-weighted interactions;
- adjacent legal domains;
- module click behavior;
- saved conversation context.

## Tests Added

`tests/api/test_behavior_conversation_api.py`

- verifies interaction logging without `doc_id`;
- verifies behavior profile from SQLite;
- verifies proactive and sequential recommendations without MongoDB;
- verifies conversation save/list/get and tenant isolation.

`tests/runtime/test_phase10_runtime.py`

- verifies interaction history, action frequencies, law type extraction;
- verifies action bigrams for habit-based next actions;
- verifies conversation session round-trip and user isolation.

## Validation

Completed on 2026-05-25:

```bash
python -m pytest tests\api\test_behavior_conversation_api.py tests\runtime\test_phase10_runtime.py -q
# 31 passed, 1 warning

python -m pytest -q
# 139 passed, 4 warnings

cd frontend
npm run lint
# passed

npm run build
# passed
```

Frontend smoke:

- `http://127.0.0.1:3000/` returned HTTP 200 from the Vite dev server.
- Automated Playwright smoke could not run because the local runtime was missing `playwright-core`; no dependency was installed as part of this phase.

## MVP Impact

The Legal Analysis MVP now has a stronger recommendation loop:

1. User describes a legal situation.
2. Analysis returns legal position, evidence, risks, and citations.
3. Next-best-action recommends relevant modules.
4. User clicks a recommendation.
5. The click is stored as behavior memory.
6. Later recommendations can use that habit and conversation context.

This is the first complete loop from analysis -> recommendation -> user gesture -> persisted memory -> improved recommendation.
