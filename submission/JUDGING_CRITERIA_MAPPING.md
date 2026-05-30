# Judging Criteria Mapping — LexAI / ULKA

Ánh xạ từng tiêu chí chấm điểm vào bằng chứng cụ thể trong dự án.

---

## Tiêu chí 1: Sáng tạo / Tính nguyên bản — 30%

### Điểm khác biệt cốt lõi

**LexAI không phải chatbot pháp lý thông thường.** Điểm sáng tạo nằm ở:

#### 1.1 Evidence-grounded legal reasoning

Hầu hết legal AI chỉ nhận câu hỏi → trả lời. LexAI còn làm thêm:
- Trích xuất **evidence status** từ input: `land_certificate = PRESENT`, `ubnd_mediation = PRESENT_FAILED`
- Lưu evidence vào session snapshot để cross-turn consistency
- Kiểm tra output mâu thuẫn với evidence đã biết → rewrite/remove

```python
# OutputValidator — không có trong chatbot thông thường
if evidence["land_certificate"] == "PRESENT":
    # Remove actions containing "thu thập sổ đỏ"
    actions = [a for a in actions if not _matches_land_supplement(a)]
```

#### 1.2 Context-aware action templates

Cùng domain dat_dai nhưng hai tình huống khác nhau → hai action list khác nhau:

| Tình huống | Action template |
|---|---|
| Chưa hòa giải | `_DOMAIN_RECOMMENDED_ACTIONS["dat_dai"]` — gồm UBND mediation step |
| Đã hòa giải không thành | `_DAT_DAI_POST_MEDIATION_ACTIONS` — gồm chuẩn bị khởi kiện |

Không phải LLM quyết định — là deterministic logic được test.

#### 1.3 QA release gate như một sản phẩm kỹ thuật

Không chỉ "chạy được là xong". Hệ thống có:
- 365 automated tests
- Benchmark 30 queries với domain accuracy metrics
- Release gate script tự động PASS/FAIL GA/Beta
- Manual QA 15 scenarios với P0-sensitive cases
- Hard gates: P0 contradictions = 0, forbidden phrases = 0, 500 errors = 0

Đây là **engineering culture** ít gặp trong hackathon projects.

#### 1.4 Legal AI cho tiếng Việt với no-diacritics support

- Domain classifier xử lý cả tiếng Việt có dấu lẫn không dấu
- `_VI_INDICATORS_NODIAC`: detect "so do", "hoa giai", "sa thai"
- Q26 benchmark: "so do cua toi bi hang xom tranh chap" → `dat_dai` ✅

#### 1.5 Minh bạch về limitation

Hệ thống có release gate và **tự báo cáo** khi không đủ điều kiện GA:
- `case_embedding_index` không tạo được → `fallback_demo_rate = 100%` → GA FAIL
- Demo cases có `is_demo=True` badge — không bao giờ giả là kết quả thật

**Tóm tắt cho giám khảo:** "Chúng tôi không build chatbot — chúng tôi build pipeline kiểm chứng. Sáng tạo là ở lớp evidence extraction + output validation, không phải ở UI đẹp."

---

## Tiêu chí 2: Triển khai kỹ thuật — 30%

### Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11) |
| Database | MongoDB Atlas M0 |
| Vector Search | MongoDB Atlas Vector Search — 384-dim cosine |
| Embedding | sentence-transformers `paraphrase-multilingual-MiniLM-L12-v2` |
| LLM | OpenAI API (tool-calling, max 4 rounds) |
| Frontend | React 19 + TypeScript + Vite + Tailwind |
| Session store | MongoDB (24h TTL) |
| Job storage | SQLite (document/job metadata) |
| Test | pytest (365 tests) |

### MongoDB Technical Implementation

**Collections:** 9 collections, 3 active vector search indexes  
**Aggregation pipelines:**
- `$vectorSearch` với numCandidates=100, domain filter, threshold=0.55
- `$addFields` để extract `{ $meta: "vectorSearchScore" }`
- `$match` score threshold
- `$sort` by score
- `$group` cho behavior analytics

**Data isolation model:**
```
is_global=True  → admin docs → visible to all users
is_global=False → user docs  → only visible to owner
Query filter: { $or: [{ user_id }, { is_global: true }] }
```

### Retrieval Fusion (Signal engineering)

```
FusionScore = 0.45 × vector_signal      # MongoDB $vectorSearch
            + 0.20 × bm25_signal        # TF keyword density
            + 0.25 × graph_signal       # Law reference BFS expansion
            + 0.10 × behavior_signal    # Collaborative filter
```

Mỗi signal được min-max normalize độc lập trước khi fusion.

### Testing

| Suite | Count | Approach |
|---|---|---|
| Engine unit | ~120 | QueryPlanner, orchestrator, retrieval |
| Evidence | ~60 | EvidenceExtractor, normalization |
| API | ~80 | Endpoint validation, smoke tests |
| S-05 regression | 25 | Post-mediation detection + action suppression |
| Total | **365** | All pass |

### Benchmark

- 30 queries (6 domains + general + no-diacritics + multi-domain)
- Mode: `http` — live backend (không mock)
- Metrics: top-1/top-3 accuracy, cross-domain error, empty rate, fallback rate

### Key Technical Decisions

