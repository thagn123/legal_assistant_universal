# OpenAI Localhost QA Report — 2026-05-28

## Overall Result

- **MVP readiness**: PASS
- **Overall score**: 85.5/100
- **Browser mode**: api_fallback
- **Critical blockers**: 0
- **Major issues**: 0
- **Minor issues**: 0

## Score Table

| Category | Score / 10 | Notes |
| :--- | :---: | :--- |
| UX clarity | 8.1/10 | Đánh giá độ rõ ràng và tương tác giao diện |
| Legal relevance | 8.8/10 | Độ chính xác và phù hợp chuyên môn pháp lý |
| Evidence/Citation usefulness | 8.9/10 | Tính hữu ích và đầy đủ của căn cứ pháp luật Việt Nam |
| Recommendation quality | 8.5/10 | Chất lượng hành động đề xuất (Next Best Actions) |
| Personalization | 8.5/10 | Độ cá nhân hóa theo từng vai trò của người dùng |
| Context retention | 8.1/10 | Ghi nhớ ngữ cảnh trao đổi và lịch sử tương tác |
| Error resilience | 8.6/10 | Khả năng chịu lỗi và fallback khi gặp dữ liệu xấu |
| MVP completeness | 8.9/10 | Độ sẵn sàng để demo và khả năng mở rộng |

## Scenario Results

### Basic Vietnamese Legal Analysis

- **Scenario ID**: `basic_vi_family_analysis`
- **Status**: `PASS`
- **User Persona**: `demo_user_family`
- **User Input**: *"Tôi muốn ly hôn, có hai con, tôi muốn nuôi cả hai bé và muốn biết tài sản chung sẽ được chia như thế nào."*
- **Response Time**: `14.62s`
- **Scores**: `ux_clarity: 8, legal_relevance: 9, evidence_citation_usefulness: 8, recommendation_quality: 9, personalization: 7, context_retention: 8, error_resilience: 9, mvp_completeness: 9`
- **What Worked**:
  - Phân tích rõ ràng về quyền nuôi con và chia tài sản chung.
  - Cung cấp dẫn chứng pháp lý cụ thể từ Luật Hôn nhân và Gia đình.
  - Đề xuất các hành động tiếp theo rất thực tế và dễ thực hiện.
- **What Failed**:
  - Một số phần của phản hồi có thể được cá nhân hóa hơn nữa dựa trên thông tin người dùng.

- **AI Judgement**: *Phản hồi từ hệ thống rất đầy đủ và chính xác, cung cấp thông tin pháp lý cần thiết cho người dùng về ly hôn, quyền nuôi con và chia tài sản. Các dẫn chứng pháp lý được trích dẫn rõ ràng và phù hợp với tình huống. Đề xuất hành động tiếp theo rất thực tế và dễ thực hiện, tuy nhiên có thể cải thiện hơn nữa về tính cá nhân hóa.*

### Recommendation Click and Context Retention

- **Scenario ID**: `recommendation_click_and_retention`
- **Status**: `PASS`
- **User Persona**: `demo_user_family`
- **User Input**: *"Tranh chấp ly hôn và giành quyền nuôi con dưới 36 tháng tuổi."*
- **Response Time**: `2.47s`
- **Scores**: `ux_clarity: 8, legal_relevance: 9, evidence_citation_usefulness: 10, recommendation_quality: 8, personalization: 9, context_retention: 9, error_resilience: 10, mvp_completeness: 9`
- **What Worked**:
  - Phản hồi rõ ràng và dễ hiểu về các vụ án tương tự.
  - Các dẫn chứng pháp lý được trích dẫn chính xác và đầy đủ.
  - Đề xuất hành động phù hợp với ngữ cảnh của người dùng.
  - Hệ thống ghi nhớ tốt ngữ cảnh và các lựa chọn trước đó.
- **What Failed**:
  - Một số vụ việc cộng đồng không có thông tin chi tiết về giải pháp hoặc bước tiếp theo.

- **AI Judgement**: *Kịch bản này hoạt động tốt với độ chính xác cao về pháp lý và tính hữu ích của dẫn chứng. Gợi ý hành động có tính khả thi và phù hợp với ngữ cảnh của người dùng. Tuy nhiên, cần cải thiện thông tin cho các vụ việc cộng đồng để tăng tính hữu ích.*

### Same Query Different Persona (Family vs SME)

