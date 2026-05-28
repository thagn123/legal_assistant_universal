# KỊCH BẢN PHÂN CẢNH VIDEO DEMO — LEXAI (ULKA)
⏱️ **Thời lượng tối đa**: 10 phút | 🎥 **Độ phân giải khuyến nghị**: 1080p 60fps

> [!NOTE]
> Kịch bản này được thiết kế để bạn có thể vừa nhìn màn hình, vừa đọc thuyết minh (Voiceover) một cách tự nhiên nhất.
> Hãy giữ nhịp điệu đọc rõ ràng, tự tin, nhấn giọng ở các từ khóa công nghệ.

---

## 🎬 TÓM TẮT PHÂN BỔ THỜI GIAN VIDEO DEMO (TỔNG: 9 PHÚT 30 GIÂY)

- **Phần 1: Giới thiệu Use-case & Bài toán giải quyết (0:00 - 1:45)** — Tổng quan và slide vấn đề.
- **Phần 2: Demo trang Dashboard & Proactive Recommendations (1:45 - 3:00)** — Giao diện cá nhân hóa theo hành vi.
- **Phần 3: Demo Chat chuyên sâu qua Staged Pipeline & GraphRAG (3:00 - 5:30)** — Trọng tâm công nghệ.
- **Phần 4: Demo các tính năng chuyên gia nâng cao (5:30 - 7:00)** — Clause Coach, Evidence Gap, Lịch sử lưu trữ.
- **Phần 5: Demo Admin Panel & Ingestion Pipeline 8 bước (7:00 - 8:15)** — Luồng cách ly dữ liệu toàn cầu.
- **Phần 6: Kết luận & Điểm sáng công nghệ (8:15 - 9:30)** — Tóm tắt hiệu năng và sự tích hợp MongoDB Atlas.

---

## 📹 CHI TIẾT KỊCH BẢN PHÂN CẢNH VÀ LỜI THOẠI

### ⏱️ Phần 1: Giới thiệu Use-case & Bài toán giải quyết (0:00 - 1:45)

| Thời gian | Hình ảnh trên màn hình | Lời thoại thuyết minh (Voiceover) | Ghi chú kỹ thuật (Hậu kỳ) |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:25** | Hiển thị Slide 1: **LexAI — Trợ lý Pháp lý Thông minh**. Logo dự án và thông tin đội thi. | "Xin chào Ban giám khảo và các bạn độc giả. Chào mừng các bạn đến với buổi Demo sản phẩm **LexAI**, Trợ lý Pháp lý Thông minh được xây dựng trên nền tảng hạ tầng tri thức pháp luật Việt Nam vượt trội." | Xuất hiện slide mượt mà. Nhạc nền nhẹ nhàng, âm lượng vừa phải (dưới 10%). |
| **0:25 - 1:10** | Chuyển sang Slide 2: **Hạn chế của RAG truyền thống trong miền luật**. Liệt kê: 1. Mất cấu trúc văn bản; 2. Hallucination điều khoản; 3. Thiếu cá nhân hóa; 4. Thiếu tính kế thừa. | "Trong thực tế, việc áp dụng công nghệ AI vào tìm kiếm và tư vấn pháp luật gặp rất nhiều rào cản. Các mô hình RAG truyền thống thường làm phẳng văn bản luật thành các đoạn text thô, dẫn đến việc mất cấu trúc điều khoản, trích dẫn sai lệch điều luật và hoàn toàn thiếu đi tính cá nhân hóa hay sự kế thừa theo hành vi của người dùng." | Hiệu ứng xuất hiện từng dòng chữ (Bullet points) trên slide để thu hút sự chú ý. |
| **1:10 - 1:45** | Chuyển sang Slide 3: **Kiến trúc LexAI — Staged Pipelines & MongoDB Atlas**. Biểu diễn 2 luồng cốt lõi: Ingestion 8 bước và Query 7 bước. | "Để giải quyết triệt để vấn đề này, chúng tôi phát triển **LexAI** dựa trên hai trụ cột cốt lõi: Quy trình Ingestion 8 bước giúp giữ nguyên cấu trúc văn bản pháp luật, và Quy trình Query Intelligence 7 bước kết hợp **MongoDB Atlas Vector Search** cùng **GraphRAG** để đưa ra các câu trả lời chính xác vượt trội, được cá nhân hóa sâu sắc theo nhu cầu của từng đối tượng người dùng." | Zoom nhẹ vào biểu đồ sơ đồ hai pipelines. |

---

