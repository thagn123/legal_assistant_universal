# OpenAI Localhost QA Report — 2026-05-28

## Overall Result

- **MVP readiness**: FAIL
- **Overall score**: 60.6/100
- **Browser mode**: api_fallback
- **Critical blockers**: 1
- **Major issues**: 8
- **Minor issues**: 3

## Score Table

| Category | Score / 10 | Notes |
| :--- | :---: | :--- |
| UX clarity | 7.1/10 | Đánh giá độ rõ ràng và tương tác giao diện |
| Legal relevance | 6.5/10 | Độ chính xác và phù hợp chuyên môn pháp lý |
| Evidence/Citation usefulness | 4.0/10 | Tính hữu ích và đầy đủ của căn cứ pháp luật Việt Nam |
| Recommendation quality | 6.2/10 | Chất lượng hành động đề xuất (Next Best Actions) |
| Personalization | 5.2/10 | Độ cá nhân hóa theo từng vai trò của người dùng |
| Context retention | 6.2/10 | Ghi nhớ ngữ cảnh trao đổi và lịch sử tương tác |
| Error resilience | 7.1/10 | Khả năng chịu lỗi và fallback khi gặp dữ liệu xấu |
| MVP completeness | 6.2/10 | Độ sẵn sàng để demo và khả năng mở rộng |

## Scenario Results

### Basic Vietnamese Legal Analysis

- **Scenario ID**: `basic_vi_family_analysis`
- **Status**: `PARTIAL`
- **User Persona**: `demo_user_family`
- **User Input**: *"Tôi muốn ly hôn, có hai con, tôi muốn nuôi cả hai bé và muốn biết tài sản chung sẽ được chia như thế nào."*
- **Response Time**: `16.48s`
- **Scores**: `ux_clarity: 8, legal_relevance: 7, evidence_citation_usefulness: 6, recommendation_quality: 8, personalization: 7, context_retention: 8, error_resilience: 9, mvp_completeness: 7`
- **What Worked**:
  - Phản hồi rõ ràng và dễ hiểu về quy trình ly hôn và quyền nuôi con.
  - Các dẫn chứng pháp lý được cung cấp có liên quan đến tình huống.
  - Đề xuất hành động tiếp theo rất thực tế và có thể thực hiện ngay.
- **What Failed**:
  - Không cung cấp đầy đủ thông tin về việc chia tài sản chung, đặc biệt là không đề cập đến nguyên tắc chia đôi.
  - Một số dẫn chứng pháp lý không được trích dẫn đầy đủ hoặc không rõ ràng.

- **AI Judgement**: *Phản hồi từ hệ thống khá tốt, nhưng cần cải thiện về độ chính xác và đầy đủ của thông tin pháp lý liên quan đến chia tài sản chung. Hệ thống đã cung cấp các bước hành động cụ thể và hữu ích cho người dùng, nhưng cần chú ý hơn đến việc đảm bảo tất cả các khía cạnh pháp lý được đề cập đầy đủ.*

### Recommendation Click and Context Retention

- **Scenario ID**: `recommendation_click_and_retention`
- **Status**: `PARTIAL`
- **User Persona**: `demo_user_family`
- **User Input**: *"Tranh chấp ly hôn và giành quyền nuôi con dưới 36 tháng tuổi."*
- **Response Time**: `2.25s`
- **Scores**: `ux_clarity: 7, legal_relevance: 5, evidence_citation_usefulness: 0, recommendation_quality: 4, personalization: 3, context_retention: 6, error_resilience: 8, mvp_completeness: 5`
- **What Worked**:
  - Hệ thống đã cung cấp thông tin về các vụ việc tương tự trong lĩnh vực Dân sự.
  - Giao diện hiển thị rõ ràng và dễ hiểu cho người dùng.