- **Scenario ID**: `same_query_different_persona`
- **Status**: `PASS`
- **User Persona**: `demo_user_sme`
- **User Input**: *"Tôi muốn ký hợp đồng thuê mặt bằng kinh doanh nhưng bên cho thuê yêu cầu đặt cọc trước 6 tháng tiền nhà."*
- **Response Time**: `2.14s`
- **Scores**: `ux_clarity: 8, legal_relevance: 9, evidence_citation_usefulness: 10, recommendation_quality: 9, personalization: 10, context_retention: 9, error_resilience: 8, mvp_completeness: 9`
- **What Worked**:
  - Phản hồi rõ ràng và dễ hiểu về các bước tiếp theo.
  - Các dẫn chứng pháp lý được cung cấp đầy đủ và chính xác.
  - Đề xuất hành động cụ thể và phù hợp với tình huống của người dùng.
  - Tính cá nhân hóa cao, phản ánh đúng vai trò của người dùng SME.
- **What Failed**:
  - Một số gợi ý hành động có thể được cải thiện về mức độ khẩn cấp.

- **AI Judgement**: *Kịch bản này hoạt động tốt với phản hồi rõ ràng, chính xác và cá nhân hóa cao. Hệ thống đã ghi nhớ ngữ cảnh và cung cấp các dẫn chứng pháp lý cụ thể, giúp người dùng có thể thực hiện các bước tiếp theo một cách hiệu quả.*

### Feedback Loop and NBA Adaptive Scoring

- **Scenario ID**: `feedback_loop_nba`
- **Status**: `PASS`
- **User Persona**: `demo_user_family`
- **User Input**: *"Tranh chấp về tài sản thừa kế đất đai giữa các anh chị em ruột."*
- **Response Time**: `2.10s`
- **Scores**: `ux_clarity: 8, legal_relevance: 9, evidence_citation_usefulness: 10, recommendation_quality: 9, personalization: 10, context_retention: 9, error_resilience: 8, mvp_completeness: 9`
- **What Worked**:
  - Các đề xuất hành động rõ ràng và dễ hiểu.
  - Phản hồi pháp lý chính xác và liên quan đến tình huống cụ thể.
  - Dẫn chứng pháp lý được cung cấp đầy đủ và chính xác.
  - Đề xuất hành động tiếp theo rất thực tế và khả thi.
  - Đề xuất được cá nhân hóa tốt cho người dùng dựa trên tình huống cụ thể.
  - Hệ thống ghi nhớ tốt ngữ cảnh và các lựa chọn trước đó của người dùng.
- **What Failed**:
  - Một số gợi ý hành động có thể được cải thiện về mức độ khẩn cấp hoặc ưu tiên.

- **AI Judgement**: *Kịch bản này thể hiện một trải nghiệm người dùng tốt với các phản hồi pháp lý chính xác và hữu ích. Hệ thống đã ghi nhớ ngữ cảnh và cá nhân hóa đề xuất một cách hiệu quả, mặc dù có thể cải thiện thêm về mức độ khẩn cấp của một số hành động gợi ý.*

### Community Similar Cases and PII Anonymization

- **Scenario ID**: `community_similar_cases`
- **Status**: `PASS`
- **User Persona**: `demo_user_employee`
- **User Input**: *"Anh Trần Văn Nam làm việc tại Công ty ABC bị sa thải trái luật vào ngày 15/05/2026, điện thoại liên hệ 0987654321, email nam.tran@gmail.com."*
- **Response Time**: `2.50s`
- **Scores**: `ux_clarity: 8, legal_relevance: 9, evidence_citation_usefulness: 8, recommendation_quality: 9, personalization: 8, context_retention: 7, error_resilience: 8, mvp_completeness: 9`
- **What Worked**:
  - Phản hồi rõ ràng và dễ hiểu về các vụ việc tương tự liên quan đến sa thải trái luật.
  - Các căn cứ pháp lý được dẫn chứng cụ thể và chính xác theo Bộ luật Lao động 2019.
  - Đề xuất các bước hành động tiếp theo rất thực tế và có thể thực hiện được.
- **What Failed**:
  - Hệ thống chưa hoàn toàn ghi nhớ ngữ cảnh của người dùng, có thể cải thiện hơn nữa.
  - Một số thông tin về các vụ việc tương tự không có dẫn chứng cụ thể.

- **AI Judgement**: *Kịch bản này hoạt động tốt với các phản hồi pháp lý chính xác và rõ ràng. Tuy nhiên, cần cải thiện khả năng ghi nhớ ngữ cảnh và đảm bảo tất cả thông tin đều có dẫn chứng cụ thể để tăng cường độ tin cậy và tính hữu ích cho người dùng.*

### Cross-Language Legal Query