### ⏱️ Phần 2: Demo trang Dashboard & Proactive Recommendations (1:45 - 3:00)

| Thời gian | Hình ảnh trên màn hình | Lời thoại thuyết minh (Voiceover) | Ghi chú kỹ thuật (Hậu kỳ) |
| :--- | :--- | :--- | :--- |
| **1:45 - 2:20** | Màn hình chuyển sang giao diện thực tế của trang **Dashboard** của LexAI. Di chuột qua thẻ **Chào mừng quay lại [Tên người dùng]** (được lấy động từ UserMemory). Chỉ vào biểu đồ **Thống kê Hành vi Pháp lý** ở góc phải. | "Bây giờ, chúng ta hãy cùng bước vào giao diện thực tế của LexAI. Ngay khi đăng nhập, hệ thống sẽ chào đón người dùng bằng tên riêng nhờ cơ chế bộ nhớ chéo phiên hội thoại UserMemory. Biểu đồ hành vi trực quan hiển thị các lĩnh vực luật mà người dùng quan tâm nhất, được tính toán tự động dựa trên lịch sử tương tác thời gian thực lưu trong MongoDB." | Zoom cận cảnh vào lời chào cá nhân hóa và Biểu đồ hình quạt (Recharts). |
| **2:20 - 3:00** | Di chuột xuống khu vực **Gợi ý chủ động (Proactive Suggestions)** gồm các thẻ: Daily Digest, Gợi ý từ đồng nghiệp (Peer Trending) và Hành động tiếp theo (Next Best Actions - NBA). Nhấp thử vào một nút hành động nhanh. | "Không chỉ dừng lại ở việc phản hồi thụ động, LexAI chủ động phân tích các mẫu chuỗi hành vi và gợi ý các hành động tiếp theo thích hợp nhất như: soạn thảo điều khoản, kiểm tra rủi ro hợp đồng dựa trên các án lệ tương tự đang thịnh hành trong cộng đồng người dùng có cùng mối quan tâm." | Di chuột mượt mà, nhấn vào nút hành động để thấy UI phản hồi chuyển trang. |

---

### ⏱️ Phần 3: Demo Chat chuyên sâu qua Staged Pipeline & GraphRAG (3:00 - 5:30)

| Thời gian | Hình ảnh trên màn hình | Lời thoại thuyết minh (Voiceover) | Ghi chú kỹ thuật (Hậu kỳ) |
| :--- | :--- | :--- | :--- |
| **3:00 - 3:45** | Chuyển sang trang **Analyze (Trợ lý Hỏi đáp)**. Nhập câu hỏi mẫu vào ô chat: `"Tôi muốn tranh chấp hợp đồng đặt cọc mua đất đai do bên bán không chịu sang tên sổ đỏ, mức phạt cọc xử lý như thế nào?"` rồi ấn Gửi. | "Chúng ta cùng thử nghiệm tính năng quan trọng nhất: Trợ lý hỏi đáp pháp lý thông minh. Tôi sẽ nhập một tình huống tranh chấp hợp đồng đặt cọc mua bán đất đai thực tế. Một câu hỏi phức tạp đan xen giữa luật Đất đai, luật Dân sự và Hợp đồng." | Hiển thị chữ gõ trên màn hình rõ ràng. |
| **3:45 - 4:40** | Câu hỏi được gửi đi. Trên giao diện chat hiển thị thanh trạng thái động hiển thị quá trình xử lý qua các Stage: *Stage 1: Lập kế hoạch truy vấn, Stage 3: Hợp nhất kết quả truy xuất (Vector + BM25 + Graph + Hành vi), Stage 4: Tra cứu đồ thị quan hệ GraphRAG, Stage 5: Trình suy luận LLM Tool-Calling...* | "Khi câu hỏi được gửi, hệ thống kích hoạt quy trình xử lý 7 giai đoạn. Stage 1 nhận diện miền luật Đất đai và Hợp đồng trong chưa đầy 10 mili-giây. Stage 3 thực hiện **Hợp nhất truy xuất (Retrieval Fusion)** giữa Vector Search, BM25 và từ khóa. Đặc biệt, Stage 4 kích hoạt **GraphRAG** để duyệt qua các liên kết pháp lý như mối quan hệ `OVERRIDES` hay `AMENDS`, giúp loại bỏ hoàn toàn các điều luật đã hết hiệu lực." | **Zoom rất cận cảnh** vào thanh trạng thái chạy các stages xử lý. BGK cực kỳ thích điểm này. |
| **4:40 - 5:30** | Kết quả phân tích hiện ra đầy đủ bằng Tiếng Việt. Có cấu trúc rõ ràng: Tóm tắt tình huống, Đánh giá pháp lý, Điều khoản áp dụng (có số điều luật rõ ràng), Khuyến nghị hành động. Rà chuột qua các thẻ trích dẫn nguồn luật. | "Kết quả trả về vô cùng chi tiết và có cấu trúc chặt chẽ. Mọi lập luận pháp lý đều được gắn kèm trích dẫn chính xác đến từng Điều, Khoản của Luật Đất đai và Bộ luật Dân sự 2015. Người dùng hoàn toàn có thể nhấp vào nguồn trích dẫn để đọc trực tiếp nội dung gốc văn bản pháp luật, đảm bảo tính giải thích cao và tuyệt đối không xảy ra hiện tượng ảo tưởng thông tin." | Zoom vào các trích dẫn nguồn điều luật (Citations) và các liên kết nguồn gốc. |

