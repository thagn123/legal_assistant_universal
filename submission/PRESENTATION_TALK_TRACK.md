# Presentation Talk Track — LexAI / ULKA

Lời thoại chi tiết cho từng segment. Viết theo ngôn ngữ tự nhiên, dễ đọc khi quay video.

---

## Segment 0: Hook (0:00–0:45)

*(Giọng chậm, rõ ràng, nhìn camera hoặc màn hình)*

---

"Giả sử hàng xóm của bạn vừa xây tường lấn 50 centimét vào đất của bạn.

Bạn mở Google. Bạn đọc 10 bài viết. Bài nào cũng nói 'liên hệ UBND', 'nên gặp luật sư', 'tùy tình huống'.

Không bài nào nói rõ: với trường hợp của tôi cụ thể — đã có sổ đỏ, hàng xóm đang lấn chiếm — bước tiếp theo của tôi là gì. Bước một. Không phải bước mười.

Chatbot pháp lý hiện tại cũng không giải quyết được vấn đề này. Vì chúng thường mắc một lỗi rất cơ bản:

Tự mâu thuẫn với những gì người dùng vừa nói.

Người dùng nói 'tôi đã có sổ đỏ' — chatbot vẫn gợi ý 'đi làm sổ đỏ'.
Người dùng nói 'tôi đã hòa giải không thành' — hệ thống vẫn khuyên 'đi hòa giải lại'.

Đây là LexAI — và đây là cách chúng tôi giải quyết vấn đề đó."

---

## Segment 1: Solution (0:45–1:30)

*(Có thể chỉ vào slide hoặc diagram đơn giản)*

---

"LexAI là một Legal Intelligence Assistant cho người dùng Việt Nam.

Không phải chatbot trả lời câu hỏi thông thường. Là một pipeline có kiểm chứng, gồm 7 giai đoạn xử lý.

Điểm khác biệt cốt lõi là ba điều:

Một: Hệ thống đọc input và trích xuất evidence status — người dùng đã có gì, đã làm gì.

Hai: Hệ thống truy xuất văn bản pháp lý từ MongoDB bằng vector search — tìm điều luật gần nghĩa nhất với tình huống.

Ba: Hệ thống validate output — bất kỳ gợi ý nào mâu thuẫn với evidence đã biết đều bị loại bỏ trước khi trả kết quả.

Và toàn bộ được kiểm thử với 365 test cases, benchmark trên 30 câu hỏi thực tế, và release gate tự động quyết định có deploy được chưa.

Tôi sẽ demo trực tiếp ba case thực tế."

---

## Segment 2: Demo 1 — Đất đai có sổ đỏ (1:30–4:00)

*(Gõ input, đợi, rồi giải thích)*

---

*[Khi gõ input]*
"Tôi nhập tình huống: Tôi đã có sổ đỏ, hàng xóm xây tường lấn 50 centimét đất của tôi, tôi cần làm gì.

Lưu ý: tôi đã nói rõ tôi có sổ đỏ. Hệ thống phải nhận ra điều này."

*[Đợi loading]*
"Hệ thống gửi query qua Stage 1 — phân loại domain. Stage 3 — retrieval fusion kết hợp 4 tín hiệu bao gồm MongoDB vector search. Stage 5 — LLM reasoning với tool-calling. Stage cuối — output validator."

*[Kết quả hiện ra, chỉ vào domain]*
"Domain được nhận dạng chính xác: đất đai.

Bây giờ tôi kiểm tra phần quan trọng nhất."

*[Zoom vào recommended_actions]*
"Nhìn vào Hành động được khuyến nghị.

Không có dòng nào gợi ý thu thập sổ đỏ. Không có 'xin cấp GCN'. Không có 'bổ sung giấy tờ đất'.

Tại sao? Vì OutputValidator đã đọc evidence status — sổ đỏ đã có, tức là PRESENT — và tự động loại bỏ những action mâu thuẫn đó.

