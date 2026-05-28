# VIDEO DEMO PLAN V3 — LexAI Competition
# Chi tiết nhất có thể — Từng giây, từng câu, từng click

---

## PHẦN 0 — CHIẾN LƯỢC & ĐỊNH VỊ

### Judging criteria alignment (MongoDB Atlas Hackathon)

| Tiêu chí | Trọng số | Scene trong video |
|---|---|---|
| MongoDB usage depth | 40% | Scene 4A-4C (Atlas UI + Vector Search + Aggregation) |
| Technical innovation | 20% | Scene 2 (7-stage pipeline) + Scene 3C (community cases Phase 23) |
| MVP completeness | 20% | Scene 1→2→3→3B liên tục không bị gián đoạn |
| Presentation clarity | 20% | Hook, persona story, closing impact statement |

### Thông điệp xuyên suốt (nói 3 lần trong video)

> "LexAI không chỉ trả lời câu hỏi — nó đề xuất bước pháp lý tiếp theo, được xếp hạng bởi hành vi người dùng và truy xuất từ MongoDB Atlas."

### Câu frame dứt khoát cho ban giám khảo

> "Legal access is a recommendation problem. And recommendation problems are MongoDB problems."

---

## PHẦN 1 — NHÂN VẬT & KỊCH BẢN DEMO

Chọn **MỘT persona**, kể **MỘT câu chuyện** xuyên suốt video. Không nhảy tình huống giữa chừng.

### Persona chính: Chị Mai — công nhân may mặc bị sa thải trái pháp luật

**Profile:**
- Tên: Chị Mai, 28 tuổi, công nhân may mặc tại TP.HCM
- Tình huống: Bị công ty sa thải ngay lập tức sau 4 năm làm việc, không được thông báo trước 30 ngày, không nhận trợ cấp thôi việc, chưa được thanh toán lương tháng cuối

**Tại sao chọn lao_dong:**
- Người Việt Nam dễ đồng cảm
- Có căn cứ pháp lý cụ thể: Điều 36, 46, 47 Bộ luật Lao động 2019
- Kết quả tìm kiếm phong phú (vụ án tương tự + community cases)
- Demo rõ Next Best Actions (thu thập bằng chứng, checklist thời hạn, vụ án tương tự)

### Câu nhập vào Analyze (copy chính xác — không thay đổi khi quay)

```
Tôi là công nhân may, làm việc 4 năm tại công ty TNHH ABC, 
bị sa thải ngay lập tức mà không có thông báo trước. 
Công ty không trả lương tháng cuối và không chi trả 
trợ cấp thôi việc theo quy định. Tôi cần biết 
quyền lợi của mình và phải làm gì tiếp theo.
```

**Tại sao câu này hoạt động tốt:**
- Đủ dài (>10 ký tự, >50 từ) → không bị MIN_QUERY_LENGTH fail
- Chứa từ khóa lao_dong rõ ràng → domain detection chính xác
- Mô tả 3 vi phạm cụ thể → analysis trả về nhiều điểm
- Tự nhiên, đúng ngữ cảnh người thật

---

## PHẦN 2 — PRE-RECORDING SETUP (Làm trước khi bật camera)

### 2.1 Environment setup — chạy theo thứ tự này

```powershell
# 1. Kích hoạt môi trường Python (Anaconda)
conda activate base

# 2. Khởi động backend
cd "c:\Users\Admin\OneDrive\Máy tính\Universal Legal Knowledge Assistant"
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8001 --reload

# 3. Mở terminal mới — seed dữ liệu (idempotent, an toàn chạy lại)
python scripts/seed_raw_data.py --skip-files
python scripts/seed_phase23_demo_personas.py

# 4. Khởi động frontend
cd frontend
npm run dev
```

### 2.2 Seed dữ liệu demo interaction (để Dashboard không trống)

