# Phase 21 - Input Guard + Session Memory Fix

Date: 2026-05-25

## Issue

During Vercel demo testing:

- random input such as `aksjf` was sent to `/intelligence/analyze` with the active `session_id`;
- the backend session memory reused the previous legal context, so the answer looked like it was responding to an older divorce question;
- greetings such as `chào` were not reliably saved in conversation history.

## Fix

`frontend/src/pages/Analyze.tsx`

- Reworked chitchat detection with Unicode normalization so Vietnamese greetings such as `chào`, `xin chào`, and `cảm ơn` are recognized reliably.
- Added a low-signal input guard:
  - very short/random text without legal signals is handled locally;
  - the app asks the user to provide more facts;
  - the request is not sent to the legal-analysis API;
  - the active legal session memory is not polluted.
- Low-signal and chitchat turns are still appended to the full chat history and saved through the existing conversation persistence flow.
- Low-signal inputs are logged as `low_signal_input` for later UX analysis.

## Demo Behavior

Expected after this phase:

- `chào` -> local greeting response, saved in conversation history.
- `aksjf` -> local clarification response, saved in conversation history.
- Neither input calls the legal analysis pipeline.
- Previous legal session context no longer leaks into random/non-legal inputs.

## Validation

Completed on 2026-05-25:

```bash
cd frontend
npm run lint
# passed

npm run build
# passed
```
