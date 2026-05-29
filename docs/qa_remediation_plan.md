# LegalTech QA Remediation Plan

**Ngày cập nhật**: 2026-05-28  
**Phạm vi**: Evidence Gap, Analyze, Similar Cases, Recommendation/NBA, Retrieval/RAG, Legal Domain Classifier, Frontend hiển thị kết quả.  
**Mục tiêu chất lượng**: giảm hallucination, chống contradiction với facts người dùng, không gợi ý sai tài liệu/chứng cứ, và chuẩn hóa UI/API để phân biệt rõ `present`, `missing`, `uncertain`, `contradicted`.

---

## 1. Executive Summary

Bug blocker đã được xác định:

```text
User input: "tôi đã có sổ đỏ, Biên lai hoặc chứng từ thanh toán tiền mua đất"
Domain: Đất đai / BĐS
Wrong behavior: hệ thống vẫn gợi ý thiếu Sổ đỏ / Giấy chứng nhận quyền sử dụng đất.
```

Root cause là evidence flow cũ thiếu bước deterministic fact extraction trước khi LLM/recommendation sinh output. Hệ thống chỉ so checklist theo keyword đơn giản, không hiểu trạng thái `đã có`, `chưa có`, `bị mất`, `không rõ`, không normalize alias tiếng Việt, và frontend gom nhiều nhóm vào luồng “thiếu chứng cứ”.

Plan này chia remediation thành 5 lớp:

1. Evidence Accuracy Core.
2. API/LLM/Recommendation guards.
3. Frontend clarity.
4. Retrieval/domain confidence guards.
5. Regression QA suite và release gate.

---

## 2. Current Remediation Status

| Area | Status | Notes |
|---|---:|---|
| Evidence deterministic core | Done | Đã có extractor, normalizer, gap engine, schemas. |
| Bug “đã có sổ đỏ nhưng vẫn missing” | Done | Covered by unit + API regression tests. |
| Recommendation guard | Done | Present evidence không còn bị gợi ý “bổ sung/thu thập”. |
| LLM prompt guard | Done | Prompt yêu cầu tôn trọng `USER_FACTS` và evidence buckets. |
| Analyze/NBA guard | Done | Recommended actions được lọc qua present evidence. |
| Frontend evidence buckets | Done | UI tách `đã có`, `cần bổ sung`, `chưa rõ`, `mâu thuẫn`. |
| Retrieval/similar confidence metadata | Done | Response có `confidence`, `source`, `limitations`. |
| Formal frontend automated tests | Pending | Hiện đã lint/build + browser QA, chưa có UI test runner. |
| Session-level shared EvidenceContext | Pending | Cần lưu và tái sử dụng evidence facts xuyên Analyze/RAG/NBA. |
| Expanded legal-domain alias coverage | Pending | Alias map cần mở rộng theo dữ liệu production. |

---

## 3. Target Evidence Flow

```text
User input
  -> deterministic fact extraction
  -> Vietnamese alias normalization
  -> required checklist by legal domain
  -> evidence status classification
  -> contradiction detection
  -> recommendation guard
  -> LLM prompt guard
  -> API response buckets
  -> frontend grouped display
```

Required evidence statuses:

| Status | Meaning | UI behavior |
|---|---|---|
| `present` | Người dùng nói rõ đã có tài liệu/chứng cứ. | Hiển thị trong “Chứng cứ đã có”; chỉ gợi ý kiểm tra tính hợp lệ. |
| `missing` | Người dùng nói rõ chưa có/mất/không giữ, hoặc checklist high-priority chưa thấy. | Hiển thị trong “Chứng cứ cần bổ sung”. |
| `uncertain` | Input chưa đủ rõ, hoặc chứng cứ medium-priority chưa được xác nhận. | Hiển thị trong “Chứng cứ chưa rõ / nên xác minh”. |
| `contradicted` | Có cả tín hiệu có và không có. | Hỏi lại người dùng, không khẳng định thiếu. |

Hard rules:

