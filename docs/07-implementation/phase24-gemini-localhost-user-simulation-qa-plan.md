# Phase 24 - Gemini Localhost User Simulation QA Plan

Date: 2026-05-28

## Goal

Tạo một bộ kiểm thử tự động chạy trên localhost, trong đó Gemini Flash đóng vai người dùng thật để trải nghiệm LexAI bằng tiếng Việt và tiếng Anh, sau đó chấm điểm sản phẩm, đánh giá MVP đã hoàn thiện chưa, và ghi lại các lỗi/chỗ chưa chạy được để tiếp tục lên plan sửa.

Mục tiêu không phải chỉ là test API. Mục tiêu là kiểm tra cảm giác sử dụng sản phẩm end-to-end:

```text
Gemini as user
  -> mở localhost
  -> chọn persona
  -> nhập tình huống pháp lý
  -> đọc phản hồi
  -> click recommendation
  -> chuyển module
  -> đánh giá kết quả
  -> ghi lỗi / điểm / đề xuất sửa
```

## Scope

### Local targets

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8001`
- Optional deployed target: env `LEXAI_QA_BASE_URL`

### AI evaluator

- Model name should be configurable:

```bash
GEMINI_MODEL=gemini-3.5-flash
```

If the exact model name is unavailable in the local Google SDK/API version, the runner should allow override through env and fail with a clear setup message, not hardcode a model forever.

### Languages

All product testing must include:

- Vietnamese user flows.
- English user flows.
- Mixed Vietnamese/English legal queries.

## Core Principle

Gemini should behave like a user, not like a unit test.

It should evaluate:

- Does the page load?
- Does the user understand what to do?
- Does the AI answer match the user's situation?
- Are recommendations actionable?
- Does context carry into the next module?
- Does the same query produce different ranking for different personas?
- Does English query retrieve Vietnamese legal knowledge?
- Are errors friendly?
- Does the MVP feel complete enough for demo?

## Suggested Runner Architecture

Create a runner script later, for example:

```text
scripts/gemini_localhost_user_qa.py
```

Recommended components:

1. **Browser automation layer**
   - Prefer Playwright if available.
   - Otherwise use requests/API smoke for backend and a reduced DOM smoke for frontend.

2. **Gemini evaluator layer**
   - Sends visible page text, screenshots or structured DOM summaries to Gemini.
   - Asks Gemini to score and decide next user action.
   - Avoids exposing secrets or raw private user info.

3. **Scenario executor**
   - Runs fixed scripts for reproducibility.
   - Allows Gemini to make limited user-like choices within a scenario.

4. **Report writer**
   - Saves output to:

```text
reports/gemini_localhost_qa_YYYY-MM-DD.md
reports/gemini_localhost_qa_YYYY-MM-DD.json
```

5. **Fix-plan writer**
   - If blocking issues are found, create:

```text
docs/07-implementation/phase24-gemini-qa-fix-plan.md
```

## Environment Variables

```bash
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.5-flash
LEXAI_FRONTEND_URL=http://localhost:3000
LEXAI_BACKEND_URL=http://localhost:8001
LEXAI_QA_HEADLESS=1
LEXAI_QA_OUTPUT_DIR=reports
```

Optional:

```bash
LEXAI_QA_BASE_URL=https://legal-assistant-universal.vercel.app
LEXAI_QA_USER_IDS=demo_user_family,demo_user_employee,demo_user_sme
```

## Gemini Role Prompt

Use this as the system/developer prompt for the evaluator:

```text
Bạn là Gemini QA Evaluator cho sản phẩm LexAI.

Bạn phải hóa thân thành người dùng thật đang trải nghiệm một legal recommendation engine.
Bạn test bằng cả tiếng Việt và tiếng Anh.
Bạn không chỉ kiểm tra app có chạy hay không, mà phải đánh giá sản phẩm có giúp người dùng đạt mục tiêu pháp lý hay không.

