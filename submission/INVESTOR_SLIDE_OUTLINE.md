# LexAI — Investor Pitch Deck
## Slide Outline (10 slides)

---

## SLIDE 1 — COVER

**Tiêu đề lớn:**
> LexAI — Trợ Lý Pháp Lý AI

**Tagline:**
> "97% doanh nghiệp Việt Nam không có luật sư riêng. Chúng tôi đang thay đổi điều đó."

**Visual:** Logo LexAI trên nền gradient xanh đậm, hình minh họa người đang nhận tư vấn pháp lý từ AI

**Footer:** thagn123 · Hackathon Demo 2026 · Powered by MongoDB Atlas

---

## SLIDE 2 — VẤN ĐỀ: Ai đang chịu thiệt thòi?

**Tiêu đề:** Pháp luật Việt Nam: Phức tạp, đắt đỏ, và không ai hướng dẫn

**3 cột số liệu:**

| | | |
|---|---|---|
| **900.000+** | **2–5 triệu VND** | **300+ văn bản** |
| SME không có pháp chế | Chi phí luật sư/giờ | Pháp lý mới mỗi năm |

**4 hậu quả thực tế:**
- Ký hợp đồng thiếu điều khoản bảo vệ → thua kiện, mất tiền
- Đất đai tranh chấp không biết quy trình → bỏ lỡ thời hiệu khiếu nại
- Lao động bị sa thải trái luật → không biết quyền được bồi thường
- Doanh nghiệp vi phạm thuế, BHXH không cố ý → bị phạt nặng

**Quote từ người dùng thực tế:**
> *"Tôi cần biết quyền lợi của mình, nhưng không đủ tiền thuê luật sư."*

---

## SLIDE 3 — GIẢI PHÁP: LexAI không phải chatbot

**Tiêu đề:** LexAI — AI Legal Intelligence Infrastructure

**So sánh trực quan:**

| ChatGPT / chatbot thông thường | LexAI |
|---|---|
| Trả lời chung chung | Trích dẫn điều luật cụ thể |
| Không nhớ ngữ cảnh | Ghi nhớ lịch sử pháp lý của bạn |
| Không phân tích rủi ro | Dự đoán rủi ro trước khi xảy ra |
| Không có bằng chứng | Kèm nguồn: Nghị định, Luật, Thông tư |

**Pipeline 7 tầng (sơ đồ đơn giản):**
```
Câu hỏi → Phân loại → Tìm kiếm → GraphRAG → LLM Suy luận → Xếp hạng → Gợi ý hành động
```

**Tagline slide:**
> Không đoán mò. Không nói chung. Chỉ pháp luật thực tế — được trích dẫn rõ ràng.

---

## SLIDE 4 — DEMO USE CASE 1: Doanh nghiệp SME

**Tiêu đề:** Tình huống thực: Doanh nghiệp bị vi phạm hợp đồng

**Kịch bản:**
> Chủ doanh nghiệp nhỏ: *"Đối tác đơn phương chấm dứt hợp đồng mà không thông báo trước 30 ngày. Tôi có thể đòi bồi thường không và làm thế nào?"*

**LexAI trả lời — 3 phần:**

**① Phân tích pháp lý:**
> Căn cứ Điều 428 Bộ luật Dân sự 2015: đơn phương chấm dứt hợp đồng không có lý do chính đáng là vi phạm. Bên vi phạm phải bồi thường thiệt hại thực tế.

**② Gợi ý hành động cụ thể:**
- Gửi thông báo yêu cầu bồi thường bằng văn bản trong vòng 7 ngày
- Thu thập bằng chứng: email, tin nhắn, biên bản giao nhận
- Khởi kiện tại TAND nếu không thỏa thuận được

**③ Tài liệu mẫu được tạo tự động:**
> Template "Thông báo yêu cầu bồi thường vi phạm hợp đồng" — điền thông tin → tải PDF

**Visual:** Screenshot giao diện chat LexAI với response được highlight

---

## SLIDE 5 — DEMO USE CASE 2: Người dân (đất đai)

**Tiêu đề:** Tình huống thực: Thu hồi đất, hòa giải không thành