Thay vào đó, actions đúng với tình huống: kiểm tra ranh giới, lập biên bản chứng cứ, yêu cầu UBND hòa giải theo Điều 202 Luật Đất đai.

Đây là hành vi mà chúng tôi kiểm thử tự động — để đảm bảo nó không bao giờ bị regression."

---

## Segment 3: Demo 2 — Bug Story S-05 (4:00–5:45)

*(Đây là đoạn kỹ thuật nhất — nói chậm hơn)*

---

*[Trước khi gõ input]*
"Case thứ hai là case quan trọng nhất về mặt kỹ thuật.

Trong quá trình manual QA, tester đã phát hiện một lỗi P0 — lỗi nghiêm trọng nhất.

Tình huống: người dùng đã đi hòa giải tại UBND xã. Hòa giải thất bại. Hàng xóm không ký biên bản. Người dùng hỏi bước tiếp theo.

Phiên bản cũ của hệ thống trả về: 'Nộp đơn yêu cầu hòa giải tại UBND cấp xã — bắt buộc theo Điều 202 trước khi khởi kiện.'

Đây là re-suggest bước người dùng đã làm và thất bại. Trong bối cảnh pháp lý, điều này không chỉ vô ích mà còn có thể làm người dùng mất thêm thời gian và bỏ lỡ thời hiệu khởi kiện."

*[Gõ input]*
"Tôi nhập: Tôi đã hòa giải ở xã nhưng không thành, hàng xóm vẫn lấn đất và không ký biên bản."

*[Đợi và chỉ vào kết quả]*
"Sau khi chúng tôi fix lỗi này và thêm 25 regression tests, hệ thống bây giờ nhận ra: đây là post-mediation case.

Nhìn vào recommended actions:

'Lưu giữ biên bản hòa giải không thành từ UBND xã — đây là tài liệu bắt buộc khi nộp đơn khởi kiện.'

'Tổng hợp chứng cứ ranh giới: bản đồ địa chính, ảnh hiện trạng lấn chiếm.'

'Chuẩn bị hồ sơ khởi kiện tại Tòa án nhân dân cấp huyện nơi có đất.'

Và key action trong full assessment: Bước ưu tiên nhất là chuẩn bị hồ sơ khởi kiện — bạn đã hoàn thành bước hòa giải bắt buộc.

Không re-suggest bước đã làm. Không gây nhầm lẫn.

Đây là câu chuyện: phát hiện bug thật qua QA → fix có mục tiêu → thêm regression test → 365 tests tất cả pass."

---

## Segment 4: Demo 3 — Ly hôn đơn phương (5:45–7:00)

---

*[Gõ input]*
"Case thứ ba — nhạy cảm hơn về mặt nội dung pháp lý.

Tôi nhập: Tôi muốn ly hôn đơn phương, có con 2 tuổi, chồng không đồng ý. Tôi có thể làm được không?"

*[Chờ và giải thích]*
"Manual QA có một yêu cầu cứng cho case này: hệ thống tuyệt đối không được nói 'không thể ly hôn' hoặc 'không có quyền ly hôn đơn phương'. Vì đó là sai về mặt pháp luật. Luật Hôn nhân Gia đình Việt Nam cho phép ly hôn đơn phương theo Điều 56."

*[Kết quả hiện ra]*
"Nhìn vào kết quả. Domain: gia đình — đúng.

Hệ thống giải thích: quyền yêu cầu ly hôn đơn phương tồn tại. Về nuôi con dưới 36 tháng — theo luật, ưu tiên mẹ nuôi con dưới 36 tháng nếu không có thỏa thuận khác.

Actions cụ thể: nộp đơn tại Tòa án, chuẩn bị các giấy tờ cần thiết.

Không có câu 'không thể'. Không có câu 'không được'. Manual QA scenario S-10 — PASS."

---

## Segment 5: Architecture + MongoDB (7:00–8:00)

---

*[Chỉ vào diagram hoặc slide]*
"Bây giờ tôi muốn nói nhanh về kiến trúc.