- **What Failed**:
  - Không có căn cứ pháp lý cụ thể nào được dẫn ra trong các vụ việc tương tự.
  - Các yêu cầu khẳng định về 'con dưới 36 tháng' và 'nghĩa vụ cấp dưỡng' không được đáp ứng.

- **AI Judgement**: *Hệ thống đã hoạt động tốt trong việc cung cấp thông tin về các vụ việc tương tự, nhưng thiếu sót nghiêm trọng về căn cứ pháp lý và không đáp ứng được các yêu cầu khẳng định của người dùng. Cần cải thiện khả năng cá nhân hóa và chất lượng gợi ý hành động.*

### Same Query Different Persona (Family vs SME)

- **Scenario ID**: `same_query_different_persona`
- **Status**: `PASS`
- **User Persona**: `demo_user_sme`
- **User Input**: *"Tôi muốn ký hợp đồng thuê mặt bằng kinh doanh nhưng bên cho thuê yêu cầu đặt cọc trước 6 tháng tiền nhà."*
- **Response Time**: `2.12s`
- **Scores**: `ux_clarity: 8, legal_relevance: 9, evidence_citation_usefulness: 7, recommendation_quality: 8, personalization: 6, context_retention: 8, error_resilience: 9, mvp_completeness: 8`
- **What Worked**:
  - Phản hồi rõ ràng và dễ hiểu về các bước cần thực hiện.
  - Các hành động gợi ý phù hợp với tình huống và mục tiêu của người dùng.
  - Hệ thống ghi nhớ tốt ngữ cảnh và các yêu cầu trước đó.
- **What Failed**:
  - Cần có nhiều dẫn chứng pháp lý cụ thể hơn để tăng tính thuyết phục.
  - Một số gợi ý hành động chưa hoàn toàn cá nhân hóa theo vai trò SME.

- **AI Judgement**: *Kịch bản này hoạt động tốt với các phản hồi rõ ràng và phù hợp với yêu cầu của người dùng. Tuy nhiên, cần cải thiện tính cá nhân hóa và cung cấp thêm dẫn chứng pháp lý cụ thể để nâng cao chất lượng phản hồi.*

### Feedback Loop and NBA Adaptive Scoring

- **Scenario ID**: `feedback_loop_nba`
- **Status**: `PARTIAL`
- **User Persona**: `demo_user_family`
- **User Input**: *"Tranh chấp về tài sản thừa kế đất đai giữa các anh chị em ruột."*
- **Response Time**: `2.08s`
- **Scores**: `ux_clarity: 7, legal_relevance: 8, evidence_citation_usefulness: 6, recommendation_quality: 7, personalization: 8, context_retention: 7, error_resilience: 5, mvp_completeness: 6`
- **What Worked**:
  - Các hành động gợi ý được cá nhân hóa theo tình huống tranh chấp đất đai.
  - Đưa ra các bước cụ thể để người dùng thực hiện tiếp theo.
  - Các dẫn chứng pháp lý được cung cấp rõ ràng và liên quan đến tình huống.
- **What Failed**:
  - Một số hành động gợi ý không có dẫn chứng điều luật cụ thể.
  - Không hoàn toàn đáp ứng yêu cầu 'next-best-action' do một số hành động không rõ ràng hoặc không thực tế.

- **AI Judgement**: *Kịch bản này có nhiều điểm mạnh trong việc cá nhân hóa và cung cấp hành động tiếp theo, nhưng cần cải thiện về dẫn chứng pháp lý và thông điệp lỗi để nâng cao trải nghiệm người dùng.*

### Community Similar Cases and PII Anonymization

