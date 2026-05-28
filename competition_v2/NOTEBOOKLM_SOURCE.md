# LexAI — Hệ Thống Gợi Ý Kiến Thức Pháp Lý Thông Minh
## Tài liệu nguồn cho NotebookLM · MongoDB Recommendation Engine Competition 2026

---

## Phần 1: Vấn Đề Chúng Tôi Giải Quyết

Việt Nam có 97 triệu dân. Mỗi năm, hàng triệu người trong số đó phải đối mặt với vấn đề pháp lý — tranh chấp đất đai, bị sa thải trái luật, hợp đồng có điều khoản bất lợi, hoặc không biết mình đang vi phạm quy định nào. Nhưng đại đa số trong số họ không biết bắt đầu từ đâu.

Vấn đề không phải là thiếu luật. Việt Nam có hàng nghìn văn bản pháp luật, từ Bộ luật Dân sự đến hàng trăm Nghị định, Thông tư được ban hành mỗi năm. Vấn đề là người dân không biết điều luật nào áp dụng cho tình huống của mình. Phí tư vấn luật sư dao động từ 500.000 đến 2.000.000 đồng mỗi giờ — một con số nằm ngoài tầm với của phần lớn người lao động và hộ gia đình.

Hơn nữa, pháp luật thay đổi liên tục. Một điều luật ban hành năm 2019 có thể đã bị sửa đổi năm 2023. Ngay cả những người có kiến thức pháp lý cũng khó theo dõi kịp tất cả thay đổi này.

Đây chính là bài toán mà LexAI ra đời để giải quyết.

---

## Phần 2: LexAI Là Gì

LexAI — viết tắt của Legal AI — là một hệ thống gợi ý kiến thức pháp lý thông minh, được xây dựng hoàn toàn trên nền tảng MongoDB Atlas. Thay vì yêu cầu người dùng phải biết tên điều luật hay số văn bản cụ thể, LexAI cho phép người dùng đặt câu hỏi bằng ngôn ngữ tự nhiên — đúng như cách họ sẽ hỏi một người bạn am hiểu pháp luật.

Khi một người dùng gõ vào "Công ty tôi tự dưng cho tôi nghỉ việc không có lý do, tôi phải làm gì?", LexAI không chỉ tìm kiếm các từ khóa như "nghỉ việc" hay "sa thải". Hệ thống hiểu ngữ cảnh, phân loại đây là vấn đề thuộc lĩnh vực lao động, sau đó gợi ý những điều luật, biểu mẫu và rủi ro pháp lý liên quan nhất — được cá nhân hóa theo lịch sử tương tác và hồ sơ của người dùng.

LexAI không phải là một chatbot đơn giản. Đây là một Recommendation Engine đa tầng với khả năng học hỏi liên tục từ hành vi của cộng đồng người dùng.

---

## Phần 3: Kiến Trúc Kỹ Thuật — Bảy Tầng Xử Lý

LexAI vận hành thông qua một pipeline thông minh gồm bảy giai đoạn, mỗi giai đoạn được thiết kế để tối ưu hóa độ chính xác và tốc độ.

**Giai đoạn một là Query Planner.** Đây là bộ não phân tích đầu vào. Trong vòng dưới 10 mili-giây — không sử dụng bất kỳ mô hình AI nào — hệ thống phân loại câu hỏi thuộc lĩnh vực pháp lý nào trong số tám lĩnh vực được hỗ trợ: đất đai, hợp đồng, lao động, doanh nghiệp, dân sự, hình sự, hành chính và gia đình. Đồng thời, hệ thống trích xuất các thực thể quan trọng như tên bên liên quan, số điều luật được đề cập, và chiến lược truy vấn phù hợp nhất.

**Giai đoạn hai là Session Memory.** Mỗi cuộc trò chuyện được lưu vào MongoDB với chỉ mục TTL tự động xóa sau 24 giờ. Điều này cho phép hệ thống nhớ ngữ cảnh của toàn bộ cuộc hội thoại mà không cần người dùng lặp lại thông tin.

