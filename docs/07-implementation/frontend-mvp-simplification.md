# Frontend MVP Simplification

Date: 2026-05-24

## Problem

The frontend had too many modules exposed as equal-weight navigation items. This made the product feel like a list of internal capabilities instead of a legal workflow.

Before simplification, the sidebar exposed many independent entries:
- Overview
- Analyze
- Journey
- Timeline
- Action planner
- Law search
- Similar cases
- Evidence gap
- Contract review
- Clause coach
- Clause search
- Documents
- Templates
- Risks
- Compliance Radar
- Checklists
- History
- Profile

This is powerful, but not MVP-friendly. A legal user should not need to understand the system architecture before getting help.

## Target MVP Flow

The product should center on this flow:

```text
Legal situation
-> legal analysis
-> evaluation and risk position
-> cited legal basis
-> recommended actions
-> optional specialized modules
```

The primary MVP entry point is:

```text
Phân tích pháp lý
```

All other modules should support this result instead of competing with it.

## New Information Architecture

### Primary Navigation

The sidebar now exposes only the main entry points first:
- Tổng quan
- Phân tích pháp lý
- Hồ sơ của tôi

### Grouped Capability Areas

Specialized modules are grouped by user intent:

#### Hồ sơ vụ việc
- Hành trình pháp lý
- Tiến trình & thời hạn
- Thiếu chứng cứ
- Kế hoạch hành động

Purpose:
- Track where the case is
- Identify missing documents
- Turn analysis into steps

#### Tra cứu & dẫn chứng
- Tra cứu điều luật
- Vụ việc tương tự
- Tài liệu
- Lịch sử phân tích

Purpose:
- Validate the analysis
- Find authority and comparable cases
- Reopen previous reasoning

#### Hợp đồng & điều khoản
- Rà soát hợp đồng
- Tư vấn điều khoản
- Tìm điều khoản tương tự
- Mẫu hợp đồng

Purpose:
- Handle contract-heavy workflows without cluttering the general legal flow

#### Rủi ro & tuân thủ
- Đánh giá rủi ro
- Compliance Radar
- Checklist tuân thủ

Purpose:
- Convert analysis into compliance/risk controls

## UI Changes

### `frontend/src/components/layout/Sidebar.tsx`

Changed from a flat long menu to:
- primary actions
- collapsible groups
- active group auto-open
- clearer labels
- compact MVP guidance block

Result:
- fewer visible choices at first glance
- related modules are still available
- sidebar reflects legal workflow instead of code modules

### `frontend/src/pages/Analyze.tsx`

Added a related-module panel inside analysis results:

```text
Dùng tiếp với module liên quan
```

From a completed analysis, users can jump to:
- Kiểm tra chứng cứ
- Tra cứu điều luật
- Vụ việc tương tự
- Đánh giá rủi ro
- Kế hoạch hành động
- Tiến trình pháp lý
- Rà soát hợp đồng
- Checklist tuân thủ
- Hành trình pháp lý

Navigation passes contextual state:
- detected domain
- session ID
- trace ID
- summary
- citations

This makes the analysis result the hub for the whole product.

## MVP Behavior

The user can now:

1. Start from `Phân tích pháp lý`.
2. Describe a situation.
3. Get:
   - position score
   - legal domain
   - full assessment
   - related laws
   - recommended actions
   - warnings
   - reasoning trace
4. Continue into specialized modules from the result itself.

This satisfies the intended MVP:

```text
phân tích pháp lý -> đưa gợi ý và đánh giá -> có dẫn chứng -> dùng được toàn bộ module liên quan
```

## Validation

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Result:
- TypeScript check: passed
- Production build: passed

Backend regression subset:

```bash
python -m pytest tests\api\test_phase10_api.py tests\api\test_phase14_api.py -q
```

Result:
- `29 passed`

## React Best-Practices Review

Checked after editing multiple TSX files:
- Hooks are not conditional.
- Sidebar group state is colocated.
- Route navigation uses semantic buttons and `NavLink`.
- Route-level lazy loading from Phase 15 remains intact.
- New analysis shortcuts use stable route paths and pass context through `navigate(..., { state })`.
- No new global state or prop drilling was introduced.

## Remaining Recommendations

1. Rename/clean mojibake strings across the frontend so source files are readable and maintainable.
2. Let specialized pages consume `location.state` to prefill inputs from analysis context.
3. Consider merging some pages in the future:
   - `Timeline`, `EvidenceGap`, and `Actions` could become tabs under `Hồ sơ vụ việc`.
   - `ClauseCoach`, `ClauseSearch`, and `Templates` could become tabs under `Hợp đồng`.
   - `Risks`, `ComplianceRadar`, and `Checklists` could become tabs under `Rủi ro & tuân thủ`.
4. Add browser smoke tests for:
   - sidebar group expand/collapse
   - analysis result shortcuts
   - mobile bottom navigation

## Context Handoff Update

Added `frontend/src/lib/analysisContext.ts` as a shared helper for reading analysis navigation state. It normalizes:
- `domain`
- `sessionId`
- `traceId`
- `summary`
- `citations`

Specialized modules now consume the analysis context when opened from the legal analysis result:
- `frontend/src/pages/Journey.tsx`
- `frontend/src/pages/Timeline.tsx`
- `frontend/src/pages/EvidenceGap.tsx`
- `frontend/src/pages/Actions.tsx`
- `frontend/src/pages/LawSearch.tsx`
- `frontend/src/pages/SimilarCases.tsx`
- `frontend/src/pages/Risks.tsx`
- `frontend/src/pages/Contract.tsx`
- `frontend/src/pages/Checklists.tsx`

This turns the MVP into a connected workflow:

```text
Phan tich phap ly
-> goi y va danh gia
-> dan chung
-> mo module chuyen sau
-> module co san ngu canh vu viec
```

Notes:
- Situation-based modules prefill their main input from the analysis summary.
- Domain-aware modules reuse the detected legal domain where the API supports it.
- Contract/checklist modules map the detected domain to a reasonable starting category.
- Modules do not auto-submit on navigation except `Journey`, which already had that pattern.

Validation after context handoff:
- `npm run lint`: passed
- `npm run build`: passed
- Dev-server smoke: `/`, `/analyze`, `/journey`, `/evidence-gap`, `/law-search`, `/similar-cases`, `/risks`, `/contract`, `/checklists` all returned HTTP 200.