- **Scenario ID**: `community_similar_cases`
- **Status**: `PASS`
- **User Persona**: `demo_user_employee`
- **User Input**: *"Anh Trần Văn Nam làm việc tại Công ty ABC bị sa thải trái luật vào ngày 15/05/2026, điện thoại liên hệ 0987654321, email nam.tran@gmail.com."*
- **Response Time**: `2.24s`
- **Scores**: `ux_clarity: 8, legal_relevance: 9, evidence_citation_usefulness: 2, recommendation_quality: 8, personalization: 7, context_retention: 8, error_resilience: 9, mvp_completeness: 8`
- **What Worked**:
  - Hệ thống cung cấp thông tin về các vụ việc tương tự liên quan đến sa thải trái luật, rất hữu ích cho người dùng.
  - Các gợi ý hành động tiếp theo rõ ràng và có thể thực hiện được.
- **What Failed**:
  - Không có dẫn chứng điều luật cụ thể nào được cung cấp, điều này làm giảm tính chính xác và độ tin cậy của thông tin pháp lý.

- **AI Judgement**: *Kịch bản này hoạt động tốt trong việc cung cấp thông tin về các vụ việc tương tự và gợi ý hành động, nhưng cần cải thiện tính chính xác pháp lý bằng cách cung cấp dẫn chứng điều luật cụ thể.*

### Cross-Language Legal Query

- **Scenario ID**: `cross_language_query`
- **Status**: `FAIL`
- **User Persona**: `demo_user_english`
- **User Input**: *"My employer terminated my labor contract without notice in Vietnam. What rights do I have?"*
- **Response Time**: `2.17s`
- **Scores**: `ux_clarity: 5, legal_relevance: 2, evidence_citation_usefulness: 1, recommendation_quality: 2, personalization: 1, context_retention: 3, error_resilience: 4, mvp_completeness: 3`
- **What Worked**:
  - Hệ thống có thể tìm thấy các vụ việc tương tự trong lĩnh vực Tổng hợp.
  - Thời gian phản hồi nhanh.
- **What Failed**:
  - Phản hồi không cung cấp thông tin pháp lý chính xác liên quan đến quyền lợi của người lao động.
  - Không có dẫn chứng cụ thể từ luật pháp Việt Nam.
  - Các yêu cầu khẳng định không được đáp ứng.

- **AI Judgement**: *Kịch bản này không đạt yêu cầu do thiếu thông tin pháp lý chính xác và không đáp ứng các yêu cầu khẳng định. Cần cải thiện khả năng cung cấp thông tin pháp lý và gợi ý hành động cho người dùng.*

### Dashboard Behavior Digest Audit

- **Scenario ID**: `dashboard_behavior_audit`
- **Status**: `PARTIAL`
- **User Persona**: `demo_user_family`
- **User Input**: *""*
- **Response Time**: `4.03s`
- **Scores**: `ux_clarity: 8, legal_relevance: 7, evidence_citation_usefulness: 6, recommendation_quality: 8, personalization: 7, context_retention: 5, error_resilience: 6, mvp_completeness: 7`
- **What Worked**:
  - Giao diện dashboard rõ ràng và dễ hiểu.
  - Các đề xuất liên quan đến lĩnh vực pháp lý mà người dùng quan tâm được đưa ra hợp lý.
  - Thông tin về hoạt động của người dùng trong 7 ngày qua được trình bày rõ ràng.
- **What Failed**:
  - Không có thông tin digest, điều này ảnh hưởng đến trải nghiệm tổng thể.
  - Một số dẫn chứng pháp lý không có trích dẫn cụ thể từ luật, làm giảm tính chính xác.

- **AI Judgement**: *Kịch bản dashboard hoạt động tốt về mặt giao diện và đề xuất, nhưng thiếu thông tin digest và một số dẫn chứng pháp lý chưa đủ chính xác. Cần cải thiện để nâng cao trải nghiệm người dùng.*

### Error and Fallback Experience

- **Scenario ID**: `error_and_fallback_experience`
- **Status**: `FAIL`
- **User Persona**: `demo_user_family`
- **User Input**: *"abc"*
- **Response Time**: `14.20s`
- **Scores**: `ux_clarity: 6, legal_relevance: 5, evidence_citation_usefulness: 4, recommendation_quality: 5, personalization: 3, context_retention: 5, error_resilience: 7, mvp_completeness: 6`
- **What Worked**:
  - Hệ thống đã cung cấp các hành động tiếp theo rõ ràng và có tính khả thi.
  - Có sự ghi nhớ ngữ cảnh từ đầu vào của người dùng.