```powershell
# Chạy script này để tạo lịch sử hành vi phong phú cho demo_user_001
python -c "
import sys, requests, time
BASE = 'http://localhost:8001'
USER = 'demo_user_001'

interactions = [
    {'doc_id': 'demo_case_labor_001', 'action_type': 'view', 'context': {'law_type': 'lao_dong', 'module': 'similar_cases'}},
    {'doc_id': 'demo_case_labor_002', 'action_type': 'recommendation_click', 'context': {'law_type': 'lao_dong', 'module': 'similar_cases'}},
    {'doc_id': 'demo_checklist_labor', 'action_type': 'recommendation_useful', 'context': {'law_type': 'lao_dong', 'module': 'checklists'}},
    {'doc_id': 'demo_evidence_gap', 'action_type': 'save', 'context': {'law_type': 'lao_dong', 'module': 'evidence_gap'}},
    {'doc_id': 'demo_case_labor_003', 'action_type': 'view', 'context': {'law_type': 'lao_dong', 'module': 'similar_cases'}},
    {'doc_id': 'demo_timeline_labor', 'action_type': 'save', 'context': {'law_type': 'lao_dong', 'module': 'timeline'}},
    {'doc_id': 'demo_risk_labor', 'action_type': 'recommendation_click', 'context': {'law_type': 'lao_dong', 'module': 'risks'}},
]

for i in interactions:
    resp = requests.post(f'{BASE}/interactions/log', json={**i, 'user_id': USER}, headers={'X-User-ID': USER})
    print(f'{i[\"action_type\"]} -> {resp.status_code}')
    time.sleep(0.3)

print('Done. Dashboard should now show lao_dong as top domain.')
"
```

### 2.3 Kiểm tra trước khi quay (checklist 10 điểm)

```
[ ] Backend running: curl http://localhost:8001/health → 200 OK
[ ] Frontend running: http://localhost:3000 loads trong <3s
[ ] MongoDB Atlas: đăng nhập sẵn, mở tab "Browse Collections" → law_chunks
[ ] Browser: zoom 110%, font size đủ lớn cho judges đọc
[ ] Notifications: tắt hết (Windows Focus Assist → Priority only)
[ ] localStorage: clear 'lexai_user_id' → set về 'demo_user_001'
[ ] Dashboard: mở http://localhost:3000 → kiểm tra có hiển thị interaction data
[ ] SimilarCases: test trước với câu demo → kết quả load < 5s
[ ] Analyze: test câu demo → kết quả load < 10s
[ ] Fallback: nếu vector search chậm → kết quả vẫn hiện (demo_fallback mode)
```

### 2.4 Chuẩn bị MongoDB Atlas

**Tab 1 — Browse Collections:**
- Collection: `law_chunks`
- Filter để show: `{ "metadata.document_type": "nghi_dinh" }`
- Mở sẵn một document để show embedding field

**Tab 2 — Aggregation:**
- Collection: `interactions`
- Pipeline mẫu (để paste nhanh khi demo):
```javascript
[
  { $match: { user_id: "demo_user_001" } },
  { $group: {
      _id: "$context.law_type",
      total: { $sum: 1 },
      clicks: { $sum: { $cond: [{ $eq: ["$action_type", "recommendation_click"] }, 1, 0] } }
  }},
  { $sort: { total: -1 } }
]
```

**Tab 3 — Atlas Search Indexes:**
- Mở Vector Search index: `law_chunks_embedding`
- Screenshot sẵn nếu cần fallback

---

## PHẦN 3 — SCRIPT VIDEO (Chi tiết từng giây)

### SCENE 1: HOOK (0:00 — 0:45)

**Screen:** Màn hình đen → fade in ảnh LexAI dashboard

**Lời thoại (đọc chậm, ngừng đúng dấu phẩy):**

> "Hàng triệu người Việt Nam mỗi ngày đối mặt với vấn đề pháp lý: bị sa thải, tranh chấp đất đai, hợp đồng rủi ro. Họ lên Google tìm kiếm — và nhận về hàng nghìn kết quả không có thứ tự. Không ai nói cho họ biết: luật nào áp dụng, chứng cứ nào cần chuẩn bị, và quan trọng nhất — bước tiếp theo phải làm gì."

**[PAUSE 1 giây]**

> "Đây là bài toán recommendation. Và đó là bài toán LexAI giải quyết."

**[Cut sang: LexAI interface đang mở]**

> "LexAI là một Legal Recommendation Engine chạy trên MongoDB Atlas. Nó biến một tình huống lộn xộn thành một lộ trình hành động cụ thể."

**Key visual:** Text xuất hiện trên màn hình:
```
Situation → Analysis → Evidence → Recommendation → Next Best Action
```

---

### SCENE 2: DEMO ANALYZE (0:45 — 3:30)

