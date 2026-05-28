# Phase 23 - Personalized Community Intelligence MVP

Date: 2026-05-28

## Product Goal

Hoàn thiện MVP để người dùng có thể trải nghiệm trọn vẹn:

1. Cùng một truy vấn nhưng 2-3 người dùng demo khác nhau nhận kết quả và thứ tự gợi ý khác nhau.
2. Người dùng có thể truy tìm vụ việc tương tự từ kho hệ thống và từ các tình huống cộng đồng đã được ẩn danh.
3. Hệ thống lưu lại tóm tắt tình huống, hướng giải quyết và tín hiệu hành vi, nhưng không lưu thông tin riêng tư.
4. Recommendation engine hoạt động end-to-end: behavior logs -> MongoDB Aggregation -> behavior score -> reranking -> UI.
5. Các tính năng chính chạy được trên web đã deploy, có fallback khi MongoDB vector search hoặc AI provider không sẵn sàng.

## MVP Scope

Tập trung vào luồng có giá trị sản phẩm cao nhất:

```text
Persona user
  -> nhập tình huống pháp lý
  -> phân tích pháp lý
  -> next-best-action được cá nhân hóa
  -> xem vụ việc tương tự
  -> lưu/tương tác/feedback
  -> Dashboard và lần tìm kiếm sau thay đổi theo hành vi
```

Không mở rộng quá nhiều module. Phase này chỉ cần hoàn thiện trải nghiệm cốt lõi:

- `Analyze`
- `SimilarCases`
- `EvidenceGap` hoặc `Actions`
- `Dashboard`
- `Profile`/persona switcher đơn giản

## Privacy Rule

Tuyệt đối không lưu raw private details vào kho cộng đồng.

Chỉ lưu bản tóm tắt đã ẩn danh:

- `summary`: mô tả trung tính, không tên người, số điện thoại, địa chỉ cụ thể, CCCD, email.
- `legal_domain`
- `user_goal`
- `resolution_summary`
- `recommended_steps`
- `citations`
- `tags`
- `source_user_segment`: ví dụ `parent_custody`, `employee_termination`, `contract_sme`; không lưu user id công khai.
- `created_at`, `last_seen_at`, `popularity`

Raw user text chỉ có thể nằm trong conversation/session riêng của user, không đưa vào community case pattern.

## Demo Personas

Tạo 3 persona đơn giản để chứng minh cá nhân hóa:

### 1. `demo_user_family`

- Quan tâm: ly hôn, nuôi con, chia tài sản.
- Hành vi seed:
  - click `similar_cases`
  - useful cho `evidence_gap`
  - save kết quả về quyền nuôi con
- Kết quả kỳ vọng:
  - ưu tiên chứng cứ nuôi con, timeline tòa án, vụ việc tương tự gia đình.

### 2. `demo_user_employee`

- Quan tâm: sa thải, lương, BHXH, bồi thường.
- Hành vi seed:
  - click `law_search`
  - useful cho `timeline`
  - save tài liệu lao động.
- Kết quả kỳ vọng:
  - ưu tiên luật lao động, thời hiệu khiếu nại, chứng cứ hợp đồng lao động.

### 3. `demo_user_sme`

- Quan tâm: hợp đồng, điều khoản phạt, thanh toán, tranh chấp doanh nghiệp.
- Hành vi seed:
  - click `contract`
  - useful cho `clause_search`
  - dismiss `similar_cases` nếu không liên quan.
- Kết quả kỳ vọng:
  - ưu tiên rà soát hợp đồng, tìm điều khoản, rủi ro nghĩa vụ thanh toán.

## Data Model Proposal

### Collection/Table: `community_case_patterns`

MongoDB primary, SQLite fallback optional for local demo.