- **What Failed**:
  - Phản hồi không thân thiện như yêu cầu, thiếu tính cá nhân hóa.
  - Căn cứ pháp lý chưa đủ mạnh và không có dẫn chứng cụ thể cho từng điều luật.
  - Câu trả lời không hoàn toàn rõ ràng về tình huống pháp lý cụ thể.

- **AI Judgement**: *Kịch bản này cho thấy hệ thống có khả năng cung cấp phản hồi pháp lý nhưng cần cải thiện về tính thân thiện và cá nhân hóa. Cần bổ sung dẫn chứng pháp lý cụ thể để tăng tính chính xác và độ tin cậy của thông tin.*

## Issues

### 1. [MAJOR] Thiếu thông tin về chia tài sản

- **Module**: `EvidenceCitation`
- **Step**: `Phân tích tình huống`
- **Expected**: Cung cấp thông tin rõ ràng về nguyên tắc chia tài sản chung.
- **Actual**: Không đề cập đến nguyên tắc chia đôi tài sản.
- **Suggested Fix**: *Cần bổ sung thông tin về nguyên tắc chia tài sản chung theo luật pháp.*

### 2. [MAJOR] Thiếu căn cứ pháp lý cụ thể

- **Module**: `SimilarCases`
- **Step**: `Người dùng yêu cầu thông tin về tranh chấp ly hôn và quyền nuôi con.`
- **Expected**: Cung cấp thông tin pháp lý cụ thể liên quan đến quyền nuôi con và nghĩa vụ cấp dưỡng.
- **Actual**: Không có dẫn chứng pháp lý nào được cung cấp.
- **Suggested Fix**: *Cần bổ sung các điều luật cụ thể liên quan đến quyền nuôi con và nghĩa vụ cấp dưỡng trong phản hồi.*

### 3. [MINOR] Gợi ý hành động không phù hợp

- **Module**: `RecommendationQuality`
- **Step**: `Người dùng tìm kiếm thông tin về tranh chấp ly hôn.`
- **Expected**: Gợi ý hành động liên quan đến việc giải quyết tranh chấp ly hôn và quyền nuôi con.
- **Actual**: Gợi ý hành động không liên quan đến ngữ cảnh cụ thể của người dùng.
- **Suggested Fix**: *Cần cải thiện khả năng gợi ý hành động dựa trên ngữ cảnh cụ thể của người dùng.*

### 4. [MAJOR] Thiếu dẫn chứng pháp lý cho một số hành động

- **Module**: `NextBestAction`
- **Step**: `Khi người dùng yêu cầu hành động tiếp theo`
- **Expected**: Mỗi hành động gợi ý đều có dẫn chứng pháp lý cụ thể.
- **Actual**: Một số hành động không có dẫn chứng pháp lý rõ ràng.
- **Suggested Fix**: *Cần đảm bảo rằng tất cả các hành động gợi ý đều có dẫn chứng pháp lý cụ thể.*

### 5. [MINOR] Thông điệp lỗi không thân thiện

- **Module**: `error_resilience`
- **Step**: `Khi gặp đầu vào không hợp lệ`
- **Expected**: Thông điệp lỗi thân thiện và hướng dẫn người dùng.
- **Actual**: Thông điệp lỗi không rõ ràng hoặc không thân thiện.
- **Suggested Fix**: *Cần cải thiện thông điệp lỗi để hướng dẫn người dùng tốt hơn.*

### 6. [MAJOR] Thiếu dẫn chứng pháp lý cụ thể

