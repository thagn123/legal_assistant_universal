# Văn bản Thuyết trình — LexAI
## Trợ lý Pháp lý Thông minh cho Người dân Việt Nam

> **Thời lượng đề xuất:** 8–10 phút  
> **Người trình bày đọc phần in thường; phần *in nghiêng* là ghi chú hành động.**

---

## SLIDE 1 — COVER

*Slide mở ra với panel tối bên trái, tên LexAI cỡ chữ lớn và pipeline 7 giai đoạn bên phải.*

---

Xin chào Ban giám khảo và các bạn.

Chúng tôi xin giới thiệu **LexAI** — Trợ lý Pháp lý Thông minh được thiết kế dành riêng cho người dân Việt Nam.

Người dân Việt Nam đang đối mặt với một vấn đề thực tế: hệ thống pháp luật phức tạp, chi phí tư vấn cao, và khi tra cứu AI thông thường thì nhận được câu trả lời chung chung, thậm chí **mâu thuẫn với tình huống cụ thể** của họ.

LexAI giải quyết điều đó bằng ba cam kết cốt lõi:

- **Hiểu bằng chứng thực tế** — hệ thống đọc và phân tích từng tình tiết cụ thể của người dùng
- **Không tự mâu thuẫn** — không gợi ý hành động đã hoàn thành hoặc không cần thiết
- **Chỉ dẫn bước tiếp theo** — đưa ra hành động cụ thể, khả thi, đúng thứ tự pháp lý

Kết quả hiện tại: **96.6% chính xác**, **365 test cases**, **0% lỗi mâu thuẫn**, và đã qua **Beta PASS** release gate.

---

## SLIDE 2 — PIPELINE 8 GIAI ĐOẠN: DỮ LIỆU THÔ → MONGODB

*Slide hiển thị sơ đồ snake 8 ô: hàng trên trái-sang-phải, hàng dưới phải-sang-trái, với mũi tên định hướng.*

---

Câu hỏi đầu tiên: **Dữ liệu pháp lý đến từ đâu và được xử lý như thế nào?**

Chúng tôi không dùng dữ liệu tổng hợp. Chúng tôi tải trực tiếp các văn bản luật gốc — PDF, DOCX từ các cơ quan ban hành — và đưa qua **8 giai đoạn xử lý**:

**Giai đoạn 1 — UPLOAD:** Nhận file PDF/DOCX từ quản trị viên. Mỗi file được gắn nhãn `is_global=True`, có nghĩa là toàn bộ người dùng đều được truy cập.

**Giai đoạn 2 — OCR Cleaner:** Xử lý văn bản scan, loại bỏ nhiễu, sửa lỗi chính tả phổ biến trong văn bản pháp lý.

**Giai đoạn 3 — Layout Profiler:** Phát hiện cấu trúc trang — bảng biểu, tiêu đề Điều, Khoản, Điểm — để chuẩn bị cho bước tiếp theo.

**Giai đoạn 4 — Structurer:** Xuất JSON có cấu trúc chuẩn: `Điều → Khoản → Điểm`, với đầy đủ metadata như tên luật, số hiệu.

**Giai đoạn 5 — Chunker:** Đây là điểm then chốt. Chúng tôi cắt văn bản **theo ranh giới Điều luật**, không cắt ngang giữa chừng. Một Điều luật luôn nằm trọn trong một chunk — bảo toàn 100% ngữ cảnh pháp lý.

**Giai đoạn 6 — Graph Builder:** Xây dựng đồ thị liên kết — mỗi Điều viện dẫn Điều khác sẽ có cạnh nối, tạo nền tảng cho GraphRAG sau này.

**Giai đoạn 7 — Embed 384-dim:** Dùng `sentence-transformers` đa ngôn ngữ, mỗi chunk được chuyển thành vector 384 chiều.

**Giai đoạn 8 — MongoDB Atlas:** Vector được lưu vào MongoDB với chỉ mục vector search sẵn sàng phục vụ truy vấn.

---

## SLIDE 3 — KIẾN TRÚC MONGODB ATLAS

*Slide 3 cột: trái là danh sách collections, giữa là code schema document, phải là vector index và filter.*

---

Bây giờ chúng ta xem **dữ liệu được tổ chức như thế nào trong MongoDB**.

**Các collections chính:**

- `law_chunks` — trung tâm của hệ thống, lưu mọi chunk văn bản luật với embedding 384 chiều và flag `is_global`
- `user_memory` — bộ nhớ dài hạn của từng người dùng, **không có TTL**, tích lũy theo thời gian
- `conversation_sessions` — lịch sử hội thoại, tự động xóa sau 24 giờ
- `templates`, `risks`, `checklists` — kho biểu mẫu hợp đồng và cảnh báo rủi ro pháp lý