- **Scenario ID**: `cross_language_query`
- **Status**: `PASS`
- **User Persona**: `demo_user_english`
- **User Input**: *"My employer terminated my labor contract without notice in Vietnam. What rights do I have?"*
- **Response Time**: `2.67s`
- **Scores**: `ux_clarity: 8, legal_relevance: 9, evidence_citation_usefulness: 9, recommendation_quality: 8, personalization: 9, context_retention: 8, error_resilience: 7, mvp_completeness: 9`
- **What Worked**:
  - Phản hồi rõ ràng và dễ hiểu về quyền lợi của người lao động trong trường hợp chấm dứt hợp đồng lao động đơn phương.
  - Cung cấp dẫn chứng pháp lý cụ thể từ Bộ luật Lao động 2019, giúp người dùng hiểu rõ hơn về quyền lợi của mình.
  - Đề xuất hành động tiếp theo cụ thể và thực tế cho người dùng.
- **What Failed**:
  - Một số thông tin có thể được trình bày rõ ràng hơn để tăng tính trực quan.
  - Hệ thống có thể cải thiện khả năng xử lý đầu vào rác hoặc không chính xác.

- **AI Judgement**: *Kịch bản này hoạt động tốt với phản hồi rõ ràng và chính xác về pháp lý. Hệ thống đã ghi nhớ ngữ cảnh và cá nhân hóa tốt cho người dùng. Tuy nhiên, cần cải thiện khả năng xử lý đầu vào không chính xác để nâng cao trải nghiệm người dùng.*

### Dashboard Behavior Digest Audit

- **Scenario ID**: `dashboard_behavior_audit`
- **Status**: `PASS`
- **User Persona**: `demo_user_family`
- **User Input**: *""*
- **Response Time**: `4.75s`
- **Scores**: `ux_clarity: 9, legal_relevance: 9, evidence_citation_usefulness: 8, recommendation_quality: 9, personalization: 9, context_retention: 10, error_resilience: 10, mvp_completeness: 9`
- **What Worked**:
  - Giao diện rõ ràng và dễ hiểu, người dùng có thể dễ dàng theo dõi thông tin cá nhân và các đề xuất.
  - Các phản hồi pháp lý liên quan đến lĩnh vực Dân sự rất chính xác và phù hợp với nhu cầu của người dùng.
  - Đề xuất hành động tiếp theo rất thực tế và phù hợp với lịch sử tương tác của người dùng.
  - Hệ thống ghi nhớ tốt ngữ cảnh và các lựa chọn trước đó của người dùng.
- **What Failed**:
  - Một số dẫn chứng pháp lý không có trích dẫn điều luật cụ thể, cần cải thiện để tăng tính chính xác.

- **AI Judgement**: *Kịch bản này hoạt động tốt với trải nghiệm người dùng mượt mà và các phản hồi pháp lý chính xác. Tuy nhiên, cần cải thiện việc cung cấp dẫn chứng pháp lý cụ thể để tăng cường độ tin cậy của thông tin.*

### Error and Fallback Experience

- **Scenario ID**: `error_and_fallback_experience`
- **Status**: `PASS`
- **User Persona**: `demo_user_family`
- **User Input**: *"abc"*
- **Response Time**: `2.12s`
- **Scores**: `ux_clarity: 8, legal_relevance: 7, evidence_citation_usefulness: 8, recommendation_quality: 7, personalization: 6, context_retention: 5, error_resilience: 9, mvp_completeness: 8`
- **What Worked**:
  - Phản hồi thân thiện và dễ hiểu cho người dùng.
  - Cung cấp thông tin pháp lý liên quan đến các lĩnh vực khác nhau.
  - Cảnh báo rõ ràng về đầu vào không hợp lệ.
- **What Failed**:
  - Thiếu tính cá nhân hóa trong các gợi ý hành động.
  - Không ghi nhớ ngữ cảnh từ các tương tác trước đó.

- **AI Judgement**: *Kịch bản này thể hiện khả năng xử lý lỗi tốt với phản hồi thân thiện và thông tin pháp lý hữu ích. Tuy nhiên, cần cải thiện tính cá nhân hóa và khả năng ghi nhớ ngữ cảnh để nâng cao trải nghiệm người dùng.*

## Issues
*Không phát hiện lỗi nghiêm trọng nào. MVP hoạt động tuyệt vời!*

## MVP Gaps
1. Số lượng case nghiên cứu thực tế (official cases) trong DB vẫn còn thô sơ, cần nạp thêm dữ liệu thông qua ingestion pipeline.
2. Tích hợp Playwright để kiểm thử giao diện thực tế (UI rendering, click flow, charts) trực tiếp trên Chrome/Firefox.
3. Hoàn thiện đồ thị quan hệ luật GraphRAG đầy đủ hơn ở tầng backend.
