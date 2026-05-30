# Video Demo Script — LexAI / ULKA

**Tổng thời gian:** ~10 phút  
**Ngôn ngữ:** Tiếng Việt  
**Format:** Màn hình quay + lời thoại  

---

## Cấu trúc tổng quan

| Segment | Thời gian | Nội dung |
|---|---|---|
| 0 | 0:00–0:45 | Hook + Bài toán |
| 1 | 0:45–1:30 | Giải pháp overview |
| 2 | 1:30–4:00 | Demo 1: Đất đai có sổ đỏ |
| 3 | 4:00–5:45 | Demo 2: Hòa giải không thành (bug story) |
| 4 | 5:45–7:00 | Demo 3: Ly hôn đơn phương |
| 5 | 7:00–8:00 | Kiến trúc + MongoDB |
| 6 | 8:00–9:15 | QA Results |
| 7 | 9:15–10:00 | Impact + Roadmap |

---

## Segment 0: Hook + Bài toán (0:00–0:45)

> *[Màn hình: trang chủ LexAI, chưa nhập gì]*

**Lời thoại:**

"Có bao giờ bạn thắc mắc: khi hàng xóm lấn chiếm đất của mình, mình phải làm gì đầu tiên? Hay khi công ty nợ lương, mình có quyền gì?

Phần lớn người Việt Nam chưa bao giờ gặp luật sư. Họ tìm trên Google, nhận được hàng chục bài viết chung chung, không biết bước nào áp dụng cho tình huống cụ thể của mình.

Chatbot pháp lý thông thường cũng không giải quyết được — vì chúng hay mắc một lỗi nghiêm trọng: **tự mâu thuẫn với những gì người dùng vừa nói**. Người dùng nói 'tôi đã có sổ đỏ' — chatbot vẫn gợi ý 'đi làm sổ đỏ'. Người dùng nói 'tôi đã hòa giải không thành' — hệ thống vẫn khuyên 'đi hòa giải'."

---

## Segment 1: Giải pháp (0:45–1:30)

> *[Màn hình: sơ đồ pipeline đơn giản hoặc slide]*

**Lời thoại:**

"LexAI là Legal Intelligence Assistant cho người dùng Việt Nam. Không phải chatbot. Là một pipeline có kiểm chứng.

Hệ thống làm 3 việc mà chatbot thông thường không làm được:

Thứ nhất, **trích xuất evidence status** — nhận biết người dùng đã có gì, đã làm gì.

Thứ hai, **truy xuất văn bản pháp lý** bằng MongoDB Vector Search — tìm điều luật gần nghĩa nhất với tình huống.

Thứ ba, **validate output** — bất kỳ gợi ý nào mâu thuẫn với evidence đã biết đều bị loại bỏ.

Và toàn bộ quy trình được kiểm thử tự động — 365 test cases, benchmark trên 30 câu hỏi thực tế, và release gate tự động quyết định có đủ điều kiện deploy hay không.

Bây giờ tôi sẽ demo trực tiếp."

---

## Segment 2: Demo 1 — Đất đai có sổ đỏ (1:30–4:00)

> *[Mở trang /analyze. Nhập vào ô input:]*

```
Tôi đã có sổ đỏ, hàng xóm xây tường lấn 50cm đất của tôi, tôi cần làm gì?
```

> *[Nhấn Phân tích. Đợi kết quả. Zoom vào phần Recommended Actions.]*

**Lời thoại trong khi chờ:**

"Tôi nhập tình huống thực tế. Người dùng đã nói rõ: tôi đã có sổ đỏ. Hệ thống phải nhận ra điều này."

> *[Kết quả hiện ra. Trỏ vào phần domain detection.]*

**Lời thoại khi kết quả hiện:**

"Domain được nhận dạng chính xác: đất đai. Confidence cao.

Bây giờ tôi sẽ kiểm tra phần quan trọng nhất — recommended actions.

[Zoom vào Recommended Actions]

Thấy không? Không có dòng nào gợi ý 'đi làm sổ đỏ', 'thu thập sổ đỏ', hay 'xin cấp GCN lần đầu'. Hệ thống đã nhận ra sổ đỏ đã có — evidence status = PRESENT — và OutputValidator đã loại bỏ những action mâu thuẫn đó trước khi trả kết quả.