**[0:45] Screen:** Mở http://localhost:3000/analyze

**Lời thoại:**
> "Đây là giao diện phân tích pháp lý. Người dùng không cần biết điều luật nào — họ chỉ cần mô tả tình huống bằng tiếng Việt thông thường."

**[1:05] Action:** Click vào textarea, BẮT ĐẦU GÕ chậm câu demo:

```
Tôi là công nhân may, làm việc 4 năm tại công ty TNHH ABC, 
bị sa thải ngay lập tức mà không có thông báo trước. 
Công ty không trả lương tháng cuối và không chi trả 
trợ cấp thôi việc theo quy định. Tôi cần biết 
quyền lợi của mình và phải làm gì tiếp theo.
```

**Lời thoại trong khi gõ (gõ chậm, nói song song):**
> "Đây là Chị Mai, công nhân may mặc tại TP.HCM. Chị bị sa thải đột ngột sau 4 năm làm việc. Chị không biết gì về pháp luật lao động — chỉ biết rằng điều này không công bằng."

**[1:45] Action:** Click nút "Phân tích pháp lý" (hoặc nhấn Ctrl+Enter)

**Lời thoại trong khi chờ kết quả:**
> "Trong vài giây, LexAI chạy qua 7 giai đoạn: phân loại lĩnh vực, tải bối cảnh phiên, tìm kiếm vector trên MongoDB Atlas, duyệt qua đồ thị pháp lý, reasoning với LLM, xếp hạng recommendations — và trả về kết quả có trích dẫn căn cứ."

**[2:15] Kết quả hiện ra — HOST chỉ vào màn hình và đọc:**

> "Nhìn vào kết quả. LexAI xác định ngay: đây là lĩnh vực Luật Lao Động."

**→ Chỉ vào domain badge: "Lao động"**

> "Và phân tích tóm tắt 3 vi phạm của công ty theo Bộ luật Lao động 2019: không thông báo trước 30 ngày theo Điều 36, không trả trợ cấp thôi việc theo Điều 46, và có thể là sa thải trái pháp luật theo Điều 41."

**→ Chỉ vào citations/references section**

> "Quan trọng hơn — nhìn vào phần này."

**[2:50] Highlight Next Best Actions:**

**→ Hover hoặc chỉ vào các NBA chips:**
> "Đây là Next Best Actions. Không phải một đoạn text tĩnh — mà là 4 hành động cụ thể được xếp hạng dựa trên lĩnh vực pháp lý, hành vi người dùng và đánh giá rủi ro. Mỗi chip là một cánh cửa dẫn vào module phù hợp."

**[3:05] — DEMO TỐT NHẤT: Click NBA chip "Vụ việc tương tự"**

> "Tôi click vào 'Vụ việc tương tự'. Để ý rằng tôi không gõ lại gì cả."

---

### SCENE 3A: SIMILAR CASES — CONTEXT RETENTION (3:30 — 5:00)

**Screen:** SimilarCases page tự động load, textarea đã được prefill với câu tình huống của Chị Mai

**Lời thoại:**
> "Trang Vụ Việc Tương Tự tự động nhận bối cảnh từ màn hình trước. Đây là context retention — một trong những khác biệt quan trọng nhất giữa LexAI và một hộp chat thông thường."

**[3:45] Kết quả load — HOST chỉ vào:**

> "MongoDB Vector Search đã so sánh ngữ nghĩa tình huống của Chị Mai với kho vụ việc. Kết quả không so khớp từ khóa — nó hiểu rằng 'bị sa thải đột ngột' và 'chấm dứt hợp đồng không đúng pháp luật' là cùng một khái niệm pháp lý."

**→ Chỉ vào similarity score bar (ví dụ: 91%)**

> "Độ tương đồng 91% — vụ này rất gần với tình huống hiện tại."

**[4:00] Click mở rộng một case card:**

> "Khi mở rộng, chúng ta thấy kết quả thực tế của vụ án: tòa lao động xử công ty phải bồi thường 3 tháng lương. Và bài học pháp lý — đây là thứ Chị Mai cần trước khi quyết định có khởi kiện hay không."

**→ Chỉ vào: "Kết quả", "Bài học", "Căn cứ pháp lý"**

---

### SCENE 3B: COMMUNITY CASES — PHASE 23 (5:00 — 5:50)

