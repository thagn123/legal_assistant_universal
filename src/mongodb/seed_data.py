"""
Seed data for the Legal Knowledge Recommendation Engine.

Loads pre-defined Vietnamese legal templates, risk patterns, and compliance
checklists into MongoDB on first startup (idempotent — safe to re-run).

Usage:
    from src.mongodb.seed_data import seed_all
    seed_all(vector_storage)
"""

from __future__ import annotations

import logging
from typing import List

from src.mongodb.mongo_storage import VectorStorage
from src.pipeline.embedding_stage import embed_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Contract Templates
# ---------------------------------------------------------------------------

_TEMPLATES = [
    {
        "template_id": "tpl_thue_nha_dan_dung",
        "name": "Hợp đồng thuê nhà ở dân dụng",
        "industry": "bat_dong_san",
        "contract_type": "thue_nha",
        "description": "Mẫu hợp đồng thuê nhà ở dân dụng giữa cá nhân, phù hợp cho thuê nhà nguyên căn hoặc phòng trọ dưới 1 năm và từ 1 năm trở lên.",
        "key_clauses": [
            "Thông tin bên cho thuê và bên thuê (CMND/CCCD, địa chỉ)",
            "Mô tả tài sản thuê (diện tích, địa chỉ, tình trạng)",
            "Thời hạn thuê, thời điểm bắt đầu và kết thúc",
            "Giá thuê, phương thức thanh toán, ngày thanh toán",
            "Tiền đặt cọc và điều kiện hoàn trả",
            "Nghĩa vụ bảo trì, sửa chữa",
            "Điều kiện chấm dứt hợp đồng trước hạn",
            "Giải quyết tranh chấp",
        ],
        "related_laws": [
            "Bộ luật Dân sự 2015 — Điều 472–482 (hợp đồng thuê tài sản)",
            "Luật Nhà ở 2023 — Điều 149–163",
            "Nghị định 99/2015/NĐ-CP hướng dẫn Luật Nhà ở",
        ],
        "download_hint": "Phù hợp thuê nhà ở giữa cá nhân, cần công chứng nếu thời hạn ≥ 6 tháng.",
        "priority": 1,
    },
    {
        "template_id": "tpl_thue_van_phong",
        "name": "Hợp đồng thuê văn phòng / mặt bằng thương mại",
        "industry": "bat_dong_san",
        "contract_type": "thue_van_phong",
        "description": "Mẫu hợp đồng thuê văn phòng hoặc mặt bằng kinh doanh, phù hợp cho doanh nghiệp thuê từ chủ tòa nhà hoặc cá nhân.",
        "key_clauses": [
            "Thông tin các bên (tên công ty, MST, người đại diện)",
            "Mô tả mặt bằng (diện tích sàn, tầng, số phòng, tiện ích đi kèm)",
            "Thời hạn thuê, gia hạn tự động",
            "Giá thuê, phụ phí (điện, nước, dịch vụ, gửi xe)",
            "Tiền đặt cọc và điều kiện hoàn trả",
            "Quyền cải tạo nội thất",
            "Điều khoản bảo hiểm tài sản",
            "Phạt vi phạm và bồi thường",
        ],
        "related_laws": [
            "Bộ luật Dân sự 2015 — Điều 472–482",
            "Luật Kinh doanh bất động sản 2023",
            "Luật Thương mại 2005 — Điều 518 (hợp đồng dịch vụ)",
        ],
        "download_hint": "Cần công chứng hoặc chứng thực nếu thời hạn thuê ≥ 6 tháng.",
        "priority": 2,
    },
    {
        "template_id": "tpl_mua_ban_dat",
        "name": "Hợp đồng chuyển nhượng quyền sử dụng đất",
        "industry": "bat_dong_san",
        "contract_type": "mua_ban_dat",
        "description": "Mẫu hợp đồng chuyển nhượng quyền sử dụng đất và tài sản gắn liền với đất, bắt buộc công chứng trước khi đăng ký tại Văn phòng đăng ký đất đai.",
        "key_clauses": [
            "Thông tin bên chuyển nhượng và bên nhận chuyển nhượng",
            "Thông tin thửa đất (số thửa, diện tích, tọa độ, loại đất, số GCN)",
            "Giá chuyển nhượng, phương thức và tiến độ thanh toán",
            "Thời điểm bàn giao thực tế",
            "Nghĩa vụ tài chính (thuế TNCN, lệ phí trước bạ)",
            "Bảo đảm không tranh chấp, không thế chấp",
            "Điều khoản phạt vi phạm",
        ],
        "related_laws": [
            "Luật Đất đai 2024 — Điều 45, 126–136",
            "Bộ luật Dân sự 2015 — Điều 500–532",
            "Luật Công chứng 2014 — Điều 35 (bắt buộc công chứng)",
            "Luật Kinh doanh bất động sản 2023",
        ],
        "download_hint": "BẮT BUỘC công chứng tại tổ chức hành nghề công chứng trước khi đăng ký sang tên.",
        "priority": 1,
    },
    {
        "template_id": "tpl_hop_dong_lao_dong",
        "name": "Hợp đồng lao động (HĐLĐ xác định thời hạn)",
        "industry": "lao_dong",
        "contract_type": "lao_dong",
        "description": "Mẫu hợp đồng lao động xác định thời hạn từ 1 đến 36 tháng, tuân thủ Bộ luật Lao động 2019.",
        "key_clauses": [
            "Thông tin người lao động và người sử dụng lao động",
            "Công việc, địa điểm làm việc",
            "Thời hạn hợp đồng (ngày bắt đầu, ngày kết thúc)",
            "Mức lương, hình thức trả lương, kỳ trả lương",
            "Thời giờ làm việc, thời giờ nghỉ ngơi",
            "Trang bị bảo hộ lao động",
            "BHXH, BHYT, BHTN",
            "Điều khoản thử việc (nếu có)",
            "Quyền và nghĩa vụ các bên",
            "Chấm dứt hợp đồng, trợ cấp thôi việc",
        ],
        "related_laws": [
            "Bộ luật Lao động 2019 — Điều 13–50",
            "Nghị định 145/2020/NĐ-CP",
            "Luật BHXH 2014",
        ],
        "download_hint": "Phải ký kết bằng văn bản. Không được thử việc quá 60 ngày (công việc yêu cầu CĐ trở lên) hoặc 30 ngày.",
        "priority": 1,
    },
    {
        "template_id": "tpl_hop_dong_dich_vu",
        "name": "Hợp đồng cung ứng dịch vụ",
        "industry": "thuong_mai",
        "contract_type": "dich_vu",
        "description": "Mẫu hợp đồng dịch vụ giữa doanh nghiệp với doanh nghiệp (B2B) hoặc doanh nghiệp với cá nhân, phù hợp cho tư vấn, gia công, kỹ thuật, marketing...",
        "key_clauses": [
            "Thông tin các bên (tên, MST/CMND, địa chỉ, người đại diện)",
            "Mô tả dịch vụ và phạm vi công việc",
            "Thời gian thực hiện và tiến độ",
            "Giá dịch vụ và lịch thanh toán",
            "Chất lượng nghiệm thu, tiêu chí hoàn thành",
            "Bảo mật thông tin",
            "Sở hữu trí tuệ đối với sản phẩm giao nộp",
            "Phạt vi phạm (thường 8% giá trị hợp đồng theo Luật TM)",
            "Bồi thường thiệt hại",
            "Giải quyết tranh chấp (Tòa án / Trọng tài VIAC)",
        ],
        "related_laws": [
            "Luật Thương mại 2005 — Điều 518–569",
            "Bộ luật Dân sự 2015 — Điều 513–521",
        ],
        "download_hint": "Phạt vi phạm tối đa 8% phần nghĩa vụ bị vi phạm theo Luật Thương mại 2005.",
        "priority": 2,
    },
    {
        "template_id": "tpl_hop_dong_mua_ban",
        "name": "Hợp đồng mua bán hàng hóa",
        "industry": "thuong_mai",
        "contract_type": "mua_ban_hang_hoa",
        "description": "Mẫu hợp đồng mua bán hàng hóa giữa các thương nhân, phù hợp cho giao dịch thương mại thông thường.",
        "key_clauses": [
            "Thông tin bên bán và bên mua",
            "Tên hàng, quy cách, chất lượng, số lượng",
            "Đơn giá, tổng giá trị",
            "Điều kiện và thời hạn thanh toán",
            "Thời hạn và địa điểm giao hàng",
            "Điều kiện giao hàng (Incoterms nếu có)",
            "Kiểm tra hàng hóa và khiếu nại",
            "Bảo hành (nếu có)",
            "Bất khả kháng",
            "Phạt vi phạm và bồi thường",
        ],
        "related_laws": [
            "Luật Thương mại 2005 — Điều 24–62",
            "Bộ luật Dân sự 2015 — Điều 430–449",
        ],
        "download_hint": "Lưu ý điều khoản phạt không được quá 8% phần nghĩa vụ vi phạm (Điều 301 LTM).",
        "priority": 2,
    },
]