```json
{
  "pattern_id": "ccp_...",
  "summary": "Người dùng muốn ly hôn, nuôi con nhỏ và chia tài sản chung.",
  "legal_domain": "gia_dinh",
  "user_goal": ["divorce", "child_custody", "asset_division"],
  "resolution_summary": "Cần chuẩn bị hồ sơ ly hôn, chứng cứ điều kiện nuôi con, tài liệu chứng minh tài sản chung/riêng.",
  "recommended_steps": [
    "Thu thập giấy đăng ký kết hôn và giấy khai sinh của con",
    "Chuẩn bị chứng cứ thu nhập, nơi ở, thời gian chăm sóc con",
    "Phân loại tài sản chung và tài sản riêng"
  ],
  "citations": ["Luật Hôn nhân và Gia đình"],
  "tags": ["ly_hon", "nuoi_con", "chia_tai_san"],
  "embedding": [0.01, 0.02],
  "language": "vi",
  "source": "user_search_anonymized",
  "source_user_segment": "parent_custody",
  "popularity": {
    "impressions": 0,
    "clicks": 0,
    "saves": 0,
    "useful": 0,
    "not_useful": 0
  },
  "created_at": "2026-05-28T00:00:00Z",
  "last_seen_at": "2026-05-28T00:00:00Z"
}
```

### Existing Signals To Reuse

- `X-User-ID` header already supports demo users.
- `frontend/src/lib/api.ts` already has `getUserId()` and `setUserId()`.
- `interactions` already logs recommendation events.
- `conversation_sessions` already stores per-user sessions.
- `NextBestActionRecommender` already accepts behavior scores.
- `RecommendationRanker` already has 6-signal concept.
- `/retrieval/similar-cases` already has vector/keyword/demo fallback.

## Required User Flows

### Flow A - Two Users, Same Query, Different Ranking

Input for both users:

```text
Tôi muốn ly hôn, có hai con và muốn biết tài sản chung sẽ được chia như thế nào.
```

Expected:

- `demo_user_family`: top actions should prioritize custody evidence, similar family cases, action plan.
- `demo_user_sme`: top actions should show lower family-specific behavior boost and may prioritize contract/risk only if context supports it; legal relevance must still keep family-law results valid.

Acceptance:

- API response includes visible `personalization_explanation` or `ranking_signals`.
- UI shows "Cá nhân hóa theo hồ sơ/hành vi của bạn".
- Test proves order differs between two user ids after seeded behavior.

### Flow B - Community Similar Case Search

User enters a situation and opens Similar Cases.

Expected:

- Results include official/demo legal cases and anonymized community patterns.
- Each community item shows:
  - summarized situation,
  - resolution summary,
  - recommended steps,
  - no private details,
  - why it matches.

Acceptance:

- A new search creates/updates an anonymized pattern record.
- PII redaction test passes.
- UI has a section: "Vụ việc cộng đồng đã tìm".

### Flow C - Feedback Improves Later Recommendations

User marks `similar_cases` useful and dismisses `contract`.

Expected:

- Later next-best-action ranking increases `similar_cases` for compatible contexts.
- `contract` is not permanently hidden, but gets a negative behavior nudge.

Acceptance:

- Tests prove `recommendation_feedback=useful` changes score within bounded range.
- Legal relevance remains primary signal.

### Flow D - Cross-language Retrieval

User asks:

```text
Vietnam labor termination without notice, what rights do I have?
```

Expected:

- System detects English query.
- Results can retrieve Vietnamese legal content through embeddings/canonical aliases.
- UI shows language note: "Đã tìm kiếm chéo ngôn ngữ".

Acceptance:

- Unit test covers English query returning Vietnamese labor result.
- Fallback keyword alias map covers common English/Vietnamese legal terms.

### Flow E - Deterministic Fallback

Disable OpenAI or simulate AI failure.

Expected:

- Search, similar cases, next-best actions and dashboard still work.
- Analysis response clearly says it is deterministic/fallback if needed.

Acceptance:

- Backend test with missing AI key passes.
- Frontend shows friendly fallback state, no white screen.

## Implementation Phases

### Phase 23.1 - Audit And Contracts

- Confirm existing user identity path through `X-User-ID`.
- Document current endpoints and missing response fields.
- Define exact schemas for:
  - community case pattern;
  - personalized search result;
  - ranking signal explanation.

Done when:

- API contracts are written.
- Tests to add are listed before coding.

### Phase 23.2 - Demo Personas And Seed Data

- Add seed data for 3 demo users.
- Seed behavior interactions for each persona.
- Seed anonymized community case patterns.
- Add frontend persona switcher for demo mode.

Done when:

- Switching user changes `X-User-ID`.
- Dashboard and recommendations reflect selected persona.

### Phase 23.3 - Community Similar Cases

- Add storage methods:
  - create/update anonymized case pattern;
  - search case patterns by vector/keyword;
  - increment popularity counters.
