# Phase 19 - Full Session History + Clickable Action Plans

Date: 2026-05-25

## Goal

Fix two MVP usability gaps:

- conversation history must save the full multi-turn session, not only the latest question/answer pair;
- action plans must be clickable so users can inspect what each plan requires step by step.

## Conversation History Changes

`frontend/src/pages/Analyze.tsx`

- Added `historyRef` and `sessionIdRef` so the saved conversation uses the exact full-history snapshot at the moment a user sends a message.
- `Hội thoại mới` now starts a clean session:
  - clears the current chat;
  - clears the active session id;
  - clears attached evidence state;
  - returns to the chat tab.
- Each analysis request now receives a stable client session id.
- Each saved conversation uses the first user message as the session title, while storing all later turns inside `turns`.
- Chitchat and legal-analysis branches both save full turn history through the same helper.

`frontend/src/lib/api.ts`

- Conversation loading now merges backend sessions with localStorage sessions.
- When backend and localStorage both have the same session, the version with more turns wins.
- This prevents a shorter backend/local copy from overwriting a fuller local session.

## Action Plan Changes

`frontend/src/pages/Actions.tsx`

- Each action item is now an expandable card.
- Clicking a plan opens:
  - `Các bước cần làm`;
  - `Cần chuẩn bị`;
  - `Kết quả mong muốn`.
- The detail checklist is derived from:
  - action category;
  - priority;
  - deadline;
  - the recommendation reason.

## User Impact

- Users can review complete multi-turn legal analysis sessions from history.
- Starting a new conversation no longer accidentally continues the previous thread.
- Action plans are no longer flat text rows; they become actionable legal task cards.

## Validation

Completed on 2026-05-25:

```bash
cd frontend
npm run lint
# passed

npm run build
# passed
```
