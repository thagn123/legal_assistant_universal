# E2E Test Plan — LexAI / ULKA

> **Status**: Playwright not yet installed. This document defines the plan.
> **Decision**: Do NOT install Playwright in this sprint — adds ~500MB of browser binaries
>   and requires a running dev server. Add in a dedicated QA sprint when the beta server is stable.

---

## Current State

| Check | Status |
|---|---|
| Playwright installed | ❌ Not found in package.json |
| Cypress installed | ❌ Not found in package.json |
| Vitest / Testing Library | ❌ Not found |
| Dev server target | `http://localhost:3000` (Vite, `npm run dev`) |
| Backend target | `http://localhost:8001` (uvicorn) |

---

## Dependencies to Add (when ready)

```jsonc
// lexai-–-trợ-lý-pháp-lý-thông-minh UI/package.json — devDependencies
{
  "@playwright/test": "^1.46.0"
}
```

Install:
```bash
cd "lexai-–-trợ-lý-pháp-lý-thông-minh UI"
npm install --save-dev @playwright/test
npx playwright install chromium   # ~130MB — headless Chromium only
```

Config file: `playwright.config.ts` at repo root (or frontend dir):
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    headless: true,
    locale: 'vi-VN',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
```

---

## First Test Flow — Analyze Page (Recommended starting point)

File: `e2e/analyze_basic.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

const P0_FORBIDDEN = [
  'bạn chưa có sổ đỏ',
  'cần làm sổ đỏ trước',
  'không thể ly hôn đơn phương',
];

test.describe('Analyze Page — S-01 Sổ đỏ có sẵn', () => {
  test('no P0 contradiction when user states sổ đỏ present', async ({ page }) => {
    await page.goto('/');
    await page.click('a[href="/analyze"]');

    const textarea = page.getByPlaceholder(/mô tả tình huống/i);
    await textarea.fill('Tôi có sổ đỏ đứng tên mình nhưng hàng xóm lấn chiếm ranh giới đất 50cm. Tôi phải làm gì?');

    await page.getByRole('button', { name: /phân tích|gửi/i }).click();
    await page.waitForSelector('[data-testid="analysis-result"], .assessment-card', { timeout: 20_000 });

    const responseText = await page.locator('body').textContent();
    for (const phrase of P0_FORBIDDEN) {
      expect(responseText?.toLowerCase()).not.toContain(phrase);
    }
  });
});
```

---

## Planned Test Flows

### E2E-01 — Analyze: S-01 Sổ đỏ có sẵn (P0 contradiction check)
**Steps:**
1. Navigate to `/analyze`
2. Type: "Tôi có sổ đỏ đứng tên mình, hàng xóm lấn chiếm 50cm."
3. Click send
4. Wait for response card
5. Assert no P0 forbidden phrases in full page text

**Pass criteria:** Response appears, no forbidden phrases

---

### E2E-02 — Analyze: S-05 Hòa giải không thành (P0 divorce mediation)
**Steps:**
1. Navigate to `/analyze`
2. Type: "Hòa giải không thành, muốn ly hôn đơn phương. Làm gì tiếp?"
3. Wait for response
4. Assert: "không thể ly hôn đơn phương" NOT in text
5. Assert: "phải có sự đồng ý" NOT in text

---

### E2E-03 — Evidence Gap: Badge and coverage display
**Steps:**
1. Navigate to `/evidence-gap`
2. Input situation with sổ đỏ present
3. Submit
4. Verify "Bằng chứng đã có" section shows sổ đỏ
5. Verify coverage_score rendered as progress bar
6. Verify NO "xin cấp sổ đỏ" advice in text

---

### E2E-04 — Similar Cases: Demo badge renders
**Steps:**
1. Navigate to `/similar-cases`
2. Input: "Hàng xóm lấn đất tranh chấp ranh giới"
3. Submit
4. If any demo case shown, verify "Ví dụ tham khảo" badge visible
5. Verify domain label displayed (e.g. "Đất đai")

---

### E2E-05 — Dashboard: NBA chips clickable + prefill
**Steps:**
1. Navigate to `/` (Dashboard)
2. Verify Quick Classify panel renders
3. Type a situation and classify
4. Verify NBA action chips appear
5. Click one chip → navigate to correct page with prefilled context

---

### E2E-06 — History: Save + reload
**Steps:**
1. Complete an analysis on `/analyze`
2. Click Save button → toast appears "Đã lưu"
3. Navigate to `/history`
4. Verify saved item appears with correct type label
5. Click Download JSON → verify file downloads

---

### E2E-07 — Admin: Login + upload flow
**Steps:**
1. Navigate to `/admin/login`
2. Enter key: `lexai-admin-secret`
3. Click login → redirect to `/admin`
4. Navigate to Documents
5. Upload a small PDF file
6. Verify job appears in Jobs table with status indicator

---

## Command to Run (once installed)

```bash
# From repo root
npx playwright test --reporter=list

# Single test
npx playwright test e2e/analyze_basic.spec.ts --headed

# With specific base URL
E2E_BASE_URL=http://localhost:3000 npx playwright test
```

---

## Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| Frontend has no `data-testid` attributes | High | Add data-testid to key elements before E2E sprint |
| Backend must be running | Medium | webServer config auto-starts frontend; backend must be started manually |
| Vietnamese input in headless browser | Low | Playwright handles UTF-8 natively; test with `page.fill()` |
| Flaky due to LLM latency | Medium | Set `timeout: 20_000` on response-wait steps; stub LLM in CI |
| 500MB browser binaries in repo | Low | Use `--save-dev` + `.gitignore node_modules`; CI installs fresh |
| Animation/transition delays | Low | Use `waitForSelector` not `waitForTimeout` |

---

## Prerequisites Before E2E Sprint

- [ ] Add `data-testid="analysis-result"` to response card in `Analyze.tsx`
- [ ] Add `data-testid="evidence-gap-result"` to result section in `EvidenceGap.tsx`
- [ ] Add `data-testid="similar-cases-list"` to case list in `SimilarCases.tsx`
- [ ] Add `data-testid="nba-chip"` to each NBA action chip in `Dashboard.tsx`
- [ ] Confirm dev server port (currently 3000) and backend port (8001) in `.env.test`
- [ ] Decide: stub or live LLM in CI (recommend stub via `MSW` mock service worker)