- **Module**: `EvidenceCitation`
- **Step**: `Khi cung cấp thông tin về các vụ việc tương tự`
- **Expected**: Có dẫn chứng điều luật cụ thể liên quan đến sa thải trái luật.
- **Actual**: Không có dẫn chứng nào được cung cấp.
- **Suggested Fix**: *Cần bổ sung các điều luật cụ thể liên quan đến sa thải trái luật trong phần thông tin vụ việc.*

### 7. [BLOCKER] Thiếu thông tin pháp lý chính xác

- **Module**: `LegalAnalysis`
- **Step**: `Người dùng hỏi về quyền lợi sau khi bị chấm dứt hợp đồng lao động.`
- **Expected**: Cung cấp thông tin về quyền lợi của người lao động theo luật lao động Việt Nam.
- **Actual**: Không có thông tin pháp lý cụ thể và không đáp ứng các yêu cầu khẳng định.
- **Suggested Fix**: *Cần cập nhật cơ sở dữ liệu pháp lý và đảm bảo cung cấp thông tin chính xác cho các yêu cầu khẳng định.*

### 8. [MAJOR] Gợi ý hành động không liên quan

- **Module**: `NextBestAction`
- **Step**: `Hệ thống gợi ý các vụ việc tương tự.`
- **Expected**: Gợi ý các hành động cụ thể cho người lao động trong tình huống bị chấm dứt hợp đồng.
- **Actual**: Chỉ cung cấp các vụ việc tương tự mà không có hành động cụ thể.
- **Suggested Fix**: *Cần phát triển các gợi ý hành động cụ thể dựa trên tình huống của người dùng.*

### 9. [MAJOR] Thiếu thông tin digest

- **Module**: `Digest`
- **Step**: `Khi người dùng yêu cầu thông tin digest`
- **Expected**: Thông tin digest đầy đủ và chính xác về các hoạt động pháp lý.
- **Actual**: Thông tin digest không được cung cấp.
- **Suggested Fix**: *Cần đảm bảo rằng thông tin digest được tạo ra và hiển thị cho người dùng.*

### 10. [MINOR] Thiếu trích dẫn điều luật cụ thể

- **Module**: `Evidence/Citation`
- **Step**: `Khi hiển thị các đề xuất pháp lý`
- **Expected**: Các đề xuất có trích dẫn điều luật cụ thể.
- **Actual**: Một số đề xuất không có trích dẫn điều luật.
- **Suggested Fix**: *Cần bổ sung trích dẫn điều luật cho các đề xuất pháp lý.*

### 11. [MAJOR] Thiếu tính thân thiện trong phản hồi

- **Module**: `Legal Relevance`
- **Step**: `Phản hồi từ hệ thống`
- **Expected**: Phản hồi thân thiện và dễ hiểu cho người dùng.
- **Actual**: Phản hồi có phần khô khan và thiếu sự cá nhân hóa.
- **Suggested Fix**: *Cải thiện ngôn ngữ phản hồi để trở nên thân thiện hơn với người dùng.*

### 12. [MAJOR] Căn cứ pháp lý không đủ mạnh

- **Module**: `Evidence/Citation Usefulness`
- **Step**: `Cung cấp căn cứ pháp lý`
- **Expected**: Cung cấp dẫn chứng cụ thể cho từng điều luật liên quan.
- **Actual**: Một số điều luật được đề cập nhưng không có dẫn chứng cụ thể.
- **Suggested Fix**: *Bổ sung dẫn chứng cụ thể cho từng điều luật trong phản hồi.*

## MVP Gaps
1. Số lượng case nghiên cứu thực tế (official cases) trong DB vẫn còn thô sơ, cần nạp thêm dữ liệu thông qua ingestion pipeline.
2. Tích hợp Playwright để kiểm thử giao diện thực tế (UI rendering, click flow, charts) trực tiếp trên Chrome/Firefox.
3. Hoàn thiện đồ thị quan hệ luật GraphRAG đầy đủ hơn ở tầng backend.