- `present_evidence` không được xuất hiện trong `missing_evidence`.
- `present_evidence` không được bị recommendation gợi ý “bổ sung/thu thập/chuẩn bị”.
- LLM không được tự bịa evidence ngoài checklist nếu không có căn cứ.
- UI không hiển thị enum thô như `TITLE`, `CERTIFICATE`, `CONFIRMATION`.
- Coverage score phải tăng theo present evidence và không coi uncertain là missing tuyệt đối.

---

## 4. Implemented Fixes

### 4.1 Evidence Core

Files:

- `src/evidence/evidence_schemas.py`
- `src/evidence/evidence_normalizer.py`
- `src/evidence/evidence_extractor.py`
- `src/evidence/evidence_gap_engine.py`
- `src/services/evidence_gap_detector.py`

Changes:

- Added canonical evidence schema with `evidence_id`, `title`, `category`, `domain`, `priority`, `aliases`.
- Added deterministic Vietnamese fact extractor.
- Added alias normalization with accent folding and legal-domain mapping.
- Added `present`, `missing`, `uncertain`, `contradicted`.
- Preserved backward compatibility through `EvidenceGapDetector`.

Regression target:

```python
input_text = (
    "Tranh chấp về tài sản thừa kế đất đai giữa các anh chị em ruột. "
    "tôi đã có sổ đỏ, Biên lai hoặc chứng từ thanh toán tiền mua đất"
)
domain = "land"
```

Expected:

- `land_certificate`: `present`
- `payment_proof`: `present`
- `transfer_document`: `missing`
- `local_confirmation`: `missing`
- `land_map`: `uncertain`
- `witness`: `uncertain`
- `coverage_score > 0.33`

### 4.2 API Response

Files:

- `src/api/analysis_routes.py`
- `frontend/src/lib/api.ts`

Response now includes:

```json
{
  "domain": "dat_dai",
  "coverage_score": 0.42,
  "summary": "...",
  "present_evidence": [],
  "missing_evidence": [],
  "uncertain_evidence": [],
  "contradictions": [],
  "recommendations": [],
  "debug": {}
}
```

Debug remains optional and should only be returned when explicitly requested.

### 4.3 Recommendation Guard

Files:

- `src/evidence/evidence_gap_engine.py`
- `src/recommenders/situation_analyzer.py`
- `src/engine/orchestrator.py`
- `src/agents/legal_agent.py`

Rules:

- Remove or rewrite actions that ask users to supplement evidence already marked `present`.
- If evidence is present, recommendations can only ask to verify validity, original/certified copy, issue date, owner name, or content consistency.
- Actions should be generated from `missing_evidence` and `uncertain_evidence`, not raw checklist.

Example correct output:

```text
Bạn đã có Sổ đỏ / Giấy chứng nhận quyền sử dụng đất.
Hãy kiểm tra tên người đứng trên sổ, nguồn gốc cấp sổ, thời điểm cấp và bản sao công chứng.
```

### 4.4 LLM Prompt Guard

Files:

- `src/llm/prompts.py`
- `src/engine/orchestrator.py`
- `src/agents/legal_agent.py`

Prompt context now includes structured evidence facts:

```json
{
  "user_facts": [],
  "present_evidence": [],
  "missing_evidence": [],
  "uncertain_evidence": [],
  "contradictions": [],
  "domain": "dat_dai"
}
```

LLM must:

- Respect `USER_FACTS`.
- Never list `PRESENT_EVIDENCE` as missing.
- Ask follow-up questions for uncertain/contradicted items.
- Avoid invented checklist items.

### 4.5 Frontend Display

Files:

- `frontend/src/pages/EvidenceGap.tsx`
- `frontend/src/lib/api.ts`

Changes:

- Added sections:
  - `Chứng cứ đã có`
  - `Chứng cứ cần bổ sung`
  - `Chứng cứ chưa rõ / nên xác minh`
  - `Mâu thuẫn cần làm rõ`
- Added Vietnamese category labels.
- Coverage summary now reflects present/missing/uncertain counts.
- Browser QA confirmed no raw enum labels and no bad recommendation for `sổ đỏ`/`biên lai`.

---

## 5. Remaining Remediation Backlog

### R1. Shared EvidenceContext Across Session

**Priority**: High  
**Owner area**: Backend orchestration / session state  
**Suggested files**:

- `src/engine/orchestrator.py`
- `src/agents/legal_agent.py`
- `src/api/analysis_routes.py`
- `src/runtime/` or session store module if available

Problem:

Analyze, Evidence Gap, Similar Cases, RAG, and NBA may recompute evidence facts separately. Recompute drift can create inconsistent output.

Plan:

1. Create a serializable `EvidenceContext` object.
2. Persist it by `session_id` when evidence extraction runs.
3. Reuse it in Analyze, Similar Cases, Next Best Actions, and RAG.
4. Add a version field for future schema changes.

Acceptance criteria:

- Same user input produces one canonical evidence context across all modules.
- Analyze does not contradict Evidence Gap.
- NBA does not recommend present evidence.

### R2. Expand Legal Evidence Alias Coverage

**Priority**: High  
**Owner area**: Legal QA / evidence taxonomy  
**Suggested files**:

- `src/evidence/evidence_normalizer.py`
- `tests/evidence/`

Add aliases for:

- Land inheritance disputes.
- Household registration / residence confirmation.
- Bank transfer proofs.
- Handwritten sale agreements.
- Divorce custody conditions.
- Labor unilateral termination evidence.
- SME contract breach evidence.

Acceptance criteria:

- New aliases covered by unit tests.
- No alias may accidentally match negated facts as present.

### R3. Formal Frontend Tests

**Priority**: Medium  
**Owner area**: Frontend QA  
**Suggested files**:

- `frontend/src/pages/EvidenceGap.tsx`
- test runner config if introduced

Plan:

1. Add frontend testing stack if repo standard exists, otherwise choose lightweight Vitest + React Testing Library.
2. Mock Evidence Gap API response.
3. Assert UI renders:
   - `Chứng cứ đã có`
   - `Chứng cứ cần bổ sung`
   - `Chứng cứ chưa rõ / nên xác minh`
4. Assert raw enum strings are not visible.

Acceptance criteria:

- UI test fails if `TITLE`, `CERTIFICATE`, `CONFIRMATION`, `MAP`, or `WITNESS` is rendered to users.

### R4. Retrieval Domain Confidence Enforcement

**Priority**: Medium  
**Owner area**: Retrieval/RAG  
**Suggested files**:

- `src/api/retrieval_routes.py`
- `src/retrieval/`
- `tests/api/test_retrieval_similar_cases.py`

Plan:

1. Standardize confidence threshold by domain.
2. If retrieved document is off-domain or low-confidence, only use it as weak context, not a legal assertion.
3. Require `source`, `confidence`, and `limitations` in RAG response.
4. Add test for land query not being dominated by SME/contract documents due behavior history.

Acceptance criteria:

- Low-confidence RAG answer explicitly says limitations.
- Similar Cases do not return far-domain cases as high-confidence.

### R5. Contradiction UX

**Priority**: Medium  
**Owner area**: Frontend + API  
**Suggested files**:

- `src/evidence/evidence_gap_engine.py`
- `frontend/src/pages/EvidenceGap.tsx`

Plan:

1. Add specific clarification prompts for contradictions.
2. Example: `tôi có sổ đỏ nhưng bản gốc bị mất` should ask whether user has certified copy, photo, or registry extract.
3. Add UI action to convert a contradiction into resolved present/missing after user answers.

Acceptance criteria:

- Contradiction is never displayed as simple missing.
- Recommendation asks for clarification or legal validity check.

---

## 6. Regression Test Plan

### Backend Unit Tests

```bash
python -m pytest tests/evidence/test_evidence_extractor.py -q
python -m pytest tests/evidence/test_evidence_gap_engine.py -q
python -m pytest tests/evidence/test_evidence_recommendation_guard.py -q
```

Required cases:

| Case | Input | Expected |
|---|---|---|
| Present certificate | `tôi đã có sổ đỏ và biên lai chuyển khoản` | `land_certificate=present`, `payment_proof=present` |
| Missing certificate | `tôi chưa có sổ đỏ nhưng có giấy mua bán viết tay` | `land_certificate=missing`, `transfer_document=present` |
| Negation ordering | `không có giấy chứng nhận quyền sử dụng đất` | not present, must be missing |
| Alias | `tôi có GCN QSDĐ` | `land_certificate=present` |
| Contradiction | `tôi có sổ đỏ nhưng bản gốc bị mất` | `contradicted` or `uncertain`, not simple missing |
| Image bug | land inheritance + `đã có sổ đỏ, biên lai...` | certificate/payment present, not missing |