**Giai đoạn ba là Retrieval Fusion — trái tim của toàn bộ hệ thống.** Đây là nơi bốn nguồn tín hiệu khác nhau được kết hợp lại. Tín hiệu đầu tiên và quan trọng nhất là MongoDB Vector Search, chiếm trọng số 45%. Hệ thống sử dụng mô hình embedding đa ngôn ngữ tạo ra vector 384 chiều cho mỗi đoạn văn bản, sau đó dùng độ tương đồng cosine để tìm các đoạn pháp lý có nghĩa gần nhất với câu hỏi của người dùng — dù được viết bằng tiếng Việt hay tiếng Anh. Tín hiệu thứ hai là BM25 keyword scoring với trọng số 20%, giúp đảm bảo các từ khóa đặc thù pháp lý không bị bỏ sót. Tín hiệu thứ ba là Graph traversal với trọng số 25%, tìm kiếm các điều luật liên quan thông qua đồ thị pháp lý. Tín hiệu thứ tư là Behavior boost với trọng số 10%, ưu tiên những loại văn bản mà người dùng đã từng tương tác tích cực trong quá khứ.

**Giai đoạn bốn là GraphRAG.** Từ các điều luật được tìm thấy ở giai đoạn ba, hệ thống duyệt tiếp qua đồ thị pháp lý bằng thuật toán tìm kiếm theo chiều rộng. Đồ thị này mã hóa các mối quan hệ giữa các văn bản: điều luật này sửa đổi điều luật kia, điều luật này mâu thuẫn với điều luật kia, hay điều luật này yêu cầu áp dụng đồng thời với điều luật khác. Việc duyệt đồ thị giúp đảm bảo người dùng không chỉ nhận được điều luật chính xác mà còn nhận được toàn bộ bức tranh pháp lý liên quan.

**Giai đoạn năm là LLM Reasoning.** Hệ thống sử dụng OpenAI với cơ chế tool-calling, tổng hợp các bằng chứng pháp lý từ các giai đoạn trước thành một câu trả lời mạch lạc, có trích dẫn nguồn. Quan trọng là, nếu không có kết nối OpenAI, hệ thống vẫn hoạt động hoàn toàn thông qua cơ chế fallback deterministic — đảm bảo tính sẵn sàng 24/7.

**Giai đoạn sáu là Reranking với sáu tín hiệu cá nhân hóa.** Sau khi có danh sách kết quả, hệ thống sắp xếp lại dựa trên: độ tương đồng ngữ nghĩa (35%), hành vi của người dùng (15%), độ liên quan trong đồ thị pháp lý (20%), độ mới của văn bản (15%), mức độ phổ biến trong cộng đồng (10%), và tỷ lệ phản hồi tích cực (5%). Kết quả là hai người dùng khác nhau hỏi cùng một câu hỏi sẽ nhận được kết quả được sắp xếp theo thứ tự phù hợp với từng người.

**Giai đoạn bảy là Persist và Learning.** Mỗi tương tác được lưu lại. Một ReflectionAgent chạy ngầm trong luồng riêng, học từ cuộc trò chuyện để cập nhật hồ sơ người dùng mà không làm chậm thời gian phản hồi. Sau vài lần tương tác, hệ thống nhớ rằng người dùng này quan tâm đến lĩnh vực lao động, đang trong tình huống tranh chấp với công ty, và ưa thích giải thích chi tiết hơn tóm tắt ngắn.

---

## Phần 4: MongoDB Vector Search — Cách Hệ Thống Hiểu Ngữ Nghĩa

Khả năng hiểu ngữ nghĩa của LexAI đến từ MongoDB Vector Search kết hợp với mô hình embedding đa ngôn ngữ. Mỗi đoạn văn bản pháp lý trong hệ thống được chuyển đổi thành một vector số học với 384 chiều. Vector này đại diện cho ý nghĩa của đoạn văn trong không gian toán học, nơi các đoạn văn có nghĩa tương đồng sẽ nằm gần nhau dù được viết bằng ngôn ngữ khác nhau.

Điều đặc biệt ở đây là mô hình embedding mà LexAI sử dụng là mô hình đa ngôn ngữ — có nghĩa là cùng một không gian vector chứa đồng thời tiếng Việt và tiếng Anh. Khi người dùng hỏi "Article 36 labor code termination rights" bằng tiếng Anh, MongoDB Vector Search vẫn tìm được Điều 36 Bộ luật Lao động viết bằng tiếng Việt, vì hai đoạn văn này có vector gần nhau trong không gian toán học.

MongoDB Atlas cung cấp chỉ mục vector với độ tương đồng cosine trên collection chứa hàng chục nghìn đoạn pháp lý. Mỗi truy vấn tìm kiếm trong số 150 ứng viên tiềm năng, sau đó trả về 20 kết quả tốt nhất trong vài mili-giây. Bộ lọc kết hợp đảm bảo mỗi người dùng chỉ thấy tài liệu của chính họ và tài liệu toàn hệ thống mà admin đã tải lên — hai loại này được phân biệt bằng trường is_global trong MongoDB.

---