**Schema của một document trong `law_chunks`:** *(chỉ vào phần code giữa slide)*

Mỗi document chứa: nội dung văn bản, loại luật, số điều tham chiếu, vector 384 chiều, và flag `is_global`.

**Vector Search Index:** Chỉ mục tên `chunk_embedding_index`, kiểu `vectorSearch`, 384 chiều, similarity `cosine`, ngưỡng `0.55`.

**Isolation filter** — đây là cơ chế bảo mật dữ liệu: mỗi truy vấn chỉ lấy chunk của đúng người dùng đó **hoặc** chunk toàn cục (`is_global=true`). Dữ liệu của người dùng A không bao giờ lộ sang người dùng B.

**Aggregation pipeline** *(chỉ vào dải đen phía dưới)*: `$vectorSearch → $match score ≥ 0.55 → $sort → $limit 10`

---

## SLIDE 4 — RETRIEVAL FUSION: 4 TÍN HIỆU

*Slide hiển thị 4 ô signal bên trên, thanh bar phân tỉ lệ %, hàng threshold phía dưới.*

---

Khi người dùng gõ câu hỏi, hệ thống không chỉ tìm kiếm theo một cách. Chúng tôi kết hợp **4 tín hiệu song song**:

**Tín hiệu 1 — Vector Search (45%):** Tìm kiếm ngữ nghĩa thuần túy. Câu hỏi được embed thành vector, so sánh cosine với toàn bộ law_chunks. Đây là tín hiệu mạnh nhất vì nắm bắt được ý nghĩa, không cần khớp từ ngữ chính xác.

**Tín hiệu 2 — GraphRAG (25%):** Từ các Điều luật tìm được, hệ thống duyệt đồ thị BFS — "Điều này viện dẫn Điều nào? Điều nào bổ sung, sửa đổi, hay bãi bỏ Điều này?" Đây là lý do LexAI biết được luật mới nhất thay thế luật cũ.

**Tín hiệu 3 — BM25 Keyword (20%):** Tần suất từ khóa — đơn giản nhưng hiệu quả cho các thuật ngữ pháp lý đặc thù như "UBND", "biên bản", "khởi kiện".

**Tín hiệu 4 — Behavior Boost (10%):** Những Điều luật mà người dùng đã tương tác trước đây (xem, lưu, tải) được ưu tiên hiển thị lại.

**Công thức kết hợp:** `Score = 0.45×Vector + 0.25×GraphRAG + 0.20×BM25 + 0.10×Behavior`

**Threshold filter:** Bất kỳ chunk nào có score dưới 0.55 bị loại hoàn toàn — không đưa vào LLM, không sinh ra câu trả lời mơ hồ từ dữ liệu không liên quan.

---

## SLIDE 5 — 7 GIAI ĐOẠN INTELLIGENCE PIPELINE

*Slide 7 cột dọc màu sắc khác nhau, mũi tên ngang nối liên tiếp, nhãn tóm tắt bên dưới mỗi cột.*

---

Đây là **luồng xử lý hoàn chỉnh** từ khi người dùng gõ câu hỏi đến khi nhận được câu trả lời:

**S1 — QueryPlanner:** Xử lý thuần logic, không dùng LLM. Trong vòng dưới 10ms, hệ thống phân loại domain pháp lý (đất đai, lao động, gia đình...), trích xuất thực thể, và chọn chiến lược truy xuất phù hợp.

**S2 — Session + Memory:** Nạp lịch sử hội thoại 24h và **bộ nhớ dài hạn** của người dùng — tên, nghề nghiệp, địa điểm, các tình huống pháp lý đã từng hỏi. Thông tin này được ghép vào đầu prompt để cá nhân hóa câu trả lời.

**S3 — Retrieval Fusion:** 4 tín hiệu chạy song song như đã trình bày ở slide trước.

**S4 — Graph Expand:** BFS mở rộng từ các Điều đã tìm được — ưu tiên quan hệ OVERRIDES > AMENDS > CITES. Mỗi bước BFS bị giảm điểm 0.10 để kiểm soát độ mở rộng.

**S5 — LLM Reasoning:** OpenAI với tool-calling, tối đa 4 vòng. Nếu LLM không khả dụng, hệ thống tự động fallback sang assessment xác định luận.

**S6 — Rec Ranker:** 6-signal reranking trên các gợi ý kèm theo — sẽ trình bày chi tiết slide sau.

