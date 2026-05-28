# Phase 24 OpenAI QA Auto Fix Plan
   
Được tự động sinh ra vào ngày 2026-05-28 dựa trên kết quả kiểm thử tự động Localhost QA.

## 1. Summary
* **Tổng số vấn đề phát hiện**: 12
  * **Blocker**: 1
  * **Major**: 8
  * **Minor**: 3

## 2. Blockers (Bắt buộc phải sửa ngay lập tức)

### B.1 — [LegalAnalysis] Thiếu thông tin pháp lý chính xác
- **Mô tả hành vi thực tế**: Không có thông tin pháp lý cụ thể và không đáp ứng các yêu cầu khẳng định.
- **Hành vi mong muốn**: Cung cấp thông tin về quyền lợi của người lao động theo luật lao động Việt Nam.
- **Đề xuất khắc phục**: Cần cập nhật cơ sở dữ liệu pháp lý và đảm bảo cung cấp thông tin chính xác cho các yêu cầu khẳng định.

## 3. Major Issues (Ưu tiên sửa trước khi Demo)

### M.1 — [EvidenceCitation] Thiếu thông tin về chia tài sản
- **Mô tả hành vi thực tế**: Không đề cập đến nguyên tắc chia đôi tài sản.
- **Hành vi mong muốn**: Cung cấp thông tin rõ ràng về nguyên tắc chia tài sản chung.
- **Đề xuất khắc phục**: Cần bổ sung thông tin về nguyên tắc chia tài sản chung theo luật pháp.

### M.2 — [SimilarCases] Thiếu căn cứ pháp lý cụ thể
- **Mô tả hành vi thực tế**: Không có dẫn chứng pháp lý nào được cung cấp.
- **Hành vi mong muốn**: Cung cấp thông tin pháp lý cụ thể liên quan đến quyền nuôi con và nghĩa vụ cấp dưỡng.
- **Đề xuất khắc phục**: Cần bổ sung các điều luật cụ thể liên quan đến quyền nuôi con và nghĩa vụ cấp dưỡng trong phản hồi.

### M.3 — [NextBestAction] Thiếu dẫn chứng pháp lý cho một số hành động
- **Mô tả hành vi thực tế**: Một số hành động không có dẫn chứng pháp lý rõ ràng.
- **Hành vi mong muốn**: Mỗi hành động gợi ý đều có dẫn chứng pháp lý cụ thể.
- **Đề xuất khắc phục**: Cần đảm bảo rằng tất cả các hành động gợi ý đều có dẫn chứng pháp lý cụ thể.

### M.4 — [EvidenceCitation] Thiếu dẫn chứng pháp lý cụ thể
- **Mô tả hành vi thực tế**: Không có dẫn chứng nào được cung cấp.
- **Hành vi mong muốn**: Có dẫn chứng điều luật cụ thể liên quan đến sa thải trái luật.
- **Đề xuất khắc phục**: Cần bổ sung các điều luật cụ thể liên quan đến sa thải trái luật trong phần thông tin vụ việc.

### M.5 — [NextBestAction] Gợi ý hành động không liên quan
- **Mô tả hành vi thực tế**: Chỉ cung cấp các vụ việc tương tự mà không có hành động cụ thể.
- **Hành vi mong muốn**: Gợi ý các hành động cụ thể cho người lao động trong tình huống bị chấm dứt hợp đồng.
- **Đề xuất khắc phục**: Cần phát triển các gợi ý hành động cụ thể dựa trên tình huống của người dùng.

### M.6 — [Digest] Thiếu thông tin digest
- **Mô tả hành vi thực tế**: Thông tin digest không được cung cấp.
- **Hành vi mong muốn**: Thông tin digest đầy đủ và chính xác về các hoạt động pháp lý.
- **Đề xuất khắc phục**: Cần đảm bảo rằng thông tin digest được tạo ra và hiển thị cho người dùng.

### M.7 — [Legal Relevance] Thiếu tính thân thiện trong phản hồi
- **Mô tả hành vi thực tế**: Phản hồi có phần khô khan và thiếu sự cá nhân hóa.
- **Hành vi mong muốn**: Phản hồi thân thiện và dễ hiểu cho người dùng.
- **Đề xuất khắc phục**: Cải thiện ngôn ngữ phản hồi để trở nên thân thiện hơn với người dùng.

### M.8 — [Evidence/Citation Usefulness] Căn cứ pháp lý không đủ mạnh
- **Mô tả hành vi thực tế**: Một số điều luật được đề cập nhưng không có dẫn chứng cụ thể.
- **Hành vi mong muốn**: Cung cấp dẫn chứng cụ thể cho từng điều luật liên quan.
- **Đề xuất khắc phục**: Bổ sung dẫn chứng cụ thể cho từng điều luật trong phản hồi.

## 4. Minor Issues (Cải thiện trải nghiệm và tối ưu hóa)

### Mi.1 — [RecommendationQuality] Gợi ý hành động không phù hợp
- **Đề xuất khắc phục**: Cần cải thiện khả năng gợi ý hành động dựa trên ngữ cảnh cụ thể của người dùng.

### Mi.2 — [error_resilience] Thông điệp lỗi không thân thiện
- **Đề xuất khắc phục**: Cần cải thiện thông điệp lỗi để hướng dẫn người dùng tốt hơn.

### Mi.3 — [Evidence/Citation] Thiếu trích dẫn điều luật cụ thể
- **Đề xuất khắc phục**: Cần bổ sung trích dẫn điều luật cho các đề xuất pháp lý.

## 5. Suggested Fix Order
1. Tập trung xử lý các lỗi **Blocker** liên quan đến việc phản hồi chậm hoặc lỗi kết nối.
2. Tối ưu hóa database MongoDB Atlas và Vector Search Index để các truy vấn tương đồng không trả về demo fallback.
3. Rà soát lại việc đồng bộ hóa dữ liệu cá nhân hóa (Feedback Loop) để NBA thay đổi nhạy bén hơn.

## 6. Affected Files (Các tệp tin cần rà soát)
- `src/api/recommendation_routes.py`
- `src/api/retrieval_routes.py`
- `src/mongodb/mongo_storage.py`
- `src/recommenders/next_best_action.py`