## Phần 5: Aggregation Pipeline — Collaborative Filtering Thuần MongoDB

Collaborative filtering là kỹ thuật gợi ý dựa trên nguyên tắc: những người có hành vi tương tự trong quá khứ thường cần những thứ tương tự trong tương lai. LexAI thực hiện toàn bộ collaborative filtering bên trong MongoDB thông qua Aggregation Pipeline — không cần framework học máy bên ngoài, không cần Python matrix operations.

Pipeline hoạt động qua năm bước. Bước đầu tiên lấy danh sách tài liệu mà người dùng hiện tại đã tương tác trong 30 ngày gần nhất, ưu tiên các tương tác mạnh như lưu và tải xuống. Bước thứ hai tìm kiếm những người dùng khác đã tương tác với cùng tài liệu — đây là các "peer" tiềm năng. Bước thứ ba tính điểm similarity giữa người dùng hiện tại và từng peer dựa trên số tài liệu chung. Bước thứ tư lấy những tài liệu mà các peer hàng đầu đã xem nhưng người dùng hiện tại chưa thấy. Bước thứ năm tổng hợp điểm collaborative và trả về top 10 gợi ý.

Toàn bộ quá trình này xảy ra trong cơ sở dữ liệu, tận dụng tối đa khả năng của MongoDB để xử lý join và aggregation phức tạp mà không cần chuyển dữ liệu ra ngoài.

Ngoài collaborative filtering, Aggregation Pipeline còn được dùng để tính behavior profile của từng người dùng — lĩnh vực pháp lý nào họ quan tâm nhất, loại tài liệu nào họ ưa thích, và xu hướng thay đổi theo thời gian. Điểm hành vi được tính với hệ số decay theo thời gian: tương tác gần đây có trọng số cao hơn tương tác cũ, với half-life khoảng 8.7 ngày.

---

## Phần 6: Truy Xuất Đa Ngôn Ngữ — Hỏi Tiếng Anh, Tìm Tiếng Việt

Pháp lý Việt Nam có đặc thù là nhiều văn bản pha trộn tiếng Anh và tiếng Việt — đặc biệt trong lĩnh vực hợp đồng thương mại quốc tế, sở hữu trí tuệ, và trọng tài. LexAI giải quyết thách thức đa ngôn ngữ này theo ba tầng.

Tầng đầu tiên là nhận dạng ngôn ngữ tự động. Hệ thống phân tích mật độ ký tự diacritical đặc trưng của tiếng Việt, kết hợp với từ điển thuật ngữ pháp lý song ngữ, để xác định ngôn ngữ chính của câu hỏi và văn bản.

Tầng thứ hai là hệ thống canonical ID đa ngôn ngữ. "Điều 1", "Article 1", "Art. 1", và "ARTICLE I" tất cả đều được ánh xạ về cùng một định danh ổn định là "article_1". Hệ thống hỗ trợ cả số La Mã và số Ả Rập. Các định danh này được gắn vào mỗi đoạn văn bản khi nhập vào hệ thống, cho phép tìm kiếm theo tham chiếu chính xác.

Tầng thứ ba là các cạnh ALIAS_OF trong đồ thị tri thức. Khi một node tiếng Anh và một node tiếng Việt đề cập đến cùng một điều luật, hệ thống tự động tạo liên kết hai chiều giữa chúng. Điều này đảm bảo rằng bất kể người dùng hỏi bằng ngôn ngữ nào, quá trình duyệt đồ thị luôn tìm được tất cả thông tin liên quan.

Kết quả đo lường trên bộ dữ liệu thử nghiệm: tỷ lệ hit cross-language đạt 100%, với trung bình 20 cạnh ALIAS_OF và 28 đến 31 canonical reference được tạo tự động cho mỗi tài liệu.

---

## Phần 7: Bộ Nhớ Người Dùng — Cá Nhân Hóa Thực Sự

Điểm khác biệt lớn nhất của LexAI so với các hệ thống tìm kiếm pháp lý thông thường là bộ nhớ vĩnh viễn cross-session. Hầu hết chatbot quên toàn bộ ngữ cảnh khi kết thúc phiên trò chuyện. LexAI nhớ.

Mỗi người dùng có một hồ sơ riêng trong MongoDB, không có ngày hết hạn, lưu trữ thông tin cá nhân như tên, nghề nghiệp, địa điểm và các ghi chú về tình huống pháp lý của họ. Hệ thống cũng lưu lịch sử tối đa 20 tình huống pháp lý gần nhất, mỗi tình huống được tóm tắt trong một câu ngắn kèm theo lĩnh vực pháp lý và trạng thái đã giải quyết hay chưa.