**S7 — Persist + Reflect:** Lưu trace, session, và chạy `ReflectionAgent` trong luồng daemon — tức là **không chặn response**. Agent này tự động trích xuất thông tin mới về người dùng và cập nhật vào bộ nhớ dài hạn.

---

## SLIDE 6 — EVIDENCE STATUS + OUTPUTVALIDATOR

*Slide chia 3 phần: trái là evidence extractor, giữa là validator đỏ, phải là so sánh trước/sau.*

---

Đây là tính năng **khác biệt lớn nhất** của LexAI so với chatbot thông thường.

**Vấn đề với chatbot thường:** Người dùng nói "Tôi đã có sổ đỏ", nhưng AI vẫn gợi ý "Thu thập sổ đỏ" — tự mâu thuẫn với thông tin người dùng vừa cung cấp.

**Giải pháp của LexAI:**

Bước 1 — **Evidence Extractor** phân tích câu nhập và xác định trạng thái từng bằng chứng:
- `land_certificate`: **PRESENT** ✓ — người dùng đã có sổ đỏ
- `ubnd_mediation`: **PENDING** ? — chưa rõ đã hòa giải chưa
- `court_filing`: **ABSENT** ✗ — chưa khởi kiện

Bước 2 — **OutputValidator** nhận danh sách actions từ LLM và lọc bỏ mọi action mâu thuẫn với evidence status đã xác định. Nếu `land_certificate=PRESENT`, mọi action liên quan đến "thu thập sổ đỏ" bị xóa khỏi kết quả.

**Kết quả so sánh** *(chỉ vào cột đỏ và cột xanh)*:
- Chatbot thường: gợi ý "Thu thập sổ đỏ", "Xin cấp GCN" — vô nghĩa và gây mất thời gian
- LexAI: chỉ gợi ý "Lập biên bản ranh giới", "Đề nghị hòa giải xã", "Nộp đơn UBND Huyện" — đúng bước, đúng thứ tự

Tính năng này được củng cố bởi **S-05 P0 fix**: 16 cụm từ nhận diện tình huống hòa giải thất bại, được kiểm thử bởi 25 regression tests.

---

## SLIDE 7 — 6-SIGNAL RECOMMENDATION RANKER

*Slide hiển thị công thức trên cùng, 6 ô pill bên dưới, 3 ô output phía dưới cùng.*

---

Ngoài câu trả lời chính, LexAI còn đưa ra **gợi ý cá nhân hóa** dựa trên 6 tín hiệu xếp hạng:

**Công thức:** `Score = 0.35×Semantic + 0.20×Graph + 0.15×Behavior + 0.15×Freshness + 0.10×Popularity + 0.05×Accepted`

Ý nghĩa từng tín hiệu:

- **Semantic (35%)** — tương đồng vector với tình huống hiện tại
- **Graph (20%)** — mức độ liên kết trong đồ thị pháp luật
- **Behavior (15%)** — lịch sử tương tác của chính người dùng đó
- **Freshness (15%)** — văn bản luật càng mới càng được ưu tiên, sử dụng decay với half-life 180 ngày
- **Popularity (10%)** — tần suất được tra cứu bởi những người dùng có tình huống tương tự
- **Accepted (5%)** — người dùng đã từng lưu hoặc tải tài liệu này

Ba loại đầu ra được cá nhân hóa:

1. **Next Best Actions** — các hành động tiếp theo cụ thể, đã lọc bỏ bước đã hoàn thành
2. **Evidence Gap** — danh sách tài liệu còn thiếu để chuẩn bị hồ sơ pháp lý
3. **Templates + Risks** — biểu mẫu hợp đồng phù hợp và cảnh báo điều khoản rủi ro

---

## SLIDE 8 — CHỈ SỐ CHẤT LƯỢNG

*Slide 4 card lớn với số liệu nổi bật màu sắc khác nhau.*

---

Chúng tôi không chỉ tuyên bố — chúng tôi có con số đo lường.

**96.6% Chính xác phân loại ngành:** Đo trên 30 tình huống thực tế đa dạng — đất đai, lao động, hôn nhân, hình sự. Lỗi chéo ngành (nhầm domain) là **0%**.

**365 Kịch bản kiểm thử tự động:** Chạy liên tục trên CI/CD mỗi khi có commit mới. Bao gồm 25 regression tests chuyên biệt cho tình huống S-05 — hòa giải thất bại.