Bạn cần chấm điểm từng flow theo thang 0-10:
- UX clarity
- legal relevance
- evidence/citation usefulness
- recommendation quality
- personalization
- context retention
- error resilience
- MVP completeness

Khi thấy lỗi, hãy ghi rõ:
- bước nào lỗi
- hành vi mong đợi
- hành vi thực tế
- mức độ nghiêm trọng: blocker / major / minor
- module liên quan
- đề xuất sửa

Không được khẳng định tư vấn pháp lý là chính thức.
Không được yêu cầu lưu thông tin riêng tư.
Không được coi câu trả lời không có dẫn chứng là hoàn thiện.
```

## MVP Score Rubric

### 1. Page Load And Navigation - 10 points

- 10: app loads, no blank screen, sidebar/header usable, route transitions work.
- 7: app loads but one non-critical route has issue.
- 4: multiple dead routes or confusing navigation.
- 0: cannot start product.

### 2. Legal Analysis Quality - 10 points

- 10: answer understands situation, cites legal basis, flags limitations.
- 7: useful but citations/evidence weak.
- 4: generic answer or wrong domain.
- 0: hallucinated or irrelevant.

### 3. Recommendation Engine - 10 points

- 10: next-best-actions are actionable, ranked, personalized, clickable.
- 7: recommendations exist but reasons/personalization unclear.
- 4: static recommendations feel generic.
- 0: no usable recommendations.

### 4. Personalization - 10 points

- 10: same query differs meaningfully for different demo users.
- 7: behavior affects some order/labels.
- 4: persona switching exists but little impact.
- 0: all users receive identical output.

### 5. Similar Cases / Community Intelligence - 10 points

- 10: similar cases and anonymized community patterns show useful summaries and resolution steps.
- 7: similar cases work but community/history weak.
- 4: results show but are generic or empty often.
- 0: route broken.

### 6. Cross-Language Retrieval - 10 points

- 10: English query retrieves relevant Vietnamese legal content or explanation.
- 7: English works but weaker than Vietnamese.
- 4: English returns generic fallback only.
- 0: English breaks flow.

### 7. Context Retention - 10 points

- 10: situation carries across Analyze, Similar Cases, Evidence Gap, Actions.
- 7: carries across some modules.
- 4: prefill works but does not auto-run or loses important context.
- 0: user must retype everywhere.

### 8. Stability And Fallback - 10 points

- 10: API failures/vector failures show friendly fallback.
- 7: most failures handled.
- 4: silent loaders or confusing errors.
- 0: white screen / HTTP 500 visible to user.

### 9. Dashboard And Behavior Loop - 10 points

- 10: dashboard reflects real user behavior and feedback affects later ranking.
- 7: dashboard has partial real metrics.
- 4: mostly static/demo data.
- 0: dashboard broken.

### 10. MVP Readiness - 10 points

- 10: a user can complete a full legal-analysis-to-action journey.
- 7: demo-ready with minor rough edges.
- 4: promising but fragmented.
- 0: not demoable.

## Test Personas

### Persona A - Vietnamese family-law user

User id:

```text
demo_user_family
```

Scenario:

```text
Tôi muốn ly hôn, có hai con, tôi muốn nuôi cả hai bé và muốn biết tài sản chung sẽ được chia như thế nào.
```

Expected focus:

- family law / civil context;
- child custody;
- asset division;
- evidence gap;
- similar cases;
- action plan.

### Persona B - Vietnamese employee user

User id:

```text
demo_user_employee
```

Scenario:

```text
Công ty cho tôi nghỉ việc không báo trước và chưa trả lương tháng cuối, tôi cần làm gì?
```

Expected focus:

- labor law;
- termination rights;
- unpaid salary;
- deadline/timeline;
- evidence such as labor contract, payslip, messages.

### Persona C - SME contract user

User id:

```text
demo_user_sme
```

Scenario:

```text
Công ty tôi chuẩn bị ký hợp đồng dịch vụ, điều khoản phạt và thanh toán đang bất lợi, hãy kiểm tra rủi ro.
```

Expected focus:

- contract review;
- clause risk;
- payment obligations;
- penalty clause;
- safer revised clauses.

### Persona D - English query user

User id:

```text
demo_user_english
```

Scenario:

```text
My employer terminated my labor contract without notice in Vietnam. What rights do I have?
```

Expected focus:

- English understood;
- Vietnamese labor-law retrieval;
- cross-language note;
- citations or clear fallback.

## Required Test Scenarios

### Scenario 1 - Basic Vietnamese Legal Analysis

Steps:

1. Open `/analyze`.
2. Set user `demo_user_family`.
3. Enter family-law scenario.
4. Submit.
5. Wait for result.
6. Gemini evaluates:
   - correct domain?
   - enough legal basis?
   - recommendation cards useful?
   - no hallucinated certainty?

Pass:

- result appears;
- next-best-action cards appear;
- at least one action is relevant to custody/evidence/similar cases.

### Scenario 2 - Recommendation Click And Context Retention

Steps:

1. From Scenario 1 result, click `Vụ việc tương tự` or recommended similar-cases card.
2. Verify `/similar-cases` loads.
3. Verify situation is prefilled or auto-run.
4. Verify results appear.

Pass:

- user does not need to retype;
- similar cases are relevant;
- page has no infinite loader.

### Scenario 3 - Same Query, Different Persona

Steps:

1. Run same query with `demo_user_family`.
2. Save top 5 recommendation action ids.
3. Switch to `demo_user_employee` or `demo_user_sme`.
4. Run same query.
5. Compare top 5.

Pass:

- order or explanation differs;
- legal relevance still remains correct;
- Gemini can explain the difference.

### Scenario 4 - Feedback Loop

Steps:

1. On Analyze result, mark `similar_cases` useful.
2. Dismiss one less relevant recommendation.
3. Submit a similar query again.
4. Compare ranking.

Pass:

- useful recommendation gets visible positive state;
- later ranking or explanation changes;
- no card disappears permanently across unrelated contexts unless dismissed by design.

### Scenario 5 - Community Similar Cases

Steps:

1. Search Similar Cases with a new situation.
2. Verify community section exists.
3. Check if community cases have:
   - anonymized summary;
   - resolution summary;
   - recommended steps;
   - no phone/email/address/CCCD/private name.

Pass:

- community section renders;
- no PII appears;
- Gemini scores usefulness >= 7/10.

### Scenario 6 - Cross-Language Query

Steps:

1. Set user `demo_user_english`.
2. Open Analyze or Law Search.
3. Enter English labor-law query.
4. Follow recommendation into law search/similar cases if suggested.

Pass:

- app does not reject English;
- results mention Vietnamese legal context;
- cross-language retrieval/fallback is understandable.

### Scenario 7 - Dashboard Behavior

Steps:

1. Perform 2-3 interactions as one persona.
2. Open Dashboard.
3. Check metrics and recommendations.

Pass:

- dashboard not empty after interactions;
- data source is clear;
- recommendations reflect persona/domain.

### Scenario 8 - Error And Fallback Experience

Steps:

1. Simulate backend unavailable if runner supports it, or call route with short/random input.
2. Verify user-facing error.
3. Search similar cases with random text.

Pass:

- no white screen;
- no stale previous session answer for random input;
- validation message is friendly.

## Report Format

The Gemini QA runner must generate Markdown like:

```markdown
# Gemini Localhost QA Report - YYYY-MM-DD