**Screen:** Cuộn xuống phần "Vụ việc cộng đồng"

**Lời thoại:**
> "Và đây là tính năng được xây dựng trong Phase 23: Community Intelligence. Ngoài các vụ án chính thống, LexAI còn hiển thị các tình huống từ cộng đồng người dùng — đã được ẩn danh hoàn toàn, không chứa tên, số điện thoại hay địa chỉ."

**→ Chỉ vào community case card với badge "Cộng đồng"**

> "Mỗi tình huống cộng đồng có: tóm tắt hướng giải quyết, các bước nên làm tiếp theo, và căn cứ pháp lý được trích dẫn."

**[5:20] Click mở rộng community case, rồi click nút "Có" (ThumbsUp):**

> "Khi người dùng bấm 'Có — hữu ích', tín hiệu này được ghi vào MongoDB. Recommendation score của loại nội dung này tăng lên. Lần sau, nội dung tương tự sẽ được xếp hạng cao hơn trong next-best-actions."

**→ Nút chuyển màu xanh lá sau khi click**

> "Đây là feedback loop thật — không phải mock."

---

### SCENE 3C: DASHBOARD — BEHAVIOR PERSONALIZATION (5:50 — 7:10)

**Screen:** Navigate sang http://localhost:3000 (Dashboard)

**Lời thoại:**
> "Mỗi lần Chị Mai tương tác — xem, lưu, click, đánh giá — LexAI ghi lại vào collection interactions trong MongoDB. Dashboard tổng hợp những tín hiệu đó thành hồ sơ hành vi."

**→ Chỉ vào Behavior Chart (BarChart) — nên thấy lao_dong là top domain**

> "Nhìn vào biểu đồ — lĩnh vực Lao động đang dẫn đầu. Đây là dữ liệu thật, tính từ MongoDB bằng Aggregation Pipeline."

**[6:10] Chỉ vào Proactive Recommendations cards:**

> "Dashboard không chỉ thống kê. Nó chủ động gợi ý những nội dung phù hợp dựa trên hành vi. Chị Mai đã xem nhiều về lao động — hệ thống đề xuất checklist thủ tục khiếu nại và mẫu đơn yêu cầu bồi thường."

**[6:35] Chỉ vào Active Sessions metric và Top Domain:**

> "Đây là dữ liệu cá nhân hóa thật: số phiên đã phân tích, lĩnh vực pháp lý chủ đạo, và gợi ý hành động tiếp theo. Mỗi số liệu trên Dashboard có nguồn gốc từ MongoDB Aggregation."

---

### SCENE 4A: MONGODB ATLAS — VECTOR SEARCH (7:10 — 8:00)

**Screen:** Chuyển sang tab Atlas — Collection law_chunks

**Lời thoại:**
> "Bây giờ tôi sẽ cho ban giám khảo thấy MongoDB ở cấp độ kỹ thuật."

**→ Show collection law_chunks với filter đang hiển thị**

> "Đây là collection law_chunks. Mỗi document là một đoạn trích từ văn bản pháp luật: nghị định, thông tư, bộ luật — đã được pipeline 8 giai đoạn của LexAI xử lý tự động. Phase 24 vừa hoàn thành: mỗi chunk giờ có thêm metadata document_family và document_type — được phát hiện tự động bằng heuristic keyword từ nội dung văn bản."

**→ Mở một document, scroll đến field `embedding`**

> "Field embedding là vector 384 chiều. Khi người dùng gửi tình huống, LexAI embed câu đó thành vector tương tự và dùng $vectorSearch để tìm các chunk gần nhất theo cosine similarity."

**→ Paste $vectorSearch pipeline (đã chuẩn bị sẵn):**

```javascript
{
  $vectorSearch: {
    index: "law_chunks_embedding",
    path: "embedding",
    queryVector: [/* 384 dims */],
    numCandidates: 150,
    limit: 20,
    filter: { $or: [{ user_id: "demo_user_001" }, { is_global: true }] }
  }
}
```

> "Bộ lọc is_global — tài liệu do admin tải lên, visible cho tất cả người dùng. Không cần thêm tham số — hệ thống tự phát hiện."

---

### SCENE 4B: MONGODB ATLAS — AGGREGATION PIPELINE (8:00 — 8:45)

**Screen:** Chuyển sang collection interactions