**0% Lỗi tự mâu thuẫn:** OutputValidator lọc 100% các action thừa hoặc mâu thuẫn với evidence status. Không có trường hợp nào AI gợi ý bước mà người dùng đã hoàn thành.

**Beta PASS:** Release gate tự động với 6 hard gates. Hệ thống hiện ở trạng thái Beta-ready. GA release đang chờ một blocker về infrastructure — tạo vector index cho case law — không ảnh hưởng đến chức năng hiện tại.

---

## SLIDE 9 — DEMO THỰC TẾ: S-05 P0 FIX

*Slide chia đôi trái/phải với header đỏ (chatbot thường) và xanh (LexAI).*

---

Hãy xem một tình huống cụ thể để hiểu rõ sự khác biệt.

**Tình huống người dùng nhập vào:** *(đọc từ ô trên cùng slide)*

> "Tôi đã hòa giải ở xã nhưng không thành, hàng xóm vẫn lấn đất và không ký biên bản."

**Hệ thống nhận diện:** Hàm `_is_post_mediation_failed()` phát hiện 2 cụm từ — "hòa giải không thành" và "không ký biên bản" — và kết luận: trạng thái = POST_MEDIATION_FAILED.

**Chatbot thường sẽ làm gì?** *(chỉ vào cột đỏ)*

Gợi ý lại từ đầu: "Nộp đơn yêu cầu hòa giải tại UBND xã", "Liên hệ cán bộ địa chính để hòa giải"... Đây là **lặp lại bước đã thất bại**. Nguy hiểm hơn — kéo dài thời gian có thể làm hết thời hiệu khởi kiện.

**LexAI làm gì?** *(chỉ vào cột xanh)*

Chuyển sang bộ hành động hoàn toàn khác:
- Lưu giữ Biên bản hòa giải không thành — đây là bằng chứng pháp lý quan trọng
- Đo đạc xác định ranh giới đất
- Chuẩn bị hồ sơ khởi kiện ra TAND Huyện

Đúng bước, đúng thứ tự, bảo toàn thời hiệu kiện.

---

## SLIDE 10 — CLOSING

*Slide tối với tên LexAI lớn ở giữa, 3 chip số liệu, và link demo.*

---

LexAI không chỉ là một chatbot pháp luật.

Đây là hạ tầng trí tuệ pháp lý — pipeline 7 giai đoạn, retrieval fusion 4 tín hiệu, bộ nhớ dài hạn, validator không mâu thuẫn — được xây dựng để **đồng hành và bảo vệ quyền lợi người dân Việt Nam**.

Với 96.6% chính xác, 365 test cases, và Beta PASS release gate, chúng tôi tự tin LexAI sẵn sàng phục vụ người dùng thực tế.

---

Ở Việt Nam, mỗi năm có hàng triệu tranh chấp đất đai, hàng trăm nghìn vụ ly hôn, hàng chục nghìn vụ sa thải trái luật.

Đa số những người đó không có luật sư. Không có người hướng dẫn. Và thường mất quyền lợi chỉ vì không biết **bước tiếp theo phải làm gì**.

LexAI được xây dựng cho những người đó.

**Khi pháp luật còn phức tạp — LexAI ở đây để chỉ đường.**

---

Cảm ơn Ban giám khảo. Chúng tôi sẵn sàng demo trực tiếp tại `localhost:3000`.

---

## Bảng Câu hỏi Dự phòng

| Câu hỏi có thể được hỏi | Trả lời ngắn gọn |
|---|---|
| Dữ liệu luật từ đâu? | File .doc/.pdf từ Bộ Tư pháp, cơ quan ban hành, được admin upload qua pipeline 8 giai đoạn. |
| Tại sao dùng 384-dim? | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 — hỗ trợ tiếng Việt, cân bằng tốc độ và độ chính xác. |
| LLM nào đang dùng? | OpenAI GPT-4o với tool-calling. Nếu LLM offline, system fallback sang assessment xác định luận — không downtime. |
| Privacy? | Dữ liệu user hoàn toàn isolated: `{$or: [{user_id}, {is_global: true}]}`. User A không thấy dữ liệu User B. |
| Scale như thế nào? | MongoDB Atlas sharding + vector index. Backend stateless, horizontal scale với FastAPI + Uvicorn. |
| Cập nhật luật mới? | Admin chạy seed script — idempotent, tự động skip file đã có. Luật mới online trong vài phút. |

---

*Tài liệu này đi kèm file `submission/LexAI_Presentation_v5.pptx`*  
*Hệ thống: Python 3.11 · FastAPI · MongoDB Atlas · sentence-transformers · OpenAI · React 19*