Thay vào đó, actions đúng với tình huống: kiểm tra ranh giới, thu thập chứng cứ lấn chiếm, yêu cầu UBND hòa giải hoặc khởi kiện.

[Trỏ vào phần Full Assessment]

Full assessment giải thích rõ: vì đã có sổ đỏ, vị thế pháp lý mạnh. Bước tiếp theo là ghi nhận chứng cứ lấn chiếm và yêu cầu hòa giải tại UBND phường/xã theo Điều 202 Luật Đất đai."

---

## Segment 3: Demo 2 — Hòa giải không thành (4:00–5:45)

> *[Mở tab mới hoặc clear input. Nhập:]*

```
Tôi đã có sổ đỏ, hàng xóm xây tường lấn 50cm đất của tôi, tôi cần làm gì?
```

> *[Nhấn Phân tích. Đợi kết quả.]*

**Lời thoại trước khi kết quả hiện:**

"Đây là case quan trọng nhất trong QA của chúng tôi.

Người dùng đã hoàn thành bước hòa giải tại UBND. Đây là bước bắt buộc theo Luật Đất đai trước khi khởi kiện. Người dùng đã làm xong — và thất bại. Bây giờ họ cần bước tiếp theo.

Vấn đề là: phiên bản cũ của hệ thống vẫn gợi ý 'Nộp đơn yêu cầu hòa giải tại UBND cấp xã' — tức là lặp lại bước đã làm rồi. Đây là lỗi P0 được phát hiện trong manual QA."

> *[Kết quả hiện ra. Zoom vào Recommended Actions.]*

**Lời thoại khi kết quả hiện:**

"Nhìn vào recommended actions bây giờ.

Không có dòng nào gợi ý hòa giải nữa. Thay vào đó:

- 'Lưu giữ biên bản hòa giải không thành — đây là tài liệu bắt buộc khi nộp đơn khởi kiện'
- 'Tổng hợp chứng cứ ranh giới: bản đồ địa chính, ảnh hiện trạng'
- 'Chuẩn bị hồ sơ khởi kiện tại Tòa án nhân dân cấp huyện'

[Trỏ vào key_action / full_assessment]

Và key action: 'Bước ưu tiên nhất: chuẩn bị hồ sơ khởi kiện tại Tòa án nhân dân cấp huyện — bạn đã hoàn thành bước hòa giải bắt buộc.'

Đây là điểm khác biệt thật sự của hệ thống: không phải trả lời dài, mà là không tự mâu thuẫn với trạng thái thực tế của người dùng.

Và lỗi này đã được phát hiện qua manual QA — chúng tôi viết 25 regression tests để đảm bảo nó không tái xuất hiện."

---

## Segment 4: Demo 3 — Ly hôn đơn phương (5:45–7:00)

> *[Nhập:]*

```
Tôi muốn ly hôn đơn phương, có con 2 tuổi, chồng tôi không đồng ý ly hôn. Tôi có thể làm được không?
```

> *[Đợi kết quả.]*

**Lời thoại:**

"Case cuối là về hôn nhân gia đình — một trong những case nhạy cảm nhất trong QA.

Yêu cầu của manual QA với case này: hệ thống tuyệt đối không được nói 'bạn không thể ly hôn' hay 'không có quyền ly hôn đơn phương' — vì đó là sai về pháp lý. Luật Hôn nhân Gia đình Việt Nam cho phép ly hôn đơn phương khi đủ điều kiện.

[Kết quả hiện ra]

Hệ thống giải thích đúng: quyền yêu cầu ly hôn đơn phương tồn tại theo Điều 56 Luật Hôn nhân Gia đình 2014. Về nuôi con dưới 36 tháng tuổi — theo quy định, con dưới 36 tháng ưu tiên ở với mẹ nếu không có thỏa thuận khác.

Không có dòng nào nói 'không thể'. Domain: gia_dinh. Actions: cụ thể và đúng theo pháp luật."

---

## Segment 5: Kiến trúc + MongoDB (7:00–8:00)

> *[Chuyển sang màn hình diagram hoặc slide kiến trúc]*

**Lời thoại:**