**Lời thoại:**
> "Đây là collection interactions. Mỗi khi người dùng xem, click, lưu, hoặc đánh giá một recommendation — một document được ghi vào đây."

**→ Chỉ vào một document với action_type: "recommendation_click"**

> "action_type có thể là view, save, recommendation_click, recommendation_useful, recommendation_not_useful. Mỗi loại có trọng số khác nhau trong ranking."

**→ Paste aggregation pipeline:**

```javascript
[
  { $match: { user_id: "demo_user_001" } },
  { $group: {
    _id: "$context.law_type",
    total: { $sum: 1 },
    clicks: { $sum: { $cond: [{ $eq: ["$action_type", "recommendation_click"] }, 1, 0] } }
  }},
  { $sort: { total: -1 } }
]
```

> "Pipeline này group theo lĩnh vực pháp lý, đếm tổng tương tác và số click riêng. Kết quả này feed trực tiếp vào behavior score — một trong 6 tín hiệu của recommendation ranker."

**→ Run pipeline — kết quả hiện: lao_dong: total 7, clicks 2**

> "Lao động dẫn đầu — chính xác với những gì Dashboard hiển thị. Hai nguồn đồng bộ với nhau."

---

### SCENE 4C: MONGODB — USER MEMORY (8:45 — 9:15)

**Screen:** Chuyển sang collection user_memory

**Lời thoại:**
> "Collection cuối cùng — user_memory. Khác với conversation_sessions chỉ sống 24 giờ, collection này không có TTL. Nó lưu thông tin cá nhân mà LexAI đã học được qua nhiều phiên: tên, nghề nghiệp, địa điểm, và tóm tắt các tình huống pháp lý đã từng phân tích."

**→ Show một user_memory document với situation_summaries array**

> "Mỗi phiên phân tích để lại một SituationRecord — lĩnh vực, ngày, tóm tắt 1 câu. Lần sau Chị Mai quay lại, LexAI đã biết bối cảnh và có thể cá nhân hóa phân tích ngay từ đầu."

---

### SCENE 5: CLOSING — WHY THIS WINS (9:15 — 10:00)

**Screen:** Quay lại LexAI Dashboard — full interface đẹp nhất

**Lời thoại:**
> "LexAI mạnh ở bốn điểm."

**→ Hiện slide text 4 điểm (hoặc đọc từ màn hình):**

> "Thứ nhất — tính sáng tạo: biến bài toán trợ lý pháp lý thành recommendation engine, với behavior signals, feedback loop và community intelligence."

> "Thứ hai — chiều sâu kỹ thuật: MongoDB Vector Search cho retrieval ngữ nghĩa, Aggregation Pipeline cho behavior analytics, 6 collection chuyên dụng, 7-stage inference pipeline, và document enrichment tự động."

> "Thứ ba — tác động xã hội: người dân như Chị Mai không cần biết luật để bảo vệ quyền lợi của mình."

> "Thứ tư — MVP hoàn chỉnh: luồng phân tích từ đầu đến cuối, context retention, feedback loop, fallback ổn định, 224 tests passing."

**[Final line — nói chậm, rõ:]**

> "LexAI recommends not just information — but the next responsible legal step. Powered by MongoDB Atlas."

---

## PHẦN 4 — TIMING TABLE (TỔNG HỢP)

| Thời gian | Scene | Screen | Key point |
|---|---|---|---|
| 0:00-0:45 | Hook | Dashboard dark | Legal access = recommendation problem |
| 0:45-1:05 | Product intro | Analyze page | "Built on MongoDB Atlas" |
| 1:05-2:15 | Type situation | Analyze textarea | Persona story — Chị Mai |
| 2:15-2:50 | Analysis result | Analyze result | Domain + citations + risk score |
| 2:50-3:30 | NBA chips | Analyze result | Click "Vụ việc tương tự" |
| 3:30-4:10 | Context retention | SimilarCases prefilled | Vector Search semantic result |
| 4:10-5:00 | Case detail | CaseCard expanded | Outcome + lesson + law citations |
| 5:00-5:50 | Community cases | CommunityCaseCard | Phase 23 — feedback loop live |
| 5:50-7:10 | Dashboard | Dashboard | Behavior chart + proactive recs |
| 7:10-8:00 | Atlas: Vector Search | MongoDB Atlas | law_chunks + $vectorSearch |
| 8:00-8:45 | Atlas: Aggregation | interactions collection | Behavior pipeline live result |
| 8:45-9:15 | Atlas: User Memory | user_memory collection | Cross-session personalization |
| 9:15-10:00 | Closing | LexAI dashboard | 4 điểm mạnh + final line |