# ---------------------------------------------------------------------------
# Legal Risk Patterns
# ---------------------------------------------------------------------------

_RISKS = [
    {
        "risk_id": "risk_dat_khong_so",
        "name": "Đất không có giấy tờ pháp lý",
        "severity": "cao",
        "description": "Giao dịch chuyển nhượng đất không có Giấy chứng nhận quyền sử dụng đất (sổ đỏ/sổ hồng) hoặc giấy tờ hợp lệ khác. Hợp đồng có thể bị vô hiệu và người mua mất toàn bộ tiền.",
        "indicators": [
            "Bên bán chỉ có giấy tờ viết tay, không có GCN do Nhà nước cấp",
            "Đất đang trong diện quy hoạch, giải tỏa",
            "Chưa thực hiện thủ tục đăng ký đất đai tại Văn phòng đăng ký",
            "Đất có tranh chấp chưa giải quyết",
        ],
        "mitigation": [
            "Yêu cầu xem bản gốc GCN, tra cứu thông tin tại Văn phòng đăng ký đất đai",
            "Kiểm tra quy hoạch tại UBND cấp huyện/xã",
            "Thuê luật sư thẩm định pháp lý trước khi giao dịch",
            "Không đặt cọc hoặc thanh toán trước khi xác minh đầy đủ",
        ],
        "related_law_types": ["dat_dai"],
    },
    {
        "risk_id": "risk_het_thoi_hieu",
        "name": "Hết thời hiệu khởi kiện",
        "severity": "cao",
        "description": "Người bị vi phạm quyền lợi không khởi kiện trong thời hạn pháp luật quy định dẫn đến mất quyền khởi kiện tại Tòa án.",
        "indicators": [
            "Đã biết vi phạm từ hơn 2-3 năm nhưng chưa khởi kiện",
            "Không có văn bản yêu cầu/khiếu nại nào để làm mốc tính thời hiệu",
            "Đang tranh chấp mà chưa xác định mốc thời điểm phát sinh quyền khởi kiện",
        ],
        "mitigation": [
            "Xác định chính xác thời điểm biết hoặc phải biết quyền bị xâm phạm",
            "Gửi văn bản yêu cầu ngay để cắt/tính lại thời hiệu",
            "Nộp đơn khởi kiện trước khi hết thời hiệu (thường 2-3 năm tùy lĩnh vực)",
            "Tham vấn luật sư ngay khi phát hiện vi phạm",
        ],
        "related_law_types": ["dan_su", "hop_dong", "dat_dai", "lao_dong"],
    },
    {
        "risk_id": "risk_hop_dong_vo_hieu",
        "name": "Hợp đồng vô hiệu",
        "severity": "cao",
        "description": "Hợp đồng bị tuyên vô hiệu do vi phạm hình thức, không đủ năng lực pháp lý, hoặc vi phạm điều cấm của luật. Các bên phải hoàn trả lại cho nhau những gì đã nhận.",
        "indicators": [
            "Hợp đồng không được công chứng/chứng thực theo quy định bắt buộc",
            "Một bên không có năng lực hành vi dân sự đầy đủ",
            "Hợp đồng do nhầm lẫn, lừa dối, hoặc đe dọa",
            "Đối tượng hợp đồng là tài sản bị cấm giao dịch",
        ],
        "mitigation": [
            "Công chứng hợp đồng khi pháp luật yêu cầu (đất đai, nhà ở)",
            "Kiểm tra năng lực pháp lý của đối tác (CMND, điều lệ công ty, ủy quyền)",
            "Không ký hợp đồng dưới bất kỳ áp lực nào",
            "Rà soát nội dung với luật sư trước khi ký",
        ],
        "related_law_types": ["hop_dong", "dat_dai", "dan_su"],
    },
    {
        "risk_id": "risk_sa_thai_trai_luat",
        "name": "Sa thải / chấm dứt hợp đồng lao động trái luật",
        "severity": "cao",
        "description": "Người sử dụng lao động chấm dứt HĐLĐ không đúng quy trình, căn cứ hoặc thông báo dẫn đến phải bồi thường, nhận lại người lao động và trả lương trong thời gian không làm việc.",
        "indicators": [
            "Sa thải mà không có quyết định bằng văn bản",
            "Không tuân thủ thủ tục xử lý kỷ luật lao động (họp xét kỷ luật, biên bản)",
            "Chấm dứt HĐLĐ xác định thời hạn trước khi hết hạn không có lý do chính đáng",
            "Không thông báo trước theo quy định (thường 30-45 ngày)",
        ],
        "mitigation": [
            "Lưu đầy đủ hồ sơ kỷ luật lao động, biên bản họp có chữ ký",
            "Tuân thủ đúng thời hạn thông báo chấm dứt HĐLĐ",
            "Tham khảo Phòng Lao động TBXH trước khi sa thải trong trường hợp phức tạp",
            "Trả đủ trợ cấp thôi việc / mất việc làm theo quy định",
        ],
        "related_law_types": ["lao_dong"],
    },
    {
        "risk_id": "risk_tron_thue",
        "name": "Rủi ro trốn thuế / khai thuế sai",
        "severity": "cao",
        "description": "Không khai báo hoặc khai sai doanh thu, thu nhập chịu thuế dẫn đến bị truy thu, phạt vi phạm hành chính, thậm chí truy cứu trách nhiệm hình sự nếu số tiền lớn.",
        "indicators": [
            "Không xuất hóa đơn cho toàn bộ doanh thu",
            "Kê khai chi phí không có chứng từ hợp lệ",
            "Không đăng ký thuế khi bắt đầu kinh doanh",
            "Chuyển nhượng tài sản dưới giá thị trường để giảm thuế",
        ],
        "mitigation": [
            "Sử dụng phần mềm kế toán, xuất hóa đơn điện tử đầy đủ",
            "Kê khai và nộp thuế đúng hạn",
            "Lưu đầy đủ chứng từ, hợp đồng, hóa đơn trong 10 năm",
            "Tham vấn kế toán/thuế trước các giao dịch lớn",
        ],
        "related_law_types": ["thue"],
    },
    {
        "risk_id": "risk_vi_pham_soht",
        "name": "Vi phạm quyền sở hữu trí tuệ",
        "severity": "trung_binh",
        "description": "Sử dụng tên thương mại, nhãn hiệu, bản quyền, kiểu dáng công nghiệp mà không được phép của chủ sở hữu, dẫn đến bị xử phạt hành chính hoặc bồi thường dân sự.",
        "indicators": [
            "Dùng logo, tên thương mại giống hoặc tương tự nhãn hiệu đã đăng ký",
            "Sao chép nội dung (văn bản, hình ảnh, phần mềm) không có giấy phép",
            "Kinh doanh hàng hóa mang nhãn hiệu giả mạo",
        ],
        "mitigation": [
            "Tra cứu nhãn hiệu trên Cơ sở dữ liệu NOIP trước khi đặt tên",
            "Đăng ký bảo hộ nhãn hiệu, kiểu dáng công nghiệp",
            "Ký hợp đồng li-xăng khi sử dụng tài sản trí tuệ của bên thứ ba",
        ],
        "related_law_types": ["so_huu_tri_tue"],
    },
    {
        "risk_id": "risk_dat_dang_the_chap",
        "name": "Mua đất đang thế chấp ngân hàng",
        "severity": "cao",
        "description": "Chuyển nhượng quyền sử dụng đất khi tài sản đang thế chấp tại tổ chức tín dụng mà không được đồng ý của bên nhận thế chấp. Giao dịch có thể bị vô hiệu và người mua mất tiền.",
        "indicators": [
            "Sổ đỏ/sổ hồng đang được giữ tại ngân hàng",
            "Bên bán yêu cầu đặt cọc lớn để 'chuộc sổ' trước",
            "Thông tin thế chấp hiển thị trên GCN hoặc hệ thống đăng ký",
        ],
        "mitigation": [
            "Kiểm tra tình trạng thế chấp tại Trung tâm đăng ký giao dịch bảo đảm",
            "Yêu cầu bên bán xuất trình GCN bản gốc không có ghi thế chấp",
            "Thanh toán trực tiếp cho ngân hàng để giải chấp trước khi giao dịch",
            "Công chứng hợp đồng sau khi đã giải chấp xong",
        ],
        "related_law_types": ["dat_dai"],
    },
]