- Add privacy sanitizer:
  - strip phone, email, CCCD-like numbers, exact addresses, names when possible.
  - summarize to neutral legal facts.
- Extend `/retrieval/similar-cases` to return:
  - official cases;
  - community patterns;
  - search mode;
  - match reasons.

Done when:

- Similar Cases page shows a community section.
- New searches generate safe anonymized records.

### Phase 23.4 - Collaborative Intelligence In MongoDB

- Implement MongoDB Aggregation Pipeline for peer behavior:
  - match current user's viewed/saved/clicked domains/actions;
  - find peer users with overlapping legal domains/actions;
  - aggregate documents/cases/actions peers used;
  - exclude items current user already dismissed;
  - return scored recommendations.
- Keep SQLite fallback for local/demo.

Done when:

- `/recommendations/behavior/peers` returns meaningful results for seeded personas.
- Dashboard can display peer/community-based suggestions.

### Phase 23.5 - Deep Personalization And 6-Signal Reranking

Apply 6 signals consistently:

1. semantic similarity;
2. behavior score;
3. graph relevance;
4. freshness;
5. popularity;
6. accepted/useful rate.

Tasks:

- Add `ranking_signals` to recommendation responses.
- Add bounded behavior boost/penalty.
- Add `personalization_explanation` for UI.
- Add tests proving 2 users get different ranking for same query.

Done when:

- Same query with `demo_user_family` and `demo_user_employee` returns different order.
- Response explains why.

### Phase 23.6 - Cross-Language Retrieval

- Add/verify language detection for retrieval endpoints.
- Add bilingual alias map for MVP:
  - divorce/ly hôn;
  - custody/nuôi con;
  - termination/sa thải/chấm dứt hợp đồng;
  - contract penalty/phạt vi phạm;
  - land dispute/tranh chấp đất.
- Ensure canonical IDs are used where available.
- Add UI note when cross-language expansion is used.

Done when:

- English query can return Vietnamese legal results in tests and demo.

### Phase 23.7 - Cross-Session User Memory

- Persist user's legal context summaries by user id.
- Ensure memory does not leak across demo personas.
- Add profile/memory preview in UI.
- Add safe controls:
  - clear memory;
  - edit/remove sensitive user profile fields.

Done when:

- User can return later and the app pre-fills or references prior legal context.
- Different users see different memory.

### Phase 23.8 - GraphRAG Evidence Expansion

- Use existing graph traversal to enrich retrieval with related laws.
- Show relation labels:
  - cites;
  - amends;
  - overrides;
  - related.
- Keep provenance/citation requirements strict.

Done when:

- Similar/law search can show at least one graph-expanded related result when data exists.
- Fallback does not invent graph relations.

### Phase 23.9 - Deterministic Fallback And Deployment Stability

- Simulate Mongo vector failure and AI failure.
- Ensure all MVP endpoints return meaningful results:
  - `/intelligence/analyze`
  - `/recommendations/next-best-actions`
  - `/retrieval/similar-cases`
  - `/recommendations/behavior/digest`
  - `/recommendations/behavior/peers`
- Ensure deployed frontend has friendly error/fallback states.

Done when:

- E2E smoke passes locally and against deployed base URL when configured.

## MVP Acceptance Criteria

The MVP is complete when:

- A user can switch between at least 2 demo personas.
- Same query gives different recommendation order for different personas.
- Similar Cases includes anonymized community patterns.
- New user searches can be summarized and saved without private details.
- Dashboard shows behavior/persona-driven metrics.
- Useful/not-useful/dismiss affects later recommendation ranking.
- Cross-language query returns a valid result or safe fallback.
- GraphRAG relation labels appear where data supports them.
- AI provider failure does not break search/recommendation flows.
- `npm run lint`, `npm run build`, and targeted backend tests pass.

## Suggested Test Commands

```bash
python -m pytest tests/api/test_recommendation_next_best_action_api.py -q
python -m pytest tests/api/test_behavior_conversation_api.py -q
python -m pytest tests/recommenders/test_next_best_action.py -q
python -m pytest tests/api/test_retrieval_similar_cases.py -q
python -m pytest tests/api/test_phase23_personalization_mvp.py -q

cd frontend
npm run lint
npm run build
```