**Kịch bản:**
> Người dân: *"Đất của tôi bị thu hồi để làm đường, hòa giải tại xã không thành. Tôi phải làm gì tiếp theo?"*

**LexAI nhận diện tình huống và cá nhân hóa:**
> "Chào anh/chị [Tên từ lịch sử hội thoại]. Dựa trên tình huống đất đai tại [Tỉnh] của anh/chị..."

**Gợi ý chính xác theo giai đoạn:**

| Bước | Hành động | Căn cứ pháp lý |
|---|---|---|
| 1 | Nộp đơn khiếu nại lên UBND huyện | Luật Khiếu nại 2011, Điều 7 |
| 2 | Thời hạn: 30 ngày kể từ nhận quyết định | Điều 9 |
| 3 | Nếu tiếp tục từ chối: khởi kiện hành chính | Luật TTHC 2015 |

**Điểm khác biệt:** LexAI biết người dùng đã qua hòa giải → **không gợi ý hòa giải nữa** (OutputValidator S-05)

---

## SLIDE 6 — GỢI Ý THÔNG MINH: Đây là trái tim của LexAI

**Tiêu đề:** 6 loại gợi ý — Mỗi loại đến từ đâu và giúp ích gì?

### GỢI Ý LÀ GÌ?

| # | Loại gợi ý | Ví dụ cụ thể |
|---|---|---|
| 1 | **Điều khoản pháp lý liên quan** | "Điều 428 BLDS 2015 áp dụng cho trường hợp của bạn" |
| 2 | **Án lệ tương tự** | "3 vụ kiện hợp đồng tương tự — kết quả và bài học" |
| 3 | **Mẫu văn bản & hợp đồng** | "Mẫu thông báo chấm dứt hợp đồng chuẩn pháp lý" |
| 4 | **Cảnh báo rủi ro** | "Rủi ro: hợp đồng của bạn thiếu điều khoản phạt vi phạm" |
| 5 | **Checklist tuân thủ** | "7 bước doanh nghiệp cần hoàn thành trước khi ký hợp đồng" |
| 6 | **Hành động tiếp theo** | "Bước tiếp theo của bạn: nộp đơn khiếu nại trong 30 ngày" |

### DỮ LIỆU ĐẾN TỪ ĐÂU?

```
MongoDB Atlas Vector Search  →  Tìm điều luật theo nghĩa (không chỉ từ khóa)
GraphRAG (đồ thị pháp lý)    →  Luật nào dẫn chiếu, sửa đổi, mâu thuẫn luật nào
Lịch sử hành vi người dùng   →  Bạn đã xem gì, quan tâm lĩnh vực nào
Cộng đồng ẩn danh            →  Người có tình huống tương tự đã tìm hiểu gì
```

### CÔNG DỤNG CHO NGƯỜI DÙNG?

- **Tiết kiệm:** Không mất 2–5 triệu/giờ cho mỗi câu hỏi cơ bản
- **Phòng ngừa:** Phát hiện rủi ro pháp lý TRƯỚC khi ký, trước khi tranh chấp
- **Hành động đúng lúc:** Không bỏ lỡ thời hiệu khiếu nại, thời hạn nộp hồ sơ
- **Tự tin:** Hiểu quyền lợi của mình, không bị bên kia dẫn dắt

---

## SLIDE 7 — CÔNG NGHỆ: MongoDB là xương sống

**Tiêu đề:** Tại sao MongoDB Atlas — không phải PostgreSQL hay Elasticsearch?

**3 lý do kỹ thuật, 1 lý do kinh doanh:**

**① Vector Search — Hiểu nghĩa pháp lý**
> Tra "vi phạm hợp đồng" → tìm được cả "đơn phương chấm dứt", "bội ước", "không thực hiện nghĩa vụ"
> → Elasticsearch keyword search không làm được điều này

**② Aggregation Pipeline — Tính điểm tổng hợp trong 1 query**
```javascript
// Tất cả trong 1 pipeline:
$vectorSearch → $addFields (vector_score) → $match (threshold) 
→ $addFields (bm25_score, graph_score, behavior_score)
→ $addFields (fusion_score = vector×0.45 + bm25×0.20 + graph×0.25 + behavior×0.10)
→ $sort → $limit → $project
```
> 1 round-trip vs. 4+ queries nếu dùng hệ thống tách biệt