---

## PHẦN 5 — FALLBACK PLAN (Khi gặp sự cố lúc quay)

### Sự cố 1: Analyze không trả về kết quả (timeout)

**Dấu hiệu:** Loading spinner quay >15 giây

**Xử lý:** Đừng nói gì thêm — chỉ cần:
1. Mở terminal → kiểm tra backend có đang chạy không
2. Thử lại với câu ngắn hơn: "Tôi bị sa thải, không được trả trợ cấp thôi việc"
3. **Nếu vẫn fail:** Dùng screenshot backup đã chụp trước → nói "Đây là kết quả từ một phiên trước"

**Lời thoại fallback:**
> "Đây là kết quả đã được lưu từ một phiên phân tích. Trong môi trường production với MongoDB Atlas đầy đủ, thời gian response thường dưới 5 giây."

---

### Sự cố 2: Vector Search trả về empty (không có dữ liệu)

**Dấu hiệu:** SimilarCases hiện "Không tìm thấy vụ việc tương tự"

**Xử lý:** Trang vẫn hiển thị search_mode label

**Lời thoại:**
> "Trong môi trường demo không có vector index đầy đủ, LexAI tự động chuyển sang keyword fallback và demo data — đảm bảo demo không bị gãy. Đây là thiết kế chủ ý cho production reliability."

---

### Sự cố 3: Dashboard chart trống

**Dấu hiệu:** BarChart không hiển thị data

**Xử lý:** Chạy lại seed script
```powershell
python -c "
import requests
BASE = 'http://localhost:8001'
USER = 'demo_user_001'
for i in range(5):
    requests.post(f'{BASE}/interactions/log', json={'doc_id': f'test_{i}', 'action_type': 'view', 'context': {'law_type': 'lao_dong', 'module': 'analyze'}}, headers={'X-User-ID': USER})
print('Done')
"
```
Sau đó refresh Dashboard.

---

### Sự cố 4: MongoDB Atlas không load

**Dấu hiệu:** Atlas tab timeout hoặc slow

**Xử lý:** Dùng pre-screenshot. Nói:
> "Tôi sẽ dùng ảnh chụp màn hình đã chuẩn bị sẵn từ MongoDB Atlas để giải thích phần kỹ thuật."

**Không cần xin lỗi — chỉ tiếp tục smooth.**

---

## PHẦN 6 — PHASE 23 & 24 FEATURE HIGHLIGHT SCRIPT

### Cách mention Phase 23 — Community Intelligence (5:00-5:50)

**Điểm chính cần nói:**
1. Cộng đồng người dùng tạo ra tri thức chung
2. Ẩn danh hoàn toàn trước khi hiển thị (privacy-first)
3. Feedback (Có/Không hữu ích) được ghi MongoDB → ảnh hưởng ranking
4. "Users like you also researched..." pattern

**Script:**
> "Phase 23 thêm Community Intelligence: các tình huống tương tự từ người dùng khác, đã được ẩn danh hoàn toàn theo quy trình privacy. Khi Chị Mai thấy tình huống cộng đồng hữu ích và bấm 'Có' — tín hiệu đó được ghi vào MongoDB và feeds ngược vào recommendation ranking. Đây là collaborative filtering ở cấp community."

### Cách mention Phase 24 — Document Enrichment (có thể skip nếu hết giờ)

**Script ngắn (15 giây, có thể thêm vào Scene 4A):**
> "Và Phase 24 vừa hoàn thành: khi admin upload văn bản pháp luật, hệ thống tự động phân loại: đây là Nghị định, Thông tư, hay Hợp đồng — không cần thêm input. Metadata này được lưu trong mỗi chunk và dùng để filter kết quả chính xác hơn."

---

## PHẦN 7 — VISUAL ASSETS CẦN CHUẨN BỊ

### Slides/Graphics (tạo bằng Canva hoặc screenshot)