Khi người dùng quay lại sau vài ngày, hệ thống tự động bổ sung ngữ cảnh từ bộ nhớ vào câu hỏi trước khi gửi đến mô hình AI. Người dùng không cần giải thích lại hoàn cảnh từ đầu — LexAI đã biết họ là ai và đang đối mặt với vấn đề gì.

Thông tin trong bộ nhớ được cập nhật tự động thông qua ReflectionAgent. Sau mỗi cuộc trò chuyện, agent này chạy trong nền, trích xuất thông tin mới từ cuộc hội thoại và cập nhật hồ sơ người dùng. Quá trình này được bảo vệ bởi nhiều lớp kiểm duyệt để ngăn chặn việc tiêm mã độc hoặc thay đổi hành vi của hệ thống thông qua đầu vào của người dùng.

---

## Phần 8: Hệ Thống Quản Lý Tài Liệu — Admin Upload và Global Documents

Khi Quốc hội ban hành luật mới, hay Chính phủ ban hành Nghị định mới, hệ thống cần cập nhật nhanh chóng. LexAI giải quyết điều này thông qua cơ chế Admin Upload và Global Documents.

Quản trị viên có thể tải lên bất kỳ file nào dưới dạng DOC, PDF, hay HTML. Hệ thống tự động xử lý qua pipeline tám giai đoạn: phân tích cấu trúc, trích xuất văn bản, chuẩn hóa, phân đoạn thành các đoạn nhỏ phù hợp để nhúng, xây dựng đồ thị quan hệ, tạo vector embedding, và cuối cùng lưu vào MongoDB với nhãn is_global bằng true.

Điểm quan trọng là tài liệu toàn hệ thống chỉ cần lưu một lần nhưng tất cả người dùng đều có thể truy cập. Không có sao chép dữ liệu, không có chi phí lưu trữ nhân bội. Mỗi truy vấn Vector Search tự động kết hợp tài liệu của người dùng và tài liệu toàn hệ thống thông qua bộ lọc MongoDB.

---

## Phần 9: Kiến Trúc Dữ Liệu MongoDB

LexAI sử dụng sáu collection trong MongoDB Atlas, mỗi collection được thiết kế có mục đích riêng biệt.

Collection law_chunks là trung tâm của toàn bộ hệ thống. Mỗi document trong collection này đại diện cho một đoạn văn bản pháp lý, bao gồm nội dung văn bản, vector embedding 384 chiều, thông tin định danh đa ngôn ngữ, và metadata về chất lượng trích xuất. Đây là collection được đánh chỉ mục vector để phục vụ Vector Search.

Collection interactions ghi lại mọi hành vi của người dùng: xem, lưu, tải xuống, mở rộng. Mỗi sự kiện được gắn với hệ số trọng số suy giảm theo thời gian, phản ánh thực tế rằng tương tác gần đây có giá trị hơn tương tác cũ. Đây là nguồn dữ liệu đầu vào chính cho collaborative filtering.

Collection user_memory lưu hồ sơ người dùng vĩnh viễn. Không có TTL index, không có ngày hết hạn. Đây là bộ nhớ dài hạn của hệ thống.

Collection conversation_sessions lưu lịch sử hội thoại với TTL index tự động xóa sau 24 giờ. Đây là bộ nhớ ngắn hạn, giúp hệ thống nhớ ngữ cảnh trong một phiên làm việc.

Collection reasoning_traces lưu toàn bộ quá trình suy luận của mỗi truy vấn, bao gồm các tín hiệu nào được kích hoạt, điểm số của từng giai đoạn, và thời gian xử lý. Đây là công cụ quan trọng để debug và cải thiện hệ thống.

Collection legal_cases lưu các án lệ và quyết định tòa án, được nhúng vector để tìm kiếm các vụ án có hoàn cảnh tương tự.

---

## Phần 10: Kết Quả và Tác Động

Trên bộ dữ liệu thử nghiệm với hai loại tài liệu — hợp đồng tiếng Anh và hợp đồng tiếng Việt — LexAI đạt được kết quả đáng chú ý. Toàn bộ pipeline xử lý hoàn tất trong dưới nửa giây. Tỷ lệ truy xuất đúng trong các bài kiểm tra cross-language đạt 100%. Hệ thống tự động tạo ra gần 30 canonical reference và 20 cạnh ALIAS_OF cho mỗi tài liệu, không cần can thiệp thủ công.