**③ Flexible Schema — Pháp luật thay đổi liên tục**
> Thêm trường mới (is_global, graph_edges, behavior_score) không cần migration

**④ Atlas M0 Free Tier — Chi phí khởi nghiệp gần 0**
> Toàn bộ hệ thống chạy trên M0 free tier trong giai đoạn demo/beta

**Visual:** So sánh kiến trúc LexAI vs. kiến trúc truyền thống

---

## SLIDE 8 — KẾT QUẢ: Những con số nói lên tất cả

**Tiêu đề:** Kết quả sau 18 giai đoạn phát triển

**4 chỉ số lớn:**

| Chỉ số | Kết quả | Ý nghĩa |
|---|---|---|
| **365/365** | Test cases pass | Hệ thống hoạt động ổn định, không regression |
| **96.6%** | Độ chính xác domain | AI hiểu đúng lĩnh vực pháp lý của câu hỏi |
| **7 lĩnh vực** | Đất đai, Hợp đồng, Lao động, Doanh nghiệp, Dân sự, Hình sự, Hành chính | Phủ rộng nhu cầu người dùng VN |
| **< 2 giây** | Thời gian phản hồi | Trải nghiệm người dùng mượt mà |

**Pipeline hoàn chỉnh:**
- 7-stage intelligence pipeline (end-to-end)
- 8-stage document ingestion (tự động xử lý văn bản pháp lý mới)
- Cross-session memory (AI nhớ bạn qua các lần chat)
- OutputValidator chống mâu thuẫn pháp lý

**Beta Gate:** PASS ✓

---

## SLIDE 9 — THỊ TRƯỜNG & CƠ HỘI

**Tiêu đề:** Thị trường $2.4 tỷ USD đang chờ được số hóa

**TAM / SAM / SOM:**

```
TAM  $2.4B USD  ← Toàn bộ thị trường tư vấn pháp lý VN + ĐNA
SAM   $180M USD  ← SME + cá nhân cần tư vấn pháp lý online
SOM    $18M USD  ← Mục tiêu năm 3 với tăng trưởng hữu cơ
```

**Mô hình doanh thu:**

| Tier | Giá | Phân khúc |
|---|---|---|
| Free | 0 | Câu hỏi cơ bản, 5 truy vấn/ngày |
| Pro | 299K/tháng | Không giới hạn, lưu lịch sử, tạo văn bản |
| Enterprise | Thương lượng | API tích hợp, white-label, bulk |

**Đối thủ cạnh tranh:**
- LuatVietnam.vn — database tĩnh, không AI
- ChatGPT — không chuyên biệt VN, không citation
- Công ty luật truyền thống — đắt, chậm, không scale

**Lợi thế cạnh tranh:** Data moat (corpus pháp lý VN), memory cá nhân hóa, OutputValidator ngăn sai sót pháp lý

---

## SLIDE 10 — KÊU GỌI ĐẦU TƯ

**Tiêu đề:** Chúng tôi đang tìm đối tác để scale

**Seed Round: $500,000 USD**

**Sử dụng vốn:**

| % | Mục đích |
|---|---|
| 40% | Tuyển dụng: 2 AI Engineer + 1 Legal Expert |
| 30% | Marketing & Growth (B2C freemium) |
| 20% | Infrastructure scale (MongoDB Atlas M10+) |
| 10% | Pháp lý & vận hành |

**Roadmap 18 tháng:**
- **Q3 2026:** Mobile app iOS/Android, 50+ luật chính
- **Q4 2026:** B2B API cho công ty luật, kế toán, HR
- **Q2 2027:** Mở rộng ĐNA: Thái Lan, Indonesia (multilingual)

**Metrics Year 1 Target:**
- 10,000 MAU
- 500 Pro subscribers (~150M VND/tháng ARR)
- 20 enterprise contracts

---

**Closing:**

> *"Khi pháp luật còn phức tạp — LexAI ở đây để chỉ đường.*
> *Hãy cùng chúng tôi đưa công lý đến tay mọi người."*

**Contact:** daothang28032003@gmail.com | github.com/thagn123/mongoDB_hakathon

---

*Deck version: Investor Edition v1.0 — 2026*