## Overall Result

- MVP readiness: PASS / PARTIAL / FAIL
- Overall score: 0-100
- Critical blockers: N
- Major issues: N
- Minor issues: N

## Score Table

| Category | Score | Notes |
|---|---:|---|
| Page load/navigation | 8/10 | ... |
| Legal analysis | 7/10 | ... |
| Recommendation engine | 6/10 | ... |

## Scenario Results

### Scenario 1 - Basic Vietnamese Legal Analysis

- Status: pass/partial/fail
- User id:
- Input:
- What worked:
- What failed:
- Evidence:
- Gemini judgement:

## Issues

### [BLOCKER] Similar Cases route does not render results

- Step:
- Expected:
- Actual:
- Module:
- Suggested fix:

## MVP Gaps

1. ...
2. ...

## Next Fix Plan

1. ...
2. ...
```

## JSON Output Schema

The runner should also save a machine-readable report:

```json
{
  "overall_status": "partial",
  "overall_score": 74,
  "mvp_complete": false,
  "scores": {
    "page_load_navigation": 9,
    "legal_analysis": 7,
    "recommendation_engine": 6,
    "personalization": 5,
    "similar_cases": 7,
    "cross_language": 6,
    "context_retention": 8,
    "stability_fallback": 8,
    "dashboard_behavior": 6,
    "mvp_readiness": 7
  },
  "issues": [
    {
      "severity": "major",
      "module": "SimilarCases",
      "title": "Community cases are not visible",
      "expected": "Show anonymized community patterns",
      "actual": "Only official/demo cases shown",
      "suggested_fix": "Extend API response and UI section"
    }
  ],
  "next_plan": [
    "Implement community case pattern storage",
    "Add persona switcher",
    "Expose ranking signal explanation"
  ]
}
```

## Implementation Tasks

### Task 1 - Create QA Prompt And Scenario File

Create:

```text
qa/gemini_user_simulation_prompt.md
qa/gemini_user_scenarios.json
```

The JSON scenario file should contain:

- id;
- language;
- persona/user_id;
- route;
- input text;
- required assertions;
- scoring rubric keys.

### Task 2 - Create Local Runner

Create:

```text
scripts/gemini_localhost_user_qa.py
```

Responsibilities:

- start with frontend/backend URLs from env;
- verify both are reachable;
- run scenarios;
- call Gemini for judgement after each scenario;
- write Markdown and JSON reports;
- exit non-zero only for infrastructure failure, not product issues.

### Task 3 - Browser Automation

Preferred:

- Playwright Python.

Fallback:

- API-only smoke if browser automation is unavailable.

The runner should clearly mark:

```text
browser_mode: full | api_fallback
```

### Task 4 - Gemini Evaluation Adapter

Create a small adapter:

```text
src/qa/gemini_evaluator.py
```

Or keep it inside script for MVP.

Responsibilities:

- send page summary and scenario context to Gemini;
- request structured JSON judgement;
- retry once on invalid JSON;
- sanitize screenshots/text before sending.

### Task 5 - Auto Fix-Plan Draft

If `mvp_complete=false`, write:

```text
docs/07-implementation/phase24-gemini-qa-fix-plan.md
```

This file should list:

- blockers;
- major issues;
- suggested order of implementation;
- tests to add.

## Definition Of Done

Phase 24 plan is implemented when:

- Gemini runner can execute at least 8 scenarios locally.
- Reports are generated in Markdown and JSON.
- Vietnamese and English flows are covered.
- Gemini can score MVP readiness.
- Issues are grouped by severity/module.
- A follow-up fix plan is auto-created when MVP is incomplete.
- The runner does not store private user data in reports beyond sanitized test inputs.

## First Manual Run Checklist

Before running Gemini QA:

```bash
# Backend
python -m uvicorn src.api.app:create_app --host 0.0.0.0 --port 8001

# Frontend
cd frontend
npm run dev -- --port 3000 --host 0.0.0.0
```

Then:

```bash
set GEMINI_API_KEY=...
set GEMINI_MODEL=gemini-3.5-flash
python scripts/gemini_localhost_user_qa.py
```

Expected outputs:

```text
reports/gemini_localhost_qa_YYYY-MM-DD.md
reports/gemini_localhost_qa_YYYY-MM-DD.json
docs/07-implementation/phase24-gemini-qa-fix-plan.md
```