1. **Stage 1 không dùng LLM** — keyword scoring thuần, <10ms, reproducible
2. **BM25 TF-only** — không cần corpus, hoạt động với any collection size
3. **OutputValidator là rule-based** — không phụ thuộc LLM availability
4. **Post-mediation fix là deterministic** — 16-phrase substring matching, <1ms, 100% predictable
5. **Demo fallback is labeled** — `is_demo=True` trong response, hiển thị badge trong UI

**Tóm tắt cho giám khảo:** "Hệ thống có 7-stage pipeline, 3 active vector search indexes trên MongoDB Atlas, 365 automated tests, và release gate tự động. Mọi decision đều có lý do kỹ thuật rõ ràng."

---

## Tiêu chí 3: Ảnh hưởng / Tiềm năng — 30%

### Bài toán thực tế

- Hơn **70% người Việt Nam** chưa từng tiếp cận dịch vụ pháp lý chính thức (theo khảo sát về tiếp cận tư pháp)
- Tranh chấp đất đai là loại tranh chấp phổ biến nhất tại Việt Nam
- Sai một bước trong thủ tục pháp lý (ví dụ: bỏ qua UBND mediation trước khi khởi kiện đất đai) → bị Tòa trả hồ sơ
- Chatbot pháp lý hiện tại hay bị lỗi mâu thuẫn — người dùng mất niềm tin

### Tác động trực tiếp

| Nhóm người dùng | Lợi ích |
|---|---|
| Người tranh chấp đất đai | Biết đúng bước tiếp theo (hòa giải → khởi kiện → Tòa) |
| Người bị sa thải trái phép | Biết quyền đòi trợ cấp thôi việc, thời hiệu khởi kiện |
| Người muốn ly hôn | Biết điều kiện, thủ tục, quyền nuôi con |
| Người ký hợp đồng | Biết điều khoản nào rủi ro, phạt vi phạm tối đa |

### Khả năng mở rộng

| Hướng | Cụ thể |
|---|---|
| Dữ liệu | Seed thêm legal cases → `case_embedding_index` → similar cases thật |
| Người dùng B2B | Doanh nghiệp vừa và nhỏ cần tư vấn hợp đồng/lao động thường xuyên |
| Workflow | Legal workflow automation — tạo đơn khởi kiện, checklist chuẩn bị hồ sơ |
| Luật sư | Lawyer-in-the-loop — AI draft, luật sư review và ký |
| Đa ngôn ngữ | English legal assistant (đã có multilingual embedding) |
| Gov integration | Kết nối với cổng thông tin pháp luật Việt Nam |

### Điểm khác biệt về tác động

Tác động thật sự không đến từ "trả lời được câu hỏi pháp lý" — chatbot nào cũng làm được. Tác động đến từ:

1. **Không gây hại** — không gợi ý sai bước, không re-suggest bước đã xong
2. **Minh bạch** — demo cases có badge, limitations được report rõ
3. **Có thể kiểm chứng** — 365 tests, benchmark, manual QA, release gate

**Tóm tắt cho giám khảo:** "Chúng tôi không đo impact bằng số user. Chúng tôi đo bằng số lần hệ thống KHÔNG gây hại — không tư vấn sai, không tự mâu thuẫn. Đó là tiêu chuẩn cao hơn cho AI trong lĩnh vực pháp lý."

---

## Tiêu chí 4: Trình bày / Demo — 10%

### Video Structure

10 phút, 7 segments rõ ràng:
1. Hook + Problem (0:45)
2. Solution overview (0:45)
3. Demo 1 — Đất đai có sổ đỏ (2:30)
4. Demo 2 — Bug story S-05 (1:45)
5. Demo 3 — Ly hôn đơn phương (1:15)
6. Architecture + MongoDB (1:00)
7. QA numbers + GA status (1:15)

### Những con số cần nhấn mạnh

| Số | Ý nghĩa |
|---|---|
| 365/365 tests pass | Engineering rigor |
| 96.6% top-1 accuracy | Domain classifier chất lượng |
| 0% cross-domain error | Không có sai lầm nghiêm trọng |
| 25 regression tests | S-05 bug được test đầy đủ |
| 7 stages pipeline | Kiến trúc phân tách rõ |
| 9 MongoDB collections | Dữ liệu phong phú |
| 3 active vector indexes | MongoDB Atlas được dùng thật |
| Beta PASS | Sẵn sàng deploy |

### Câu nói gây ấn tượng (có thể dùng trong video)

> "Điểm khác biệt không phải là trả lời thật dài — mà là không được tự mâu thuẫn với dữ kiện người dùng đã nói."

> "Chúng tôi không build chatbot. Chúng tôi build pipeline kiểm chứng: truy xuất, suy luận, kiểm tra mâu thuẫn, và release gate."

> "Release gate của chúng tôi tự phát hiện blocker và chặn GA — không cần ai nhớ check."

> "Fallback rate 100% là blocker infrastructure, không phải lỗi code. Hệ thống tự báo cáo điều này."

### Documents kèm theo

- System architecture diagram (Mermaid)
- MongoDB collections + indexes (screenshots)
- Retrieval benchmark report (96.6%)
- Release gate report (Beta PASS)
- Test suite output (365/365)