Quan trọng hơn các con số kỹ thuật là tác động thực tế. Một người lao động bình thường tại Việt Nam có thể nhận được câu trả lời pháp lý chính xác trong vòng hai giây, thay vì phải chờ đợi vài ngày và trả hàng trăm nghìn đồng cho mỗi lần tư vấn. Một doanh nghiệp nhỏ có thể kiểm tra điều khoản hợp đồng của mình ngay trong đêm trước khi ký, thay vì phụ thuộc vào lịch hẹn của luật sư.

LexAI không thay thế luật sư. Nhưng nó dân chủ hóa khả năng tiếp cận kiến thức pháp lý cơ bản — đưa thông tin đúng đến đúng người vào đúng lúc.

---

## Phần 11: Khả Năng Mở Rộng — Universal Recommendation Infrastructure

Điều quan trọng cần nhấn mạnh là LexAI không phải chỉ là một ứng dụng pháp lý. Đây là một kiến trúc Recommendation Engine phổ quát, có thể áp dụng cho bất kỳ domain nào chỉ cần thay đổi tập dữ liệu đầu vào.

Thay collection law_chunks bằng catalog sản phẩm, bạn có hệ thống gợi ý thương mại điện tử với khả năng hiểu ngữ nghĩa câu hỏi của khách hàng. Thay bằng thư viện nội dung phim và series, bạn có hệ thống gợi ý streaming cá nhân hóa. Thay bằng hướng dẫn y tế và tài liệu lâm sàng, bạn có hệ thống hỗ trợ quyết định trong y tế. Thay bằng nội dung khóa học và bài giảng, bạn có hệ thống học tập thích ứng.

MongoDB Vector Search và Aggregation Pipeline là hạ tầng cốt lõi. Hybrid retrieval fusion, collaborative filtering, six-signal reranking, và cross-language canonical IDs là các thành phần kỹ thuật. Tất cả đều độc lập với domain. Chỉ có dữ liệu và từ điển thuật ngữ là thay đổi.

---

## Phần 12: Lộ Trình Phát Triển

Trong quý ba năm 2026, nhóm phát triển sẽ tích hợp mô hình embedding BGE-M3, được tối ưu đặc biệt cho tiếng Việt và các ngôn ngữ châu Á. Đồng thời, hệ thống phản hồi thời gian thực sẽ được hoàn thiện, cho phép reranking cập nhật ngay khi người dùng đánh giá kết quả.

Trong quý bốn năm 2026, LexAI sẽ mở API công khai cho luật sư và công ty luật, cùng với tính năng so sánh và phát hiện mâu thuẫn giữa các văn bản pháp luật. Ứng dụng di động cũng sẽ được ra mắt để tiếp cận người dùng không có máy tính.

Đến năm 2027, mục tiêu là mở rộng sang các nước ASEAN — bắt đầu với Thái Lan, Indonesia, và Malaysia — nơi cũng có khoảng cách lớn giữa nhu cầu tư vấn pháp lý và khả năng tiếp cận của người dân. Mô hình kinh doanh B2B SaaS sẽ được triển khai cho các doanh nghiệp cần theo dõi tuân thủ pháp lý.

---

## Phần 13: Vì Sao LexAI Xứng Đáng Chiến Thắng

LexAI đáp ứng đầy đủ yêu cầu kỹ thuật của cuộc thi: MongoDB Vector Search cho semantic similarity search và Aggregation Pipeline cho collaborative filtering. Nhưng hơn thế nữa, LexAI thể hiện cách hai công nghệ này có thể kết hợp để giải quyết một bài toán thực sự quan trọng.

Sự sáng tạo đến từ việc áp dụng Recommendation Engine vào domain pháp lý — một lĩnh vực chưa ai khai thác ở Việt Nam, nhưng có tiềm năng tác động đến hàng triệu người. Triển khai kỹ thuật vượt xa yêu cầu tối thiểu, với pipeline bảy tầng, bộ nhớ cross-session, đa ngôn ngữ, và khả năng fallback khi không có kết nối AI. Tác động và tiềm năng là rõ ràng: 97 triệu người dùng tiềm năng, chi phí tư vấn hiện tại vượt quá khả năng của đại đa số, và thị trường LegalTech toàn cầu đang tăng trưởng hơn 10% mỗi năm.

LexAI là bằng chứng rằng MongoDB không chỉ là nơi lưu dữ liệu — mà là hạ tầng đủ mạnh để chạy toàn bộ một hệ thống AI thông minh, từ vector search đến collaborative filtering, từ bộ nhớ vĩnh viễn đến phân tích hành vi thời gian thực.

Mọi người đều xứng đáng được tư vấn đúng lúc.
