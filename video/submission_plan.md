# Kế hoạch Chuẩn bị Bài dự thi LexAI (Hạn chót: 18:00 Thứ Bảy 31/05/2026)

Để bảo đảm bài dự thi đạt điểm tối đa ở cả 4 tiêu chí của Ban giám khảo (Sáng tạo, Kỹ thuật, Ảnh hưởng, Trình bày), chúng ta sẽ chia lộ trình thực hiện thành các mốc thời gian rõ ràng và phân bổ tài liệu cần thiết.

---

## 📅 Lộ trình và Mốc thời gian thực hiện (Milestones)

```mermaid
gantt
    title Lộ trình chuẩn bị bài dự thi LexAI
    dateFormat  YYYY-MM-DD
    section Tài liệu Kỹ thuật
    Biên soạn & hoàn thiện Tài liệu Kỹ thuật :active, 2026-05-27, 2026-05-29
    Rà soát & kiểm tra sơ đồ MongoDB : 2026-05-29, 2026-05-30
    section Video Demo
    Lên kịch bản quay chi tiết (Script) : 2026-05-27, 2026-05-28
    Quay màn hình giải pháp thực tế : 2026-05-29, 2026-05-30
    Lồng tiếng, biên tập video (Dưới 10 phút) : 2026-05-30, 2026-05-31
    section Nộp bài
    Tổng duyệt & Nộp bài dự thi trước 18:00 : 2026-05-31, 2026-05-31
```

### 1. Giai đoạn 1: Chuẩn bị Nội dung & Tài liệu Kỹ thuật (27/05 - 29/05)
* **Mục tiêu**: Hoàn thiện toàn bộ khung kiến trúc, sơ đồ dữ liệu và mô tả các pipeline của MongoDB.
* **Sản phẩm**: Tệp `technical_documentation.md` đã được viết sẵn đầy đủ các phân mục kỹ thuật cao cấp, sẵn sàng nộp bài.

### 2. Giai đoạn 2: Lên kịch bản & Quay Video Demo (28/05 - 30/05)
* **Mục tiêu**: Xây dựng kịch bản video cô đọng (dưới 10 phút), làm nổi bật giải pháp và quay các tính năng hoạt động mượt mà nhất.
* **Kế hoạch quay**:
  * **0:00 - 2:00**: Giới thiệu Use-case (Bài toán khó khăn khi tra cứu pháp luật Việt Nam, sự lỗi thời của việc tìm kiếm theo từ khóa thô sơ).
  * **2:00 - 5:00**: Trình diễn các tính năng cốt lõi (Phân tích vụ việc AI, Rà soát hợp đồng tự động, Tìm kiếm vụ việc tương tự với Vector Search và cơ chế fallback thông minh).
  * **5:00 - 8:00**: Trình bày kiến trúc kỹ thuật (Hệ thống GraphRAG cục bộ kết hợp với cơ sở dữ liệu MongoDB Atlas).
  * **8:00 - 10:00**: Điểm nổi bật & Tầm nhìn tương lai (Khả năng mở rộng, ý nghĩa xã hội và tiềm năng thương mại).

### 3. Giai đoạn 3: Biên tập & Nộp bài (30/05 - 31/05)
* **Mục tiêu**: Cắt ghép video, chèn slide/chú thích sắc nét và đóng gói toàn bộ bài dự thi trước 18:00 Thứ Bảy 31/05.

---

## 📂 Danh sách các File cần thiết cho bài dự thi

1. 📝 **Tệp Tài liệu Kỹ thuật chính thức**: `technical_documentation.md` (đã biên soạn chi tiết các phần sơ đồ MongoDB, Vector Search và Aggregation Pipelines).
2. 🎥 **Kịch bản quay Video chi tiết**: `video_script.md` (hướng dẫn từng phân cảnh, lời thoại thuyết minh và hành động trên màn hình khi quay demo).
3. 📁 **Source Code nén**: Tệp ZIP chứa mã nguồn hệ thống (đã được dọn dẹp thư mục tạm, bảo đảm chạy local mượt mà bằng `start.bat`).

---

## 🎯 Chiến lược giành điểm cao (Tiêu chí Giám khảo)

* **💡 Tính nguyên bản (30%)**: Làm nổi bật cơ chế **Multimodal GraphRAG kết hợp Vector Search của MongoDB** — tiếp cận thông minh vượt xa các chat bot RAG thông thường nhờ phân tích ranh giới và liên kết thực thể pháp lý.
* **⚙️ Triển khai kỹ thuật (30%)**: Trình bày rõ ràng cấu trúc dữ liệu MongoDB được thiết kế chuẩn hóa, cách áp dụng **Vector Search** đa chiều và sức mạnh của **Aggregation Pipelines** trong việc phân tích hành vi người dùng trên Dashboard.
* **🌍 Ảnh hưởng thực tế (30%)**: Chứng minh giải pháp giúp người dân và doanh nghiệp tự bảo vệ quyền lợi pháp lý, giảm thiểu rủi ro ký kết hợp đồng, có khả năng mở rộng lên hàng triệu người dùng nhờ cơ chế lưu trữ phân tán.