### API Tests

```bash
python -m pytest tests/api/test_evidence_gap_accuracy.py -q
python -m pytest tests/api/test_recommendation_next_best_action_api.py -q
python -m pytest tests/api/test_retrieval_similar_cases.py -q
python -m pytest tests/recommenders/test_next_best_action.py -q
```

API acceptance criteria:

- `"Sổ đỏ"` not in `missing_titles`.
- `"Biên lai"` not in `missing_titles`.
- `"Sổ đỏ"` in `present_titles`.
- `coverage_score > 0.33`.
- Recommendations do not contain `bổ sung sổ đỏ` or `thu thập biên lai` when present.

### Frontend Checks

```bash
cd frontend
npm run lint
npm run build
```

Manual/browser acceptance:

- Evidence Gap page loads.
- Result displays 3 evidence buckets.
- Raw enum labels are absent.
- Coverage message reflects present evidence.
- Present evidence is not shown inside missing group.

---

## 7. Manual QA Matrix

| Scenario | Input | Expected |
|---|---|---|
| Land case 1 | `Tranh chấp về tài sản thừa kế đất đai giữa các anh chị em ruột. tôi đã có sổ đỏ, Biên lai hoặc chứng từ thanh toán tiền mua đất` | Sổ đỏ + payment present; transfer/local confirmation missing; map/witness uncertain. |
| Land case 2 | `Tôi chưa có sổ đỏ, chỉ có giấy mua bán viết tay và người làm chứng.` | Sổ đỏ missing; transfer document + witness present. |
| Labor case | `Công ty cho tôi nghỉ việc không báo trước. Tôi có hợp đồng lao động, email thông báo nghỉ việc và bảng lương.` | Contract, termination notice/email, salary proof present; no duplicate supplement action. |
| Family case | `Tôi muốn ly hôn và nuôi con. Tôi có giấy đăng ký kết hôn, giấy khai sinh của con và sao kê lương.` | Three documents present; recommendations focus on childcare/living-condition evidence. |
| Contradiction case | `Tôi có sổ đỏ nhưng bản gốc bị mất.` | Ask clarification / certified copy / registry extract; do not classify as simple missing. |

---

## 8. Release Gate

Before merging:

- All backend evidence tests pass.
- API regression for the `sổ đỏ` bug passes.
- Existing recommendation/retrieval related tests pass.
- Frontend lint and build pass.
- Manual QA matrix is recorded with pass/fail notes.
- No raw category enum appears in the UI.
- No present evidence appears in missing/recommendation supplement actions.

Current verified baseline:

```bash
python -m pytest tests/evidence/test_evidence_extractor.py \
  tests/evidence/test_evidence_gap_engine.py \
  tests/evidence/test_evidence_recommendation_guard.py \
  tests/api/test_evidence_gap_accuracy.py \
  tests/api/test_recommendation_next_best_action_api.py \
  tests/api/test_retrieval_similar_cases.py \
  tests/recommenders/test_next_best_action.py -q
# 32 passed

cd frontend
npm.cmd run lint
# pass

npm.cmd run build
# pass
```

---

## 9. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Alias false positives | Present/missing classification wrong | Keep negation tests and require review for new aliases. |
| LLM ignores evidence context | Hallucinated recommendations | Keep prompt guard plus post-generation recommendation filter. |
| Domain misclassification | Wrong checklist/RAG sources | Add confidence threshold and show limitations. |
| Frontend fallback hides buckets | User sees “missing” only | Add frontend tests for bucket labels. |
| EvidenceContext drift | Analyze/NBA/RAG disagree | Implement shared session-level EvidenceContext. |

---

## 10. Next Recommended Sprint

1. Implement shared `EvidenceContext` persistence.
2. Add frontend automated tests for Evidence Gap buckets and category labels.
3. Expand alias map using real anonymized user queries.
4. Add contradiction resolution UX.
5. Tighten retrieval confidence gates for off-domain documents.
