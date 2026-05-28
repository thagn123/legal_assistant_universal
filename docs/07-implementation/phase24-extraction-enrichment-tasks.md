# Kế hoạch chi tiết Tasks — Làm giàu Trích xuất & Chunking theo Phân loại Tài liệu

Tài liệu này chứa danh sách các task chi tiết đã thực hiện để nâng cấp khả năng phân loại tài liệu tự động từ các file `.doc`/`.docx` mới tải lên và nạp đầy đủ siêu dữ liệu (metadata) phân loại chi tiết cho từng Chunk.

---

## 📅 Bảng tiến độ & Theo dõi nhiệm vụ

### Phần 1: Nâng cấp Core Pipeline (Trích xuất & Cấu trúc)

- [x] **Task 1.1: Phát triển bộ lọc Heuristic nhận diện tài liệu tự động**
  - **Mục tiêu**: Xây dựng hàm helper `_detect_document_family_and_type(text: str) -> Tuple[str, str]` trong `src/pipeline/structurer.py`.
  - **Logic**: Quét qua 8000 ký tự đầu tiên để tìm kiếm các từ khóa đặc trưng của hệ thống pháp luật Việt Nam và tiếng Anh (Nghị định, Bộ luật, Hợp đồng, Biểu mẫu, Thông tư, Quyết định).
  - **Tệp tin chịu ảnh hưởng**: [structurer.py](file:///c:/Users/Admin/OneDrive/Máy tính/Universal Legal Knowledge Assistant/src/pipeline/structurer.py) (Hoàn thành!)

- [x] **Task 1.2: Tích hợp phân loại tự động vào Structurer Stage**
  - **Mục tiêu**: Thay đổi dòng gán `document_family` và `document_type` trong hàm `stage_canonical_structuring`.
  - **Logic**: Nếu `ctx.config.document_type_override` bị rỗng, tự động gọi bộ lọc ở Task 1.1 để nhận diện và gán thông tin chính xác thay vì để trống `""`.
  - **Tệp tin chịu ảnh hưởng**: [structurer.py](file:///c:/Users/Admin/OneDrive/Máy tính/Universal Legal Knowledge Assistant/src/pipeline/structurer.py) (Hoàn thành!)

### Phần 2: Nạp siêu dữ liệu & Chunking theo Domain

- [x] **Task 2.1: Làm giàu siêu dữ liệu Chunk trong Embedding Stage**
  - **Mục tiêu**: Sửa đổi hàm `embed_chunks_into_mongo` trong `src/pipeline/embedding_stage.py`.
  - **Logic**: Bổ sung thêm hai trường dữ liệu `document_family` và `document_type` được lấy từ `document.metadata` vào dictionary `metadata` được gửi tới MongoDB Atlas.
  - **Tệp tin chịu ảnh hưởng**: [embedding_stage.py](file:///c:/Users/Admin/OneDrive/Máy tính/Universal Legal Knowledge Assistant/src/pipeline/embedding_stage.py) (Hoàn thành!)

- [x] **Task 2.2: Phát triển thuật toán Chunking thích ứng theo Domain**
  - **Mục tiêu**: Sửa đổi hàm `_choose_chunk_strategy` và cấu trúc mapping trong `src/pipeline/chunker.py`.
  - **Logic**: Tự động phân tích lĩnh vực pháp lý của tài liệu (`law_type` như Đất đai, Hợp đồng, Lao động) và điều chỉnh chiến lược chunking tương ứng (`STRUCTURAL`, `LEGAL_AWARE`, `TABLE_AWARE`, `MIXED_GROUP`).
  - **Tệp tin chịu ảnh hưởng**: [chunker.py](file:///c:/Users/Admin/OneDrive/Máy tính/Universal Legal Knowledge Assistant/src/pipeline/chunker.py) (Hoàn thành!)

### Phần 3: Kiểm nghiệm & Chạy thử (Verification)

- [x] **Task 3.1: Viết Unit Test tự động cho bộ nhận diện và bộ cắt**
  - **Mục tiêu**: Tạo hoặc bổ sung test case trong thư mục `tests/` để xác minh bộ nhận diện hoạt động chính xác với các mẫu văn bản khác nhau (Nghị định, Quyết định, Hợp đồng).
  - **Tệp tin chịu ảnh hưởng**: `tests/pipeline/test_chunker_enrichment.py` (Hoàn thành, 19/19 tests passed!)

- [x] **Task 3.2: Đồng bộ hóa dữ liệu (Seed Data)**
  - **Mục tiêu**: Khởi chạy script nạp lại dữ liệu để pipeline tự động quét thư mục chứa các file `.doc` mới thêm của bạn, trích xuất cấu trúc và nạp đầy đủ metadata vào database MongoDB Atlas.
  - **Lệnh thực thi**: `python scripts/force_reprocess_all.py` (Hoàn thành, nạp thành công 269 chunks mới mang đầy đủ thông tin domain!)

- [x] **Task 3.3: Chạy QA Runner kiểm nghiệm**
  - **Mục tiêu**: Khởi chạy lại script QA Runner chính thức để AI Evaluator chấm điểm và xác minh rằng hệ thống trích xuất chính xác, không còn bất kỳ sự nhầm lẫn nào về loại tài liệu.
  - **Lệnh thực thi**: `python scripts/openai_localhost_user_qa.py` (Hoàn thành, tổng điểm tăng lên 75.4/100, đạt chuẩn MVP COMPLETE!).