"Bây giờ tôi muốn nói nhanh về kiến trúc kỹ thuật.

Hệ thống là một pipeline 7 giai đoạn. Từ input người dùng đến response, có 7 lớp xử lý độc lập.

[Chỉ vào từng bước trong diagram]

Stage 1: Query Planner — phân loại domain bằng keyword scoring, không dùng LLM, dưới 10 millisecond. Hỗ trợ cả tiếng Việt có dấu và không dấu.

Stage 3: Retrieval Fusion — đây là trái tim của hệ thống. Kết hợp 4 tín hiệu: Vector Search 45%, BM25 keyword 20%, Graph expansion 25%, và Behavior boost 10%.

[Chuyển sang màn hình MongoDB Atlas nếu có]

MongoDB là nền tảng lưu trữ chính. Collection chunks_vec chứa toàn bộ law chunks với 384-dim embeddings. Vector search index cho phép tìm kiếm theo ngữ nghĩa — không phải exact match.

Pipeline aggregation: filter theo domain, project vector score, apply threshold 0.55, sort và trả kết quả top-K.

[Nói nhanh về limitation]

Một limitation minh bạch: Atlas M0 giới hạn 3 vector search indexes. Chúng tôi đã dùng hết 3 slots cho law chunks, templates, và risks. Collection legal_cases chưa có vector index — và release gate của chúng tôi tự động phát hiện điều này và chặn GA."

---

## Segment 6: QA Results (8:00–9:15)

> *[Mở qa/release_gate_report.md hoặc terminal]*

**Lời thoại:**

"[Chỉ vào terminal output]

Toàn bộ test suite: 365 tests, 365 pass, 0 fail.

[Chuyển sang benchmark report]

Benchmark trên 30 câu hỏi thực tế:
- Top-1 domain accuracy: 96.6%. Nghĩa là 28 trong 29 câu hỏi pháp lý được phân loại đúng domain ngay lần đầu.
- Cross-domain error: 0%. Không có câu hỏi đất đai nào bị nhảy sang lao động hay ngược lại.
- Empty rate: 0%. Mọi câu hỏi đều có kết quả.

[Chỉ vào release gate report]

Beta gate: PASS. Hệ thống sẵn sàng deploy cho beta users.

GA gate: FAIL — chỉ vì một blocker infrastructure: thiếu vector index cho similar cases. Chúng tôi không hide điều này. Release gate tự động phát hiện và ghi rõ trong report.

Và manual QA: 15 tình huống thực tế, sau khi fix bug S-05, đạt 15/15 pass."

---

## Segment 7: Impact + Roadmap (9:15–10:00)

**Lời thoại:**

"Cuối cùng — tại sao dự án này có ý nghĩa?

Theo khảo sát, hơn 70% người Việt Nam chưa bao giờ tiếp cận dịch vụ pháp lý chính thức. Tranh chấp đất đai, lao động, hôn nhân — những vấn đề ảnh hưởng trực tiếp đến cuộc sống — thường được giải quyết qua nghe nói, tin đồn, hoặc bỏ mặc.

LexAI không thay thế luật sư. Nhưng nó giúp người dùng biết: bước tiếp theo của mình là gì, bằng chứng nào cần chuẩn bị, và đâu là cơ quan giải quyết đúng thẩm quyền.

Roadmap gần hạn: upgrade Atlas M10+, tạo case vector index, hoàn tất GA gate.

Roadmap xa hơn: contract upload, lawyer-in-the-loop review, legal workflow automation cho doanh nghiệp.

Cảm ơn các bạn đã xem demo. Tôi sẵn sàng trả lời câu hỏi."

---

## Lưu ý khi quay

- **Tắt notifications** trên màn hình trước khi quay
- **Phóng to font** trong terminal/browser (Ctrl+= hoặc 125%)
- **Zoom vào kết quả** sau mỗi demo — đặc biệt phần recommended_actions
- **Pause 2 giây** sau mỗi kết quả quan trọng để giám khảo đọc
- **Không cần perfect take** — natural và chân thực tốt hơn scripted
- Nếu có backend đang chạy: **demo live** tốt hơn video pre-recorded
- Nếu không có backend: **quay màn hình với kết quả đã có sẵn** từ file JSON/MD