Pipeline 7 giai đoạn. Từ input người dùng đến response cuối cùng, có 7 lớp xử lý độc lập và có thể test riêng.

Stage 1 là Query Planner — phân loại domain thuần bằng keyword scoring. Không LLM, dưới 10 millisecond. Hỗ trợ cả tiếng Việt có dấu và không dấu.

Stage 3 là Retrieval Fusion Engine — đây là trái tim của hệ thống. Kết hợp 4 tín hiệu: MongoDB vector search với weight 45%, BM25 keyword 20%, graph expansion 25%, và behavior signal 10%.

Và MongoDB là nền tảng lưu trữ chính. Collection chunks_vec chứa toàn bộ law chunks với 384-dim embeddings. Index chunk_embedding_index cho phép $vectorSearch cosine similarity.

Pipeline aggregation: filter theo domain và user isolation, project vector score, threshold 0.55, sort và trả kết quả top-K.

Một hạn chế chúng tôi minh bạch: Atlas M0 giới hạn 3 vector search indexes. Chúng tôi đã dùng hết 3 slots. Collection legal_cases chưa có index — và release gate của chúng tôi tự phát hiện và báo cáo điều này."

---

## Segment 6: QA Numbers (8:00–9:15)

---

*[Chuyển sang terminal và reports]*
"Đây là kết quả kiểm thử.

[Terminal] 365 tests. 365 pass. 0 fail.

[Benchmark report] Benchmark 30 câu hỏi thực tế — top-1 domain accuracy 96.6%. 28 trong 29 câu hỏi pháp lý được phân loại đúng domain ngay lần đầu. Cross-domain error 0% — không có câu hỏi đất đai nào nhảy sang lao động.

[Release gate] Beta gate: PASS. Hệ thống sẵn sàng deploy cho beta users.

GA gate: FAIL. Chỉ vì một blocker infrastructure: thiếu case_embedding_index cho legal_cases. Fallback rate 100% — tất cả similar case queries đang trả demo data. Chúng tôi không hide điều này. Release gate tự phát hiện, tự báo cáo, tự chặn GA.

Và manual QA: 15 tình huống thực tế, sau khi fix bug S-05, 15/15 pass."

---

## Segment 7: Impact + Roadmap (9:15–10:00)

---

"Cuối cùng — tại sao điều này quan trọng.

Hơn 70% người Việt Nam chưa từng tiếp cận dịch vụ pháp lý chính thức. Tranh chấp đất đai, lao động, hôn nhân gia đình — những vấn đề ảnh hưởng trực tiếp đến cuộc sống — thường được giải quyết qua nghe nói, hoặc bỏ mặc.

LexAI không thay luật sư. Nhưng giúp người dùng biết bước tiếp theo của mình là gì, bằng chứng nào cần chuẩn bị, và không bị hệ thống tư vấn sai bước.

Roadmap gần hạn: upgrade Atlas M10+, tạo case vector index, GA gate PASS.

Roadmap xa hơn: contract upload, lawyer-in-the-loop review, legal workflow automation.

Cảm ơn các bạn đã xem demo."

---

## Câu fallback (nếu bị hỏi khó)

**Hỏi:** Accuracy 96.6% đo như thế nào?  
**Trả lời:** "30 câu hỏi thực tế, mỗi câu có expected_domain. Hệ thống dự đoán domain top-1. 28/29 câu đúng — Q03 là cross-domain ambiguous giữa dat_dai và hanh_chinh, cả hai domain đều có lý."

**Hỏi:** Tại sao fallback rate 100%?  
**Trả lời:** "Atlas M0 giới hạn 3 vector search indexes. Chúng tôi đã dùng hết 3 slots cho law chunks, templates, và risks. Index cho similar cases chưa tạo được. Release gate phát hiện và báo cáo — hệ thống hoàn toàn transparent."

**Hỏi:** Có live demo không?  
**Trả lời:** "Có thể demo live nếu backend đang chạy. Hoặc xem output đã capture trong qa/api_smoke_report.json và qa/retrieval_benchmark_results.json."