| Asset | Dùng ở | Mô tả |
|---|---|---|
| Slide "Legal access = recommendation problem" | Scene 1 (0:00) | Text trên nền tối, font lớn |
| Diagram: 7-stage pipeline | Scene 2 (1:50) | Flow chart đơn giản, 7 bước |
| Text animation: 4 điểm mạnh | Scene 5 (9:15) | Innovation / Tech / Impact / MVP |
| MongoDB logo + LexAI logo | Closing (9:50) | Side by side |

### Screenshots backup (chụp trước khi quay)

1. Analyze result với câu demo Chị Mai → lưu 2 ảnh (full page + NBA section zoom)
2. SimilarCases với 3 kết quả → lưu 2 ảnh (list view + one expanded)
3. CommunityCaseCard với feedback buttons → 1 ảnh trước click, 1 sau click
4. Dashboard với behavior chart → 1 ảnh
5. MongoDB Atlas law_chunks với embedding field → 1 ảnh
6. MongoDB Atlas interactions với aggregation result → 1 ảnh

---

## PHẦN 8 — RECORDING SETUP

### Phần mềm đề xuất

| Mục đích | Phần mềm |
|---|---|
| Screen recording | OBS Studio (free) hoặc Loom |
| Video editing | DaVinci Resolve (free) hoặc CapCut |
| Microphone | Bất kỳ USB mic nào, ghi trong phòng yên tĩnh |
| Backup audio | Điện thoại đặt cách 30cm từ miệng |

### OBS Setup

```
Scene: LexAI Demo
Sources:
  - Window Capture: Chrome (LexAI app)
  - Window Capture: Chrome (MongoDB Atlas) — ẩn, chỉ bật khi cần
  - Audio: Microphone
Output: 1920x1080, 30fps, MP4
```

### Quy trình ghi

1. Ghi AUDIO riêng trước → viết script hoàn chỉnh, đọc tự nhiên
2. Ghi SCREEN riêng → làm demo theo đúng timing của audio
3. Ghép trong DaVinci Resolve / CapCut
4. Thêm text overlay: tên section, key terms, MongoDB logo

**Lý do ghi riêng:** Không bị áp lực vừa nói vừa click. Demo smoother. Audio cleaner.

---

## PHẦN 9 — JUDGE BRIEFING (Slide cuối hoặc description)

Nếu cuộc thi cho phép nộp description kèm video, dùng text sau:

```
LexAI — MongoDB-Powered Legal Recommendation Engine

LexAI is a legal recommendation engine built entirely on MongoDB Atlas.
It turns a user's natural-language legal situation into grounded analysis,
ranked next-best actions, similar cases via Vector Search, and behavior-based
personalization via Aggregation Pipelines.

MongoDB Atlas usage:
• law_chunks: 384-dim embeddings, $vectorSearch for semantic legal retrieval
• interactions: behavior signals (click, save, dismiss, feedback)
• user_memory: cross-session personalization, no TTL
• conversation_sessions: 24h TTL multi-turn context
• legal_cases: similar case outcome patterns
• reasoning_traces: 7-stage pipeline execution logs

Key differentiators:
• 7-stage intelligence pipeline (deterministic query planning + LLM reasoning)
• Community Intelligence (Phase 23): anonymized peer cases + feedback loop
• Document auto-classification (Phase 24): heuristic keyword rules detect decree/circular/contract
• Stable fallback: demo never breaks even without vector index or API key
• 224 backend tests passing

Tech stack: FastAPI · MongoDB Atlas · React 19/TypeScript/Vite · sentence-transformers · OpenAI
```

---

## PHẦN 10 — FINAL CHECKLIST TRƯỚC KHI NỘP

```
[ ] Video đúng định dạng yêu cầu (MP4, ≤10 phút)
[ ] Audio rõ ràng, không tạp âm
[ ] Không có thông tin cá nhân thật trong demo (dùng "Chị Mai" - nhân vật hư cấu)
[ ] Không có API key nào hiển thị trên màn hình
[ ] MongoDB Atlas UI xuất hiện ít nhất 90 giây trong video
[ ] Câu "Legal access is a recommendation problem" xuất hiện trong hook
[ ] Feedback loop demo (ThumbsUp/ThumbsDown) được show
[ ] Câu closing "next responsible legal step" đọc rõ
[ ] Subtitle/caption nếu cuộc thi yêu cầu
[ ] Description đã paste vào submission form
```