---

### ⏱️ Phần 4: Demo các tính năng chuyên gia nâng cao (5:30 - 7:00)

| Thời gian | Hình ảnh trên màn hình | Lời thoại thuyết minh (Voiceover) | Ghi chú kỹ thuật (Hậu kỳ) |
| :--- | :--- | :--- | :--- |
| **5:30 - 6:15** | Nhấp vào tính năng **Clause Coach (Phân tích Hợp đồng)**. Cho thấy màn hình tải lên một điều khoản hợp đồng. Hệ thống trả về danh sách phân tích rủi ro (Risk Analysis) với mức độ màu đỏ/vàng/xanh và đề xuất điều khoản sửa đổi phù hợp. | "Bên cạnh hỏi đáp, LexAI cung cấp các công cụ chuyên sâu như **Clause Coach** hỗ trợ rà soát hợp đồng. AI tự động bóc tách các điều khoản, đối chiếu với cơ sở dữ liệu rủi ro của MongoDB Atlas và đưa ra đề xuất điều khoản sửa đổi an toàn hơn cho người dùng." | Hiệu ứng highlight các mức độ rủi ro bằng màu sắc đỏ, vàng, xanh lá. |
| **6:15 - 6:45** | Di chuyển sang trang **Evidence Gap (Đánh giá Chứng cứ)** hoặc **Lịch sử Phân tích (Analysis History)**. Nhấp thử vào một lịch sử đã lưu trước đó, tải xuống file JSON chứa toàn bộ trace suy luận. | "Người dùng có thể dễ dàng lưu lại các phiên phân tích vào bộ nhớ đám mây cá nhân. Trong trang Lịch sử Phân tích, toàn bộ các lượt rà soát, tư vấn trước đây được lưu trữ phân loại khoa học theo 11 nhóm chủ đề pháp lý khác nhau và hỗ trợ tải xuống định dạng JSON để tiện trao đổi với luật sư." | Click vào nút **Lưu phân tích**, xuất hiện thông báo Toast chúc mừng thành công. Click nút **Tải JSON**. |
| **6:45 - 7:00** | Quay lại trang Profile cá nhân, chỉ vào khu vực **"AI ghi nhớ về bạn"** hiển thị thông tin tên, tuổi, nghề nghiệp, khu vực sinh sống đã được AI tự động trích xuất từ các câu chuyện chat thông qua Daemon Thread Reflection. | "Đặc biệt, hệ thống sở hữu cơ chế **Reflection Agent** chạy ngầm. Sau mỗi phiên chat, AI tự động đúc rút thông tin cá nhân cơ bản và ghi nhớ lâu dài mà không làm chậm tốc độ phản hồi của người dùng, giúp các phiên làm việc sau ngày càng thông minh và cá nhân hóa sâu sắc hơn." | Zoom vào phần thông tin cá nhân được ghi nhớ trong Profile. |

---

### ⏱️ Phần 5: Demo Admin Panel & Ingestion Pipeline 8 bước (7:00 - 8:15)