# ---------------------------------------------------------------------------
# Compliance Checklists
# ---------------------------------------------------------------------------

_CHECKLISTS = [
    {
        "checklist_id": "chk_thanh_lap_tnhh",
        "name": "Checklist thành lập Công ty TNHH hai thành viên trở lên",
        "business_type": "tnhh",
        "transaction_type": "thanh_lap_cong_ty",
        "description": "Danh mục giấy tờ và thủ tục cần hoàn thiện để đăng ký thành lập Công ty TNHH hai thành viên trở lên theo Luật Doanh nghiệp 2020.",
        "related_laws": [
            "Luật Doanh nghiệp 2020 — Điều 44–73",
            "Nghị định 01/2021/NĐ-CP về đăng ký doanh nghiệp",
        ],
        "priority": 1,
        "items": [
            {
                "item_id": "i1", "category": "Giấy tờ pháp lý",
                "description": "CMND/CCCD/Hộ chiếu còn hiệu lực của tất cả thành viên góp vốn",
                "required": True, "related_law": "Luật DN 2020 — Điều 46",
                "deadline_note": "Chuẩn bị trước khi nộp hồ sơ",
            },
            {
                "item_id": "i2", "category": "Giấy tờ pháp lý",
                "description": "Soạn thảo và ký Điều lệ Công ty (theo mẫu hoặc tự soạn)",
                "required": True, "related_law": "Luật DN 2020 — Điều 24–26",
                "deadline_note": "Ký trước ngày nộp hồ sơ",
            },
            {
                "item_id": "i3", "category": "Đăng ký",
                "description": "Nộp hồ sơ đăng ký doanh nghiệp tại Cổng dịch vụ công quốc gia hoặc Phòng Đăng ký kinh doanh — Sở KH&ĐT",
                "required": True, "related_law": "Nghị định 01/2021",
                "deadline_note": "Phòng ĐKKD cấp GCN trong 3 ngày làm việc",
            },
            {
                "item_id": "i4", "category": "Tài chính",
                "description": "Xác định vốn điều lệ và thời hạn góp đủ vốn (tối đa 90 ngày từ ngày cấp GCN)",
                "required": True, "related_law": "Luật DN 2020 — Điều 47",
                "deadline_note": "Góp đủ vốn trong 90 ngày từ ngày cấp GCN",
            },
            {
                "item_id": "i5", "category": "Thuế",
                "description": "Đăng ký thuế và nhận mã số thuế (tự động cấp cùng GCN doanh nghiệp)",
                "required": True, "related_law": "Luật Quản lý thuế 2019",
                "deadline_note": "Tự động sau khi được cấp GCN",
            },
            {
                "item_id": "i6", "category": "Hoạt động",
                "description": "Mở tài khoản ngân hàng cho doanh nghiệp và đăng ký với cơ quan thuế",
                "required": True, "related_law": "Thông tư 80/2021/TT-BTC",
                "deadline_note": "Trong vòng 10 ngày kể từ ngày mở tài khoản",
            },
            {
                "item_id": "i7", "category": "Hoạt động",
                "description": "Đặt biển hiệu tại trụ sở chính",
                "required": True, "related_law": "Luật DN 2020 — Điều 40",
                "deadline_note": "Trước ngày bắt đầu hoạt động",
            },
            {
                "item_id": "i8", "category": "Hoạt động",
                "description": "Đăng ký sử dụng hóa đơn điện tử",
                "required": True, "related_law": "Nghị định 123/2020/NĐ-CP",
                "deadline_note": "Trước khi phát sinh doanh thu đầu tiên",
            },
        ],
    },
    {
        "checklist_id": "chk_mua_ban_dat",
        "name": "Checklist giao dịch chuyển nhượng quyền sử dụng đất",
        "business_type": "general",
        "transaction_type": "mua_ban_dat",
        "description": "Danh mục thủ tục pháp lý cần thực hiện khi mua bán / chuyển nhượng quyền sử dụng đất.",
        "related_laws": [
            "Luật Đất đai 2024 — Điều 45, 126–136",
            "Bộ luật Dân sự 2015 — Điều 500–532",
            "Luật Công chứng 2014 — Điều 35",
        ],
        "priority": 1,
        "items": [
            {
                "item_id": "i1", "category": "Thẩm định",
                "description": "Kiểm tra GCN bản gốc: số thửa, diện tích, loại đất, thời hạn sử dụng, tên chủ sử dụng",
                "required": True, "related_law": "Luật Đất đai 2024 — Điều 133",
                "deadline_note": "Trước khi đặt cọc",
            },
            {
                "item_id": "i2", "category": "Thẩm định",
                "description": "Kiểm tra tình trạng thế chấp tại Trung tâm Đăng ký giao dịch bảo đảm",
                "required": True, "related_law": "Nghị định 99/2022/NĐ-CP",
                "deadline_note": "Trước khi đặt cọc",
            },
            {
                "item_id": "i3", "category": "Thẩm định",
                "description": "Tra cứu quy hoạch sử dụng đất tại UBND cấp huyện",
                "required": True, "related_law": "Luật Đất đai 2024 — Điều 220",
                "deadline_note": "Trước khi ký hợp đồng",
            },
            {
                "item_id": "i4", "category": "Hợp đồng",
                "description": "Ký hợp đồng đặt cọc (nên công chứng), giới hạn tiền cọc ≤ 10% giá trị",
                "required": False, "related_law": "Bộ luật Dân sự 2015 — Điều 328",
                "deadline_note": "Ký trước khi ký hợp đồng chính thức",
            },
            {
                "item_id": "i5", "category": "Hợp đồng",
                "description": "Công chứng hợp đồng chuyển nhượng tại tổ chức hành nghề công chứng",
                "required": True, "related_law": "Luật Công chứng 2014 — Điều 35",
                "deadline_note": "Bắt buộc, không thể thay thế",
            },
            {
                "item_id": "i6", "category": "Thuế",
                "description": "Nộp thuế thu nhập cá nhân (2% giá chuyển nhượng) và lệ phí trước bạ (0,5% giá trị)",
                "required": True, "related_law": "Luật Thuế TNCN; Nghị định 10/2022/NĐ-CP",
                "deadline_note": "Trước khi nộp hồ sơ đăng ký biến động",
            },
            {
                "item_id": "i7", "category": "Đăng ký",
                "description": "Nộp hồ sơ đăng ký biến động đất đai tại Văn phòng Đăng ký đất đai",
                "required": True, "related_law": "Luật Đất đai 2024 — Điều 133",
                "deadline_note": "Trong 30 ngày kể từ ngày ký hợp đồng công chứng",
            },
        ],
    },
    {
        "checklist_id": "chk_thue_lao_dong",
        "name": "Checklist tuân thủ khi tuyển dụng lao động",
        "business_type": "general",
        "transaction_type": "thue_lao_dong",
        "description": "Danh mục thủ tục pháp lý doanh nghiệp cần thực hiện khi tuyển dụng và ký hợp đồng lao động.",
        "related_laws": [
            "Bộ luật Lao động 2019",
            "Luật BHXH 2014",
            "Nghị định 145/2020/NĐ-CP",
        ],
        "priority": 2,
        "items": [
            {
                "item_id": "i1", "category": "Hợp đồng",
                "description": "Ký HĐLĐ bằng văn bản trước hoặc ngay khi người lao động bắt đầu làm việc",
                "required": True, "related_law": "BLLĐ 2019 — Điều 14",
                "deadline_note": "Bắt buộc, không thể dùng hình thức miệng",
            },
            {
                "item_id": "i2", "category": "Bảo hiểm",
                "description": "Đăng ký BHXH, BHYT, BHTN cho người lao động",
                "required": True, "related_law": "Luật BHXH 2014 — Điều 4, 30",
                "deadline_note": "Trong 30 ngày kể từ ngày ký HĐLĐ",
            },
            {
                "item_id": "i3", "category": "Lương",
                "description": "Đảm bảo mức lương ≥ mức lương tối thiểu vùng hiện hành",
                "required": True, "related_law": "BLLĐ 2019 — Điều 91; Nghị định 74/2024/NĐ-CP",
                "deadline_note": "Áp dụng ngay từ ngày 01/07/2024",
            },
            {
                "item_id": "i4", "category": "Nội quy",
                "description": "Ban hành Nội quy lao động và đăng ký tại Sở/Phòng LĐTBXH (DN ≥ 10 lao động)",
                "required": True, "related_law": "BLLĐ 2019 — Điều 119",
                "deadline_note": "Trước khi thi hành",
            },
            {
                "item_id": "i5", "category": "Thuế",
                "description": "Khấu trừ và khai nộp thuế TNCN từ tiền lương hàng tháng",
                "required": True, "related_law": "Luật Thuế TNCN; TT 111/2013/TT-BTC",
                "deadline_note": "Hàng tháng hoặc quý tùy quy mô",
            },
            {
                "item_id": "i6", "category": "An toàn",
                "description": "Huấn luyện an toàn lao động cho NLĐ trước khi bắt đầu công việc",
                "required": True, "related_law": "Luật ATVSLĐ 2015 — Điều 14",
                "deadline_note": "Trước ngày đầu tiên làm việc",
            },
        ],
    },
    {
        "checklist_id": "chk_thanh_lap_co_phan",
        "name": "Checklist thành lập Công ty Cổ phần",
        "business_type": "co_phan",
        "transaction_type": "thanh_lap_cong_ty",
        "description": "Danh mục thủ tục thành lập Công ty Cổ phần theo Luật Doanh nghiệp 2020.",
        "related_laws": [
            "Luật Doanh nghiệp 2020 — Điều 111–171",
            "Nghị định 01/2021/NĐ-CP",
        ],
        "priority": 1,
        "items": [
            {
                "item_id": "i1", "category": "Cổ đông",
                "description": "Xác định cơ cấu cổ đông sáng lập (tối thiểu 3 cổ đông sáng lập)",
                "required": True, "related_law": "Luật DN 2020 — Điều 120",
                "deadline_note": "Trước khi nộp hồ sơ",
            },
            {
                "item_id": "i2", "category": "Giấy tờ",
                "description": "Chuẩn bị CMND/CCCD của tất cả cổ đông sáng lập và người đại diện pháp luật",
                "required": True, "related_law": "Luật DN 2020 — Điều 112",
                "deadline_note": "Trước khi nộp hồ sơ",
            },
            {
                "item_id": "i3", "category": "Giấy tờ",
                "description": "Soạn Điều lệ Công ty Cổ phần và Danh sách cổ đông sáng lập",
                "required": True, "related_law": "Luật DN 2020 — Điều 24, 122",
                "deadline_note": "Ký trước ngày nộp hồ sơ",
            },
            {
                "item_id": "i4", "category": "Đăng ký",
                "description": "Nộp hồ sơ đăng ký doanh nghiệp trực tuyến hoặc tại Sở KH&ĐT",
                "required": True, "related_law": "Nghị định 01/2021",
                "deadline_note": "GCN được cấp trong 3 ngày làm việc",
            },
            {
                "item_id": "i5", "category": "Tài chính",
                "description": "Góp đủ vốn điều lệ trong thời hạn quy định (90 ngày)",
                "required": True, "related_law": "Luật DN 2020 — Điều 113",
                "deadline_note": "90 ngày từ ngày cấp GCN",
            },
            {
                "item_id": "i6", "category": "Cổ phần",
                "description": "Phát hành cổ phiếu cho cổ đông sáng lập và vào Sổ đăng ký cổ đông",
                "required": True, "related_law": "Luật DN 2020 — Điều 121",
                "deadline_note": "Sau khi góp đủ vốn",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Seed runner
# ---------------------------------------------------------------------------


def seed_all(vector_storage: VectorStorage) -> dict:
    """
    Insert all templates, risks, checklists, and legal cases into MongoDB.
    Generates embeddings for templates, risks, and cases for vector search.
    Safe to re-run (upsert semantics). Returns counts dict.
    """
    from typing import Dict as _Dict
    logger.info("seed_data: seeding templates …")
    _seed_templates(vector_storage)

    logger.info("seed_data: seeding risks …")
    _seed_risks(vector_storage)

    logger.info("seed_data: seeding checklists …")
    _seed_checklists(vector_storage)

    logger.info("seed_data: seeding legal cases …")
    _seed_legal_cases(vector_storage)

    logger.info("seed_data: done.")
    return {
        "templates": len(_TEMPLATES),
        "risks": len(_RISKS),
        "checklists": len(_CHECKLISTS),
        "legal_cases": len(_LEGAL_CASES),
    }


def _seed_templates(vs: VectorStorage) -> None:
    for tpl in _TEMPLATES:
        embed_text_for = tpl["description"] + " " + " ".join(tpl["key_clauses"])
        emb = embed_text(embed_text_for)
        doc = dict(tpl)
        if emb:
            doc["embedding"] = emb
        vs.upsert_template(doc)
    logger.info("seed_data: %d templates upserted.", len(_TEMPLATES))


def _seed_risks(vs: VectorStorage) -> None:
    for risk in _RISKS:
        embed_text_for = risk["description"] + " " + " ".join(risk["indicators"])
        emb = embed_text(embed_text_for)
        doc = dict(risk)
        if emb:
            doc["embedding"] = emb
        vs.upsert_risk(doc)
    logger.info("seed_data: %d risks upserted.", len(_RISKS))


def _seed_checklists(vs: VectorStorage) -> None:
    for chk in _CHECKLISTS:
        vs.upsert_checklist(chk)
    logger.info("seed_data: %d checklists upserted.", len(_CHECKLISTS))


def _seed_legal_cases(vs: VectorStorage) -> None:
    for case in _LEGAL_CASES:
        embed_text_for = case["title"] + " " + case["situation_summary"]
        emb = embed_text(embed_text_for)
        doc = dict(case)
        if emb:
            doc["embedding"] = emb
        vs.upsert_case(doc)
    logger.info("seed_data: %d legal cases upserted.", len(_LEGAL_CASES))


# ---------------------------------------------------------------------------
# Legal Cases seed data
# ---------------------------------------------------------------------------

_LEGAL_CASES: List[dict] = [
    {
        "case_id": "case_dat_dai_lan_chiem_001",
        "title": "Tranh chấp lấn chiếm đất — hàng xóm xây tường vượt ranh giới",
        "law_type": "dat_dai",
        "situation_summary": (
            "Hàng xóm tự ý xây tường rào lấn sang 50cm đất có sổ đỏ của chủ đất. "
            "Chủ đất đã nhắc nhở nhiều lần nhưng không được giải quyết. "
            "Phần đất bị lấn chiếm khoảng 15m². Sổ đỏ được cấp năm 2010."
        ),
        "legal_issues": ["lấn chiếm đất đai", "tranh chấp ranh giới", "xây dựng trái phép"],
        "outcome": "Thắng kiện sau hòa giải tại UBND",
        "result": "Bên lấn chiếm phải dỡ bỏ công trình và bồi thường chi phí đo đạc.",
        "key_laws": [
            "Luật Đất đai 2024 — Điều 235 (tranh chấp đất đai)",
            "Luật Đất đai 2024 — Điều 168 (quyền của người sử dụng đất)",
            "BLDS 2015 — Điều 174 (ranh giới giữa các bất động sản liền kề)",
        ],
        "lesson": (
            "Bước đầu tiên bắt buộc là hòa giải tại UBND cấp xã trước khi khởi kiện. "
            "Cần thuê đơn vị đo đạc độc lập để có bằng chứng khách quan về ranh giới."
        ),
        "priority": 1,
    },
    {
        "case_id": "case_dat_dai_giay_viet_tay_001",
        "title": "Mua đất bằng giấy viết tay — người bán đòi lại đất",
        "law_type": "dat_dai",
        "situation_summary": (
            "Người mua mua đất năm 2018 bằng giấy tờ viết tay, chưa công chứng, "
            "chưa sang tên sổ đỏ. Người bán nay đòi lại đất với lý do hợp đồng không hợp lệ. "
            "Người mua đã xây nhà và sinh sống trên đất 5 năm."
        ),
        "legal_issues": [
            "hợp đồng chuyển nhượng không công chứng",
            "tranh chấp quyền sử dụng đất",
            "chiếm hữu ngay tình",
        ],
        "outcome": "Tranh chấp — kết quả phụ thuộc vào chứng cứ và thời hiệu",
        "result": (
            "Hợp đồng viết tay về đất đai vô hiệu về hình thức (BLDS 2015 Điều 129). "
            "Tuy nhiên nếu đã thực hiện 2/3 nghĩa vụ, tòa có thể công nhận hiệu lực."
        ),
        "key_laws": [
            "Luật Đất đai 2024 — Điều 27 (hình thức giao dịch đất)",
            "BLDS 2015 — Điều 117, 129 (điều kiện và hình thức giao dịch dân sự)",
            "BLDS 2015 — Điều 236 (xác lập quyền sở hữu theo thời hiệu)",
        ],
        "lesson": (
            "Giao dịch đất đai bắt buộc phải công chứng/chứng thực. "
            "Nếu đã chiếm hữu liên tục, công khai 10 năm có thể xin xác lập quyền sở hữu. "
            "Cần xem xét khả năng yêu cầu tòa công nhận hợp đồng theo Điều 129 BLDS."
        ),
        "priority": 1,
    },
    {
        "case_id": "case_hop_dong_vi_pham_001",
        "title": "Vi phạm hợp đồng dịch vụ — bên cung cấp không thực hiện đúng hạn",
        "law_type": "hop_dong",
        "situation_summary": (
            "Công ty A ký hợp đồng dịch vụ thiết kế website với công ty B, "
            "trị giá 150 triệu đồng, thời hạn 3 tháng. "
            "Sau 5 tháng B vẫn chưa bàn giao sản phẩm và không phản hồi email. "
            "Hợp đồng có điều khoản phạt 0.1%/ngày chậm trễ."
        ),
        "legal_issues": ["vi phạm hợp đồng", "chậm bàn giao", "phạt vi phạm", "bồi thường thiệt hại"],
        "outcome": "Thắng kiện tại Tòa kinh tế",
        "result": (
            "Tòa buộc bên B hoàn trả 150 triệu, bồi thường thiệt hại thực tế 30 triệu, "
            "và phạt vi phạm theo hợp đồng (giới hạn 8% theo Luật Thương mại)."
        ),
        "key_laws": [
            "Luật Thương mại 2005 — Điều 301 (mức phạt vi phạm tối đa 8%)",
            "Luật Thương mại 2005 — Điều 302–303 (bồi thường thiệt hại)",
            "BLDS 2015 — Điều 351–354 (trách nhiệm do vi phạm nghĩa vụ)",
        ],
        "lesson": (
            "Phải gửi thông báo vi phạm bằng văn bản có xác nhận nhận trước khi khởi kiện. "
            "Thời hiệu khởi kiện tranh chấp thương mại là 2 năm. "
            "Mức phạt vi phạm trong hợp đồng thương mại không được vượt 8% giá trị vi phạm."
        ),
        "priority": 1,
    },
    {
        "case_id": "case_lao_dong_sa_thai_001",
        "title": "Sa thải trái luật — không có biên bản họp hội đồng kỷ luật",
        "law_type": "lao_dong",
        "situation_summary": (
            "Người lao động bị sa thải sau 5 năm làm việc với lý do 'vi phạm nội quy' "
            "nhưng không có biên bản xử lý kỷ luật, không được thông báo trước, "
            "và không có biên bản họp hội đồng kỷ luật theo quy định. "
            "Công ty không trả trợ cấp thôi việc."
        ),
        "legal_issues": [
            "sa thải trái luật",
            "vi phạm thủ tục kỷ luật",
            "trợ cấp thôi việc",
            "bồi thường sa thải trái pháp luật",
        ],
        "outcome": "Thắng — sa thải trái luật được xác nhận",
        "result": (
            "Tòa buộc công ty: (1) nhận lại lao động hoặc bồi thường 2 tháng lương/năm làm việc, "
            "(2) trả lương trong thời gian chờ giải quyết, "
            "(3) đóng đủ BHXH bị thiếu."
        ),
        "key_laws": [
            "BLLĐ 2019 — Điều 70 (thủ tục xử lý kỷ luật)",
            "BLLĐ 2019 — Điều 41 (bồi thường sa thải trái pháp luật)",
            "BLLĐ 2019 — Điều 46 (trợ cấp thôi việc)",
        ],
        "lesson": (
            "Sa thải phải tuân thủ đúng thủ tục: có biên bản họp, thông báo trước, "
            "có mặt người lao động hoặc đại diện. "
            "Thiếu thủ tục = sa thải trái luật dù lý do thực chất có thể đúng."
        ),
        "priority": 1,
    },
    {
        "case_id": "case_doanh_nghiep_co_dong_001",
        "title": "Tranh chấp nội bộ — cổ đông thiểu số bị loại khỏi điều hành",
        "law_type": "doanh_nghiep",
        "situation_summary": (
            "Cổ đông thiểu số (30% vốn) trong công ty cổ phần bị đa số cổ đông "
            "thay thế khỏi vị trí Giám đốc bằng nghị quyết ĐHCĐ. "
            "Nghị quyết được thông qua mà không thông báo đúng hạn cho cổ đông thiểu số."
        ),
        "legal_issues": [
            "triệu tập ĐHCĐ không hợp lệ",
            "quyền của cổ đông thiểu số",
            "tranh chấp nội bộ công ty",
        ],
        "outcome": "Thắng một phần — nghị quyết bị tuyên vô hiệu",
        "result": (
            "Tòa tuyên nghị quyết ĐHCĐ vô hiệu do vi phạm thủ tục triệu tập. "
            "Công ty phải tổ chức lại ĐHCĐ theo đúng trình tự Luật Doanh nghiệp."
        ),
        "key_laws": [
            "Luật Doanh nghiệp 2020 — Điều 139–143 (triệu tập ĐHCĐ)",
            "Luật Doanh nghiệp 2020 — Điều 151 (điều kiện thông qua nghị quyết)",
            "Luật Doanh nghiệp 2020 — Điều 206 (quyền khởi kiện của cổ đông)",
        ],
        "lesson": (
            "Nghị quyết ĐHCĐ phải được thông báo đúng thời hạn và đúng địa chỉ đăng ký. "
            "Cổ đông sở hữu từ 5% có quyền yêu cầu triệu tập ĐHCĐ bất thường. "
            "Cổ đông có thể khởi kiện trong vòng 90 ngày kể từ ngày thông qua nghị quyết."
        ),
        "priority": 2,
    },
    {
        "case_id": "case_dat_dai_thua_ke_001",
        "title": "Tranh chấp thừa kế đất đai — di chúc viết tay không hợp lệ",
        "law_type": "dat_dai",
        "situation_summary": (
            "Người để lại di sản có mảnh đất và di chúc viết tay để lại cho con trưởng. "
            "Các con khác phản đối vì di chúc không có người làm chứng và không công chứng. "
            "Người để lại di sản đã mất 2 năm trước."
        ),
        "legal_issues": [
            "di chúc viết tay không hợp lệ",
            "thừa kế theo pháp luật",
            "tranh chấp thừa kế đất",
        ],
        "outcome": "Di chúc bị tuyên vô hiệu — chia thừa kế theo pháp luật",
        "result": (
            "Di chúc viết tay không có người làm chứng bị tuyên vô hiệu. "
            "Tòa chia đất theo pháp luật (chia đều cho các thừa kế cùng hàng). "
            "Con trưởng được ưu tiên nhận đất nếu đồng ý hoàn tiền cho các anh/chị/em."
        ),
        "key_laws": [
            "BLDS 2015 — Điều 634 (di chúc bằng văn bản không có người làm chứng)",
            "BLDS 2015 — Điều 650 (thừa kế theo pháp luật)",
            "Luật Đất đai 2024 — Điều 45 (điều kiện thực hiện quyền thừa kế đất)",
        ],
        "lesson": (
            "Di chúc viết tay cần có ít nhất 2 người làm chứng không thuộc hàng thừa kế. "
            "Nên công chứng di chúc để tránh tranh chấp. "
            "Thời hiệu khởi kiện tranh chấp thừa kế: 30 năm với BĐS kể từ ngày mở thừa kế."
        ),
        "priority": 1,
    },
    {
        "case_id": "case_hop_dong_thue_nha_001",
        "title": "Tranh chấp hợp đồng thuê nhà — chủ nhà đơn phương chấm dứt không đúng hạn",
        "law_type": "hop_dong",
        "situation_summary": (
            "Người thuê nhà có hợp đồng 2 năm, còn 8 tháng hợp đồng. "
            "Chủ nhà yêu cầu dọn ra trong 15 ngày với lý do cần nhà để ở, "
            "không phải lý do vi phạm của bên thuê. "
            "Bên thuê đã đặt cọc 3 tháng tiền thuê."
        ),
        "legal_issues": [
            "đơn phương chấm dứt hợp đồng thuê nhà",
            "hoàn trả tiền đặt cọc",
            "bồi thường thiệt hại",
        ],
        "outcome": "Thắng — bên thuê được bồi thường",
        "result": (
            "Tòa buộc chủ nhà: hoàn trả tiền đặt cọc, "
            "bồi thường 2 tháng tiền thuê và chi phí chuyển nhà thực tế. "
            "Bên thuê được ở thêm 30 ngày để tìm nhà mới."
        ),
        "key_laws": [
            "BLDS 2015 — Điều 132 (chấm dứt hợp đồng thuê tài sản)",
            "Luật Nhà ở 2023 — Điều 131 (quyền và nghĩa vụ bên cho thuê)",
            "BLDS 2015 — Điều 328 (đặt cọc và hoàn trả)",
        ],
        "lesson": (
            "Chủ nhà chỉ được đơn phương chấm dứt hợp đồng thuê khi bên thuê vi phạm "
            "hoặc theo thỏa thuận trong hợp đồng. "
            "Nếu vi phạm, phải bồi thường tiền cọc và thiệt hại thực tế."
        ),
        "priority": 1,
    },
    {
        "case_id": "case_lao_dong_luong_001",
        "title": "Tranh chấp tiền lương — công ty không trả lương tháng cuối và trợ cấp",
        "law_type": "lao_dong",
        "situation_summary": (
            "Người lao động nghỉ việc sau khi nộp đơn xin thôi việc đúng thời hạn (30 ngày). "
            "Công ty không trả lương tháng cuối và tiền trợ cấp thôi việc. "
            "Người lao động đã làm việc 7 năm, lương 12 triệu/tháng."
        ),
        "legal_issues": ["chậm trả lương", "trợ cấp thôi việc", "tiền lương tháng cuối"],
        "outcome": "Thắng tại Phòng Lao động",
        "result": (
            "Công ty bị buộc trả: lương tháng cuối 12 triệu + trợ cấp thôi việc 42 triệu "
            "(7 năm × 0.5 tháng lương/năm) + lãi chậm trả theo BLLĐ."
        ),
        "key_laws": [
            "BLLĐ 2019 — Điều 46 (trợ cấp thôi việc = 0.5 tháng lương/năm)",
            "BLLĐ 2019 — Điều 94 (nghĩa vụ trả lương đúng hạn)",
            "BLLĐ 2019 — Điều 48 (nghĩa vụ thanh toán khi chấm dứt HĐ lao động)",
        ],
        "lesson": (
            "Công ty phải thanh toán đầy đủ trong vòng 14 ngày kể từ ngày chấm dứt HĐLĐ. "
            "Chậm trả lương phải tính thêm lãi. "
            "Trợ cấp thôi việc = 0.5 tháng lương bình quân × số năm làm việc "
            "(chỉ tính các năm chưa đóng BHTN)."
        ),
        "priority": 1,
    },
]