| Thời gian | Hình ảnh trên màn hình | Lời thoại thuyết minh (Voiceover) | Ghi chú kỹ thuật (Hậu kỳ) |
| :--- | :--- | :--- | :--- |
| **7:00 - 7:35** | Màn hình chuyển sang giao diện đăng nhập Admin tại `/admin/login`. Nhập mật khẩu admin rồi chuyển vào **Admin Dashboard** hiển thị biểu đồ thống kê hệ thống (Recharts). | "Hệ thống LexAI được thiết kế với kiến trúc dữ liệu cô lập an toàn. Đối với quản trị viên hệ thống, chúng tôi cung cấp một giao diện Admin Panel riêng biệt. Tại đây, Admin có thể theo dõi toàn bộ trạng thái công việc và số lượng dữ liệu toàn hệ thống." | Hiển thị quá trình login admin và hiển thị trang Admin Dashboard tuyệt đẹp. |
| **7:35 - 8:15** | Nhấp vào **Quản lý tài liệu**, chọn tải lên một file tài liệu pháp luật (PDF/DOCX). Hệ thống hiển thị tiến trình xử lý job qua 8 stage của Ingestion Pipeline. Giải thích thuộc tính `is_global`. | "Khi Admin tải lên các nghị định hoặc luật mới, tài liệu sẽ đi qua quy trình Ingestion Pipeline 8 bước nghiêm ngặt: từ tiền xử lý, cấu trúc hóa, cắt nhỏ ngữ nghĩa theo điều luật, đến vẽ đồ thị quan hệ và nhúng vector. Mọi tài liệu Admin tải lên đều tự động gắn cờ `is_global: true` trong MongoDB, cho phép mọi người dùng cùng truy cập mà không xâm phạm dữ liệu cá nhân của nhau." | Zoom cận cảnh vào tiến trình chạy Ingestion Job. |

---

### ⏱️ Phần 6: Kết luận & Điểm sáng công nghệ (8:15 - 9:30)

| Thời gian | Hình ảnh trên màn hình | Lời thoại thuyết minh (Voiceover) | Ghi chú kỹ thuật (Hậu kỳ) |
| :--- | :--- | :--- | :--- |
| **8:15 - 9:00** | Hiển thị Slide 4: **Điểm nhấn kỹ thuật MongoDB Atlas & Hiệu năng**. Liệt kê: 1. Vector Search + Post-filter; 2. Collaborative Filtering Aggregation; 3. Decay Rate & Freshness Signal; 4. Offline Fallback. | "Để tóm tắt về điểm nhấn kỹ thuật, LexAI tự hào tích hợp sâu sắc các tính năng tiên tiến nhất của **MongoDB Atlas**:<br>1. **Vector Search** cosine 384 chiều giúp truy xuất ngữ nghĩa chính xác;<br>2. **Aggregation Pipelines** phức tạp hỗ trợ tính toán gợi ý cộng tác theo thời gian thực và khai phá mẫu hành vi;<br>3. Cơ chế suy luận an toàn kết hợp Reranking theo 6 tín hiệu (freshness, popularity, behavior);<br>4. Và khả năng hoạt động ổn định nhờ cơ chế **Deterministic Fallback** tự động khi LLM gặp sự cố." | Các dòng chữ trên slide lần lượt hiện ra sắc nét. |
| **9:00 - 9:30** | Hiển thị Slide 5: **Lời cảm ơn & Thông tin liên hệ**. | "LexAI không chỉ là một chatbot, đó là cả một nền tảng hạ tầng trí tuệ nhân tạo toàn diện cho pháp luật Việt Nam. Chúng tôi tin rằng giải pháp này sẽ mang lại giá trị thực tiễn to lớn cho cộng đồng pháp lý và mọi người dân Việt Nam.<br><br>Cảm ơn Ban giám khảo đã chú ý lắng nghe phần trình bày của đội thi chúng tôi. Rất mong nhận được sự phản hồi và đánh giá từ quý vị!" | Nhạc nền tăng âm lượng nhẹ nhàng ở cuối video. Màn hình tối dần (Fade to black) chuyên nghiệp. |

---

## 🎬 HƯỚNG DẪN KỸ THUẬT QUAY VÀ BIÊN TẬP
1. **Âm thanh (Voiceover)**: Hãy thu âm trước, sau đó phát lại file thu âm và thực hiện các thao tác trên màn hình UI theo lời nói để khớp thời gian hoàn hảo nhất.
2. **Hiệu ứng Zoom**: Khi dựng video (bằng Camtasia, Premiere hoặc CapCut), hãy chủ động phóng to màn hình ở các chi tiết như:
   - Đoạn hội thoại chat có hiển thị nguồn trích dẫn luật.
   - Các Stage Processing Bar trong lúc chờ phản hồi chat.
   - Các biểu đồ thống kê Dashboard.
   - Các đoạn code Python / JSON (nếu có chèn minh họa kỹ thuật).
3. **Subtitles**: Bạn nên xuất file SRT phụ đề tiếng Việt và chèn trực tiếp vào video ở cạnh dưới để BGK dễ đọc và hiểu nội dung thuyết minh rõ ràng hơn.
