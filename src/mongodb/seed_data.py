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
# Official Forms — Thông tư 55/2026/TT-BTC Phụ lục I (49 mẫu văn bản đầu tư)
# ---------------------------------------------------------------------------

_OFFICIAL_FORMS: List[dict] = [
    # ── Mẫu 1: Phụ lục điều kiện kỹ thuật xây dựng ──────────────────────────
    {
        "template_id": "tt55_I_phuluc",
        "form_code": "I",
        "name": "Phụ lục I — Các điều kiện, tiêu chuẩn, quy chuẩn kỹ thuật xây dựng",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "ho_so_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Phụ lục kỹ thuật gửi kèm văn bản đề nghị thực hiện dự án đầu tư, liệt kê các điều kiện, tiêu chuẩn và quy chuẩn kỹ thuật theo pháp luật xây dựng phải đáp ứng.",
        "key_clauses": ["Quy chuẩn quốc gia về xây dựng", "Tiêu chuẩn áp dụng cho công trình", "Điều kiện an toàn phòng cháy", "Hệ thống hạ tầng kỹ thuật"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Gửi kèm theo Văn bản đề nghị thực hiện dự án đầu tư (Mẫu I.1.1).",
        "priority": 3,
    },
    # ── Mẫu I.1.2 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_2",
        "form_code": "I.1.2",
        "name": "Đề xuất dự án đầu tư (do cơ quan có thẩm quyền lập)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "chap_thuan_chu_truong",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu đề xuất dự án đầu tư do cơ quan có thẩm quyền lập, áp dụng cho các dự án thuộc diện chấp thuận chủ trương đầu tư do Thủ tướng hoặc UBND cấp tỉnh quyết định. Bao gồm thông tin nhà đầu tư, quy mô, vốn, địa điểm, tiến độ thực hiện.",
        "key_clauses": ["Thông tin nhà đầu tư", "Mục tiêu và quy mô dự án", "Vốn đầu tư và nguồn vốn", "Địa điểm thực hiện", "Tiến độ triển khai"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 31", "Nghị định 96/2026/NĐ-CP — Điều 33", "TT55/2026/TT-BTC"],
        "download_hint": "Dùng cho dự án thuộc diện chấp thuận chủ trương đầu tư, do cơ quan nhà nước lập đề xuất.",
        "priority": 2,
    },
    # ── Mẫu I.1.3 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_3",
        "form_code": "I.1.3",
        "name": "Đề xuất dự án đầu tư (do nhà đầu tư lập)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "chap_thuan_chu_truong",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu đề xuất dự án đầu tư do nhà đầu tư (cá nhân hoặc tổ chức) lập, nộp cho cơ quan đăng ký đầu tư để xem xét chấp thuận chủ trương đầu tư. Ghi rõ mục tiêu, vốn, quy mô, tiến độ và tác động môi trường.",
        "key_clauses": ["Thông tin nhà đầu tư (cá nhân/tổ chức)", "Mục tiêu, phạm vi dự án", "Vốn đầu tư, cơ cấu nguồn vốn", "Diện tích sử dụng đất", "Nhu cầu lao động", "Đánh giá sơ bộ tác động môi trường"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 32, 33", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Nhà đầu tư cá nhân hoặc tổ chức sử dụng mẫu này khi nộp hồ sơ đề nghị chấp thuận chủ trương đầu tư.",
        "priority": 1,
    },
    # ── Mẫu I.1.4 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_4",
        "form_code": "I.1.4",
        "name": "Văn bản đề nghị chấp thuận nhà đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "chap_thuan_nha_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản nhà đầu tư gửi cơ quan nhà nước đề nghị được chấp thuận là nhà đầu tư thực hiện dự án đầu tư. Áp dụng khi dự án không thuộc diện đấu thầu lựa chọn nhà đầu tư. Khai báo năng lực tài chính, kinh nghiệm và phương án thực hiện dự án.",
        "key_clauses": ["Thông tin nhà đầu tư", "Năng lực tài chính (vốn chủ sở hữu, nguồn huy động)", "Kinh nghiệm dự án tương tự", "Phương án thực hiện dự án", "Cam kết đáp ứng điều kiện đầu tư"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 31, 38", "Nghị định 96/2026/NĐ-CP — Điều 31, 38", "TT55/2026/TT-BTC"],
        "download_hint": "Dùng khi dự án thuộc diện chấp thuận nhà đầu tư mà không qua đấu thầu. Nộp kèm hồ sơ năng lực.",
        "priority": 1,
    },
    # ── Mẫu I.1.5 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_5",
        "form_code": "I.1.5",
        "name": "Văn bản đề nghị cấp Giấy chứng nhận đăng ký đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "cap_gcn_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản nhà đầu tư nộp để xin cấp Giấy chứng nhận đăng ký đầu tư (GCN ĐKĐT). Áp dụng khi dự án phải đăng ký đầu tư theo quy định. Khai báo đầy đủ thông tin dự án để được cấp mã số dự án.",
        "key_clauses": ["Thông tin nhà đầu tư (tên, địa chỉ, MST/CMND)", "Tên dự án và mục tiêu", "Địa điểm thực hiện dự án", "Vốn đầu tư và tiến độ góp vốn", "Thời hạn hoạt động dự án", "Lao động dự kiến"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 37, 38", "Nghị định 96/2026/NĐ-CP — Điều 37", "TT55/2026/TT-BTC"],
        "download_hint": "Nộp tại Cơ quan đăng ký đầu tư (Sở KH&ĐT hoặc Ban Quản lý KCN). Thời hạn xử lý: 15 ngày làm việc.",
        "priority": 1,
    },
    # ── Mẫu I.1.7 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_7",
        "form_code": "I.1.7",
        "name": "Văn bản đề nghị cập nhật thông tin địa điểm dự án (sắp xếp đơn vị hành chính)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "dieu_chinh_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản nhà đầu tư đề nghị cập nhật thông tin địa điểm thực hiện dự án trên Giấy chứng nhận đăng ký đầu tư do thay đổi địa giới hành chính theo sắp xếp đơn vị hành chính và tổ chức chính quyền địa phương hai cấp.",
        "key_clauses": ["Thông tin dự án (mã số, tên)", "Địa điểm cũ và địa điểm mới sau sắp xếp", "Căn cứ pháp lý thay đổi địa giới", "Cam kết thông tin chính xác"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Dùng khi địa điểm dự án thay đổi do sắp xếp đơn vị hành chính (không phải do nhà đầu tư chủ động điều chỉnh).",
        "priority": 2,
    },
    # ── Mẫu I.1.8 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_8",
        "form_code": "I.1.8",
        "name": "Văn bản đề nghị điều chỉnh dự án đầu tư (điều chỉnh chung)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "dieu_chinh_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản nhà đầu tư nộp để xin điều chỉnh các nội dung của dự án đầu tư đã được chấp thuận hoặc đăng ký, trong trường hợp điều chỉnh chung (không thuộc các trường hợp đặc thù). Áp dụng cho điều chỉnh vốn, tiến độ, quy mô, mục tiêu dự án.",
        "key_clauses": ["Nội dung điều chỉnh (vốn/tiến độ/quy mô/mục tiêu)", "Lý do điều chỉnh", "So sánh nội dung trước và sau điều chỉnh", "Phương án thực hiện sau điều chỉnh"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 41", "Nghị định 96/2026/NĐ-CP — Điều 48, 52, 53, 54", "TT55/2026/TT-BTC"],
        "download_hint": "Mẫu điều chỉnh chung, dùng khi không thuộc các trường hợp chuyển nhượng, chia tách, góp vốn bằng đất.",
        "priority": 1,
    },
    # ── Mẫu I.1.8.a ──────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_8a",
        "form_code": "I.1.8.a",
        "name": "Văn bản đề nghị điều chỉnh dự án — chuyển nhượng một phần hoặc toàn bộ dự án",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "chuyen_nhuong_du_an",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản đề nghị điều chỉnh Giấy chứng nhận đăng ký đầu tư trong trường hợp nhà đầu tư chuyển nhượng một phần hoặc toàn bộ dự án đầu tư cho nhà đầu tư khác. Khai báo thông tin bên chuyển nhượng, bên nhận chuyển nhượng và giá trị chuyển nhượng.",
        "key_clauses": ["Thông tin bên chuyển nhượng và bên nhận chuyển nhượng", "Phần dự án được chuyển nhượng", "Giá trị chuyển nhượng", "Cam kết tiếp tục thực hiện dự án"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 44", "Nghị định 96/2026/NĐ-CP — Điều 57", "TT55/2026/TT-BTC"],
        "download_hint": "Nộp kèm hợp đồng chuyển nhượng dự án và các tài liệu về năng lực của bên nhận chuyển nhượng.",
        "priority": 1,
    },
    # ── Mẫu I.1.8.b ──────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_8b",
        "form_code": "I.1.8.b",
        "name": "Văn bản đề nghị điều chỉnh dự án — nhà đầu tư nhận chuyển nhượng tài sản bảo đảm",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "chuyen_nhuong_du_an",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản đề nghị điều chỉnh khi nhà đầu tư nhận chuyển nhượng dự án đầu tư là tài sản bảo đảm của khoản vay (nhà đầu tư mới tiếp nhận dự án từ ngân hàng hoặc tổ chức tín dụng xử lý tài sản bảo đảm).",
        "key_clauses": ["Thông tin dự án và tài sản bảo đảm", "Thông tin tổ chức tín dụng xử lý tài sản", "Thông tin nhà đầu tư nhận chuyển nhượng", "Phương án tiếp tục thực hiện dự án"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 44", "Nghị định 96/2026/NĐ-CP — Điều 57", "TT55/2026/TT-BTC"],
        "download_hint": "Áp dụng khi nhà đầu tư nhận dự án từ ngân hàng/tổ chức tín dụng xử lý tài sản bảo đảm.",
        "priority": 2,
    },
    # ── Mẫu I.1.8.d ──────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_8d",
        "form_code": "I.1.8.d",
        "name": "Văn bản đề nghị điều chỉnh dự án — chia, tách, hợp nhất, sáp nhập tổ chức kinh tế",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "to_chuc_lai_doanh_nghiep",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản đề nghị điều chỉnh GCN đăng ký đầu tư khi tổ chức kinh tế thực hiện dự án trải qua chia, tách, hợp nhất, sáp nhập hoặc chuyển đổi loại hình, dẫn đến thay đổi chủ thể đứng tên dự án.",
        "key_clauses": ["Hình thức tổ chức lại (chia/tách/hợp nhất/sáp nhập/chuyển đổi)", "Tên tổ chức kinh tế trước và sau tổ chức lại", "Quyết định về tổ chức lại doanh nghiệp", "Phân bổ dự án cho tổ chức kinh tế tiếp nhận"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 44", "Luật Doanh nghiệp 2020 — Điều 192–207", "Nghị định 96/2026/NĐ-CP — Điều 59", "TT55/2026/TT-BTC"],
        "download_hint": "Dùng khi công ty bị chia, tách, hợp nhất hoặc sáp nhập và cần điều chỉnh thông tin nhà đầu tư trên GCN đầu tư.",
        "priority": 2,
    },
    # ── Mẫu I.1.8.e ──────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_8e",
        "form_code": "I.1.8.e",
        "name": "Văn bản đề nghị điều chỉnh dự án — góp vốn bằng quyền sử dụng đất thuộc dự án",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "gop_von_dat_dai",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản đề nghị điều chỉnh khi nhà đầu tư sử dụng quyền sử dụng đất hoặc tài sản gắn liền với đất thuộc dự án đầu tư để góp vốn vào doanh nghiệp khác, dẫn đến thay đổi quyền sở hữu tài sản trong dự án.",
        "key_clauses": ["Thông tin về phần đất/tài sản góp vốn", "Thông tin doanh nghiệp nhận vốn góp", "Giá trị góp vốn", "Tác động đến tiến độ và mục tiêu dự án"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Luật Đất đai 2024 — Điều 45", "Nghị định 96/2026/NĐ-CP — Điều 61", "TT55/2026/TT-BTC"],
        "download_hint": "Dùng khi góp vốn bằng QSDĐ thuộc dự án đầu tư vào doanh nghiệp khác.",
        "priority": 2,
    },
    # ── Mẫu I.1.8.g ──────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_8g",
        "form_code": "I.1.8.g",
        "name": "Văn bản đề nghị điều chỉnh dự án đầu tư (trường hợp khác)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "dieu_chinh_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu văn bản điều chỉnh dự án đầu tư cho các trường hợp đặc thù không thuộc các mẫu I.1.8.a đến I.1.8.f.",
        "key_clauses": ["Nội dung cần điều chỉnh", "Căn cứ pháp lý yêu cầu điều chỉnh", "Phương án thực hiện mới"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 41", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Dùng cho các trường hợp điều chỉnh dự án không thuộc các mẫu điều chỉnh đặc thù khác.",
        "priority": 3,
    },
    # ── Mẫu I.1.8.h ──────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_8h",
        "form_code": "I.1.8.h",
        "name": "Văn bản đề nghị điều chỉnh dự án — theo bản án, quyết định tòa án, trọng tài",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "dieu_chinh_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản đề nghị điều chỉnh GCN đăng ký đầu tư khi có bản án hoặc quyết định của tòa án, trọng tài có hiệu lực pháp luật yêu cầu thay đổi nhà đầu tư hoặc nội dung dự án.",
        "key_clauses": ["Tóm tắt nội dung bản án/quyết định trọng tài", "Nội dung điều chỉnh theo yêu cầu của bản án", "Nhà đầu tư mới (nếu có)", "Tiến độ thực hiện sau điều chỉnh"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Bộ luật Tố tụng Dân sự 2015", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Gửi kèm bản sao có xác nhận của bản án hoặc phán quyết trọng tài đã có hiệu lực.",
        "priority": 2,
    },
    # ── Mẫu I.1.9 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_9",
        "form_code": "I.1.9",
        "name": "Báo cáo tình hình thực hiện dự án đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "bao_cao_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Báo cáo định kỳ nhà đầu tư gửi cơ quan đăng ký đầu tư về tình hình triển khai dự án, tiến độ giải ngân vốn, kết quả sản xuất kinh doanh, và các khó khăn vướng mắc. Bắt buộc nộp trước khi điều chỉnh hoặc cấp lại GCN đầu tư.",
        "key_clauses": ["Tiến độ thực hiện dự án (% hoàn thành)", "Vốn đã giải ngân theo từng hạng mục", "Doanh thu, lợi nhuận, lao động", "Nghĩa vụ tài chính đã thực hiện", "Khó khăn và kiến nghị"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 72", "Nghị định 96/2026/NĐ-CP — Điều 39", "TT55/2026/TT-BTC"],
        "download_hint": "Bắt buộc nộp kèm hồ sơ điều chỉnh dự án. Nộp báo cáo định kỳ trước ngày 31/3 hàng năm.",
        "priority": 1,
    },
    # ── Mẫu I.1.10 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_10",
        "form_code": "I.1.10",
        "name": "Văn bản đề nghị gia hạn thời hạn hoạt động dự án đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "gia_han_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản nhà đầu tư gửi cơ quan đăng ký đầu tư để xin gia hạn thời hạn hoạt động của dự án khi GCN đăng ký đầu tư sắp hết hạn, nhưng dự án vẫn cần tiếp tục hoạt động.",
        "key_clauses": ["Thời hạn hoạt động hiện tại", "Thời gian xin gia hạn", "Lý do cần gia hạn", "Kết quả hoạt động đến thời điểm đề nghị", "Kế hoạch hoạt động tiếp theo"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 43", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Nộp trước khi GCN hết hạn ít nhất 6 tháng. Thời hạn gia hạn tối đa theo Luật Đầu tư.",
        "priority": 1,
    },
    # ── Mẫu I.1.11 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_11",
        "form_code": "I.1.11",
        "name": "Thông báo về việc tự quyết định ngừng hoạt động dự án",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "cham_dut_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Thông báo nhà đầu tư gửi cơ quan đăng ký đầu tư khi tự quyết định ngừng hoạt động dự án tạm thời (không phải chấm dứt hẳn). Khai báo lý do ngừng, thời hạn ngừng và kế hoạch tiếp tục.",
        "key_clauses": ["Tên dự án, mã số dự án", "Lý do ngừng hoạt động", "Thời gian ngừng hoạt động dự kiến", "Phương án bảo vệ tài sản trong thời gian ngừng"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 36", "Nghị định 96/2026/NĐ-CP — Điều 65", "TT55/2026/TT-BTC"],
        "download_hint": "Nộp trong vòng 5 ngày làm việc kể từ ngày quyết định ngừng hoạt động.",
        "priority": 2,
    },
    # ── Mẫu I.1.12 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_12",
        "form_code": "I.1.12",
        "name": "Thông báo về việc tự quyết định chấm dứt hoạt động dự án đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "cham_dut_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Thông báo nhà đầu tư gửi cơ quan đăng ký đầu tư khi quyết định chấm dứt hoàn toàn hoạt động dự án đầu tư trước thời hạn, theo ý chí chủ động của nhà đầu tư (không phải bị thu hồi).",
        "key_clauses": ["Tên và mã số dự án", "Lý do chấm dứt hoạt động", "Thời điểm chấm dứt hiệu lực", "Phương án thanh lý tài sản", "Nghĩa vụ tài chính còn lại"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 36", "Nghị định 96/2026/NĐ-CP — Điều 66", "TT55/2026/TT-BTC"],
        "download_hint": "Nộp tại cơ quan đăng ký đầu tư. Kèm theo tài liệu chứng minh đã hoàn thành nghĩa vụ tài chính.",
        "priority": 1,
    },
    # ── Mẫu I.1.13 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_13",
        "form_code": "I.1.13",
        "name": "Văn bản đăng ký góp vốn/mua cổ phần/mua phần vốn góp của nhà đầu tư nước ngoài",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "gop_von_nuoc_ngoai",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản nhà đầu tư nước ngoài nộp để đăng ký việc góp vốn, mua cổ phần hoặc mua phần vốn góp vào tổ chức kinh tế trong nước (M&A có yếu tố nước ngoài). Cần được cơ quan đăng ký đầu tư xem xét điều kiện trước khi thực hiện.",
        "key_clauses": ["Thông tin nhà đầu tư nước ngoài", "Tên tổ chức kinh tế nhận vốn góp", "Tỷ lệ vốn góp/cổ phần mua", "Điều kiện tiếp cận thị trường", "Nguồn vốn góp"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 46", "Nghị định 96/2026/NĐ-CP — Điều 69–71", "TT55/2026/TT-BTC"],
        "download_hint": "Bắt buộc với nhà đầu tư nước ngoài trước khi góp vốn/mua cổ phần vào DN Việt Nam. Thời hạn xử lý: 15 ngày.",
        "priority": 1,
    },
    # ── Mẫu I.1.14 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_14",
        "form_code": "I.1.14",
        "name": "Văn bản đăng ký thành lập văn phòng điều hành trong hợp đồng BCC",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "van_phong_dieu_hanh",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản nhà đầu tư nước ngoài nộp để đăng ký thành lập văn phòng điều hành tại Việt Nam trong khuôn khổ hợp đồng hợp tác kinh doanh (BCC — Business Cooperation Contract) mà không thành lập pháp nhân.",
        "key_clauses": ["Thông tin nhà đầu tư nước ngoài và hợp đồng BCC", "Địa điểm văn phòng điều hành", "Người đứng đầu văn phòng", "Phạm vi hoạt động của văn phòng"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 50", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Chỉ dùng cho nhà đầu tư nước ngoài tham gia hợp đồng BCC tại Việt Nam.",
        "priority": 2,
    },
    # ── Mẫu I.1.15 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_15",
        "form_code": "I.1.15",
        "name": "Văn bản đề nghị điều chỉnh Giấy chứng nhận đăng ký hoạt động văn phòng điều hành",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "van_phong_dieu_hanh",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản điều chỉnh Giấy chứng nhận đăng ký hoạt động văn phòng điều hành trong hợp đồng BCC, khi có thay đổi về địa điểm, người đứng đầu hoặc phạm vi hoạt động.",
        "key_clauses": ["Thông tin văn phòng điều hành hiện tại", "Nội dung cần điều chỉnh", "Lý do điều chỉnh"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Dùng khi có thay đổi thông tin văn phòng điều hành trong hợp đồng BCC.",
        "priority": 3,
    },
    # ── Mẫu I.1.17 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_17",
        "form_code": "I.1.17",
        "name": "Văn bản đề nghị cấp lại Giấy chứng nhận đăng ký đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "cap_lai_gcn_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản nhà đầu tư nộp để đề nghị cấp lại Giấy chứng nhận đăng ký đầu tư khi GCN bị mất, hư hỏng hoặc không còn sử dụng được, mà không có thay đổi nội dung dự án.",
        "key_clauses": ["Lý do cấp lại (mất/hư hỏng)", "Tình trạng GCN cũ", "Cam kết thông tin trên GCN cũ vẫn còn hiệu lực"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Nộp kèm GCN cũ nếu còn (trường hợp hư hỏng); hoặc đơn khai báo mất nếu bị mất.",
        "priority": 2,
    },
    # ── Mẫu I.1.18 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_18",
        "form_code": "I.1.18",
        "name": "Văn bản đề nghị hiệu đính thông tin Giấy chứng nhận đăng ký đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "hieu_dinh_gcn_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản nhà đầu tư nộp để yêu cầu hiệu đính (sửa lỗi) thông tin trên Giấy chứng nhận đăng ký đầu tư do sai sót kỹ thuật hoặc đánh máy từ phía cơ quan cấp, mà không thay đổi nội dung thực chất của dự án.",
        "key_clauses": ["Thông tin cần hiệu đính (sai sót gì)", "Thông tin đúng cần ghi", "Chứng minh sai sót do cơ quan cấp"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Chỉ dùng khi GCN có lỗi kỹ thuật từ cơ quan cấp, không dùng để thay đổi nội dung dự án.",
        "priority": 3,
    },
    # ── Mẫu I.1.19 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_19",
        "form_code": "I.1.19",
        "name": "Văn bản đề nghị nộp lại Giấy chứng nhận đăng ký đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "cap_lai_gcn_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản nhà đầu tư nộp lại GCN đăng ký đầu tư cho cơ quan cấp, trong các trường hợp pháp luật yêu cầu nộp lại (ví dụ khi dự án chấm dứt hoặc thu hồi).",
        "key_clauses": ["Lý do nộp lại GCN", "Tình trạng dự án tại thời điểm nộp lại"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Nộp kèm GCN bản gốc.",
        "priority": 3,
    },
    # ── Mẫu I.1.20 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_20",
        "form_code": "I.1.20",
        "name": "Văn bản đề nghị đổi Giấy chứng nhận đăng ký đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "cap_lai_gcn_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản nhà đầu tư nộp để đổi Giấy chứng nhận đăng ký đầu tư sang mẫu mới (do thay đổi biểu mẫu GCN theo quy định pháp luật mới) mà không thay đổi nội dung dự án.",
        "key_clauses": ["Thông tin GCN cũ cần đổi", "Lý do đổi (thay đổi mẫu GCN theo quy định mới)"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Nộp kèm GCN cũ bản gốc.",
        "priority": 3,
    },
    # ── Mẫu I.1.21 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_1_21",
        "form_code": "I.1.21",
        "name": "Văn bản đề nghị áp dụng các biện pháp bảo đảm đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "bao_dam_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản nhà đầu tư gửi Nhà nước để yêu cầu áp dụng các biện pháp bảo đảm đầu tư theo quy định, khi có thay đổi pháp luật ảnh hưởng bất lợi đến quyền lợi hợp pháp của nhà đầu tư đã được ghi nhận trong GCN đầu tư.",
        "key_clauses": ["Nội dung quy định pháp luật thay đổi gây bất lợi", "Quyền lợi bị ảnh hưởng", "Yêu cầu biện pháp bảo đảm cụ thể", "Căn cứ pháp lý"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Chương IV (bảo đảm đầu tư)", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Dùng khi nhà nước thay đổi pháp luật gây bất lợi cho dự án đã được cấp GCN.",
        "priority": 2,
    },
    # ── Mẫu I.2.1 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_1",
        "form_code": "I.2.1",
        "name": "Quyết định chấp thuận chủ trương đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "quyet_dinh_chap_thuan",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Quyết định chấp thuận chủ trương đầu tư do cơ quan nhà nước có thẩm quyền ban hành (Thủ tướng Chính phủ hoặc Chủ tịch UBND cấp tỉnh), ghi nhận sự chấp thuận về chủ trương của dự án đầu tư trước khi thực hiện các thủ tục tiếp theo.",
        "key_clauses": ["Căn cứ pháp lý", "Tên và nội dung chủ yếu của dự án", "Nhà đầu tư được chấp thuận", "Địa điểm và quy mô dự án", "Điều kiện chấp thuận (nếu có)", "Thời hạn hiệu lực của quyết định"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 33–34", "Nghị định 96/2026/NĐ-CP — Điều 36, 52, 53", "TT55/2026/TT-BTC"],
        "download_hint": "Đây là quyết định do cơ quan nhà nước ban hành, nhà đầu tư nhận sau khi được chấp thuận chủ trương.",
        "priority": 1,
    },
    # ── Mẫu I.2.2 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_2",
        "form_code": "I.2.2",
        "name": "Quyết định chấp thuận điều chỉnh chủ trương đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "quyet_dinh_chap_thuan",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Quyết định của cơ quan nhà nước chấp thuận điều chỉnh chủ trương đầu tư, ban hành khi nhà đầu tư đã được chấp thuận chủ trương và nay xin điều chỉnh nội dung chủ yếu của dự án.",
        "key_clauses": ["Nội dung điều chỉnh so với quyết định chủ trương ban đầu", "Điều kiện điều chỉnh", "Hiệu lực điều chỉnh"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 35", "Nghị định 96/2026/NĐ-CP — Điều 52, 53", "TT55/2026/TT-BTC"],
        "download_hint": "Cơ quan nhà nước ban hành sau khi xem xét hồ sơ điều chỉnh chủ trương của nhà đầu tư.",
        "priority": 2,
    },
    # ── Mẫu I.2.3 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_3",
        "form_code": "I.2.3",
        "name": "Quyết định chấp thuận chủ trương đầu tư đồng thời với chấp thuận nhà đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "quyet_dinh_chap_thuan",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Quyết định kết hợp hai nội dung: vừa chấp thuận chủ trương đầu tư vừa chấp thuận nhà đầu tư cụ thể thực hiện dự án, áp dụng khi dự án chỉ định nhà đầu tư không qua đấu thầu.",
        "key_clauses": ["Chủ trương dự án được chấp thuận", "Nhà đầu tư được chỉ định thực hiện", "Điều kiện và cam kết của nhà đầu tư", "Thời hạn hiệu lực"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 33, 38", "Nghị định 96/2026/NĐ-CP — Điều 36", "TT55/2026/TT-BTC"],
        "download_hint": "Dùng cho dự án vừa cần chấp thuận chủ trương vừa chấp thuận nhà đầu tư (không qua đấu thầu).",
        "priority": 1,
    },
    # ── Mẫu I.2.4 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_4",
        "form_code": "I.2.4",
        "name": "Quyết định chấp thuận nhà đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "quyet_dinh_chap_thuan",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Quyết định của cơ quan nhà nước chính thức chấp thuận nhà đầu tư được thực hiện dự án, ban hành sau khi đã có quyết định chủ trương đầu tư. Là căn cứ để nhà đầu tư thực hiện các thủ tục tiếp theo.",
        "key_clauses": ["Nhà đầu tư được chấp thuận (tên, mã số thuế, địa chỉ)", "Dự án được giao thực hiện", "Các điều kiện nhà đầu tư phải đáp ứng", "Quyền và nghĩa vụ của nhà đầu tư"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 38", "Nghị định 96/2026/NĐ-CP — Điều 31, 38", "TT55/2026/TT-BTC"],
        "download_hint": "Cơ quan nhà nước ban hành sau khi xét duyệt hồ sơ chấp thuận nhà đầu tư.",
        "priority": 1,
    },
    # ── Mẫu I.2.5.a ──────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_5a",
        "form_code": "I.2.5.a",
        "name": "Quyết định chấp thuận điều chỉnh nhà đầu tư (trường hợp a)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "quyet_dinh_chap_thuan",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Quyết định chấp thuận điều chỉnh nhà đầu tư trong trường hợp đặc thù a (chuyển nhượng dự án, chia tách, hoặc thay đổi nhà đầu tư theo quy định).",
        "key_clauses": ["Nhà đầu tư mới được chấp thuận", "Nhà đầu tư cũ chuyển giao quyền", "Điều kiện chấp thuận điều chỉnh"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Cơ quan nhà nước ban hành khi chấp thuận thay đổi nhà đầu tư thực hiện dự án.",
        "priority": 2,
    },
    # ── Mẫu I.2.5.b ──────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_5b",
        "form_code": "I.2.5.b",
        "name": "Quyết định chấp thuận điều chỉnh nhà đầu tư (trường hợp b)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "quyet_dinh_chap_thuan",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Quyết định chấp thuận điều chỉnh nhà đầu tư trong trường hợp b (nhà đầu tư tiếp nhận dự án từ xử lý tài sản bảo đảm hoặc tổ chức lại doanh nghiệp).",
        "key_clauses": ["Nhà đầu tư mới và căn cứ tiếp nhận", "Nghĩa vụ nhà đầu tư mới kế thừa", "Hiệu lực điều chỉnh"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Cơ quan nhà nước ban hành khi chấp thuận điều chỉnh nhà đầu tư trong các trường hợp đặc thù.",
        "priority": 2,
    },
    # ── Mẫu I.2.6 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_6",
        "form_code": "I.2.6",
        "name": "Giấy chứng nhận đăng ký đầu tư (cấp mới)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "gcn_dang_ky_dau_tu",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Giấy chứng nhận đăng ký đầu tư (GCN ĐKĐT) do cơ quan đăng ký đầu tư cấp lần đầu cho dự án mới. Là tài liệu pháp lý chứng nhận dự án đầu tư, ghi rõ mã số dự án, nhà đầu tư, quy mô và các điều kiện thực hiện.",
        "key_clauses": ["Mã số dự án", "Tên và thông tin nhà đầu tư", "Tên dự án và mục tiêu", "Vốn đầu tư đã đăng ký", "Địa điểm thực hiện", "Thời hạn hoạt động", "Các điều kiện và ưu đãi đầu tư"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 37, 38", "Nghị định 96/2026/NĐ-CP — Điều 40", "TT55/2026/TT-BTC"],
        "download_hint": "GCN ĐKĐT do cơ quan nhà nước cấp, không phải nhà đầu tư tự lập. Nhà đầu tư nhận sau khi hồ sơ được xét duyệt.",
        "priority": 1,
    },
    # ── Mẫu I.2.7 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_7",
        "form_code": "I.2.7",
        "name": "Giấy chứng nhận đăng ký đầu tư (điều chỉnh)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "gcn_dang_ky_dau_tu",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu GCN đăng ký đầu tư điều chỉnh, cấp cho nhà đầu tư khi có thay đổi nội dung dự án đã được ghi nhận trong GCN cũ (điều chỉnh vốn, tiến độ, mục tiêu, nhà đầu tư, v.v.).",
        "key_clauses": ["Nội dung điều chỉnh so với GCN cũ", "Ngày cấp lần đầu và số lần điều chỉnh", "Nội dung còn nguyên vẹn"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 41–45", "Nghị định 96/2026/NĐ-CP — Mục 5 Chương IV", "TT55/2026/TT-BTC"],
        "download_hint": "GCN điều chỉnh do cơ quan nhà nước cấp sau khi chấp thuận hồ sơ điều chỉnh của nhà đầu tư.",
        "priority": 1,
    },
    # ── Mẫu I.2.8 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_8",
        "form_code": "I.2.8",
        "name": "Giấy chứng nhận đăng ký đầu tư (đổi, cấp lại, hiệu đính)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "gcn_dang_ky_dau_tu",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu GCN đăng ký đầu tư dùng cho trường hợp đổi mẫu, cấp lại (do mất/hư hỏng) hoặc hiệu đính thông tin sai sót kỹ thuật, không thay đổi nội dung thực chất của dự án.",
        "key_clauses": ["Lý do đổi/cấp lại/hiệu đính", "Nội dung được hiệu đính", "Số và ngày GCN cũ"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Cơ quan nhà nước cấp sau khi nhận đề nghị đổi/cấp lại/hiệu đính từ nhà đầu tư.",
        "priority": 2,
    },
    # ── Mẫu I.2.9 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_9",
        "form_code": "I.2.9",
        "name": "Văn bản thỏa thuận bảo đảm thực hiện dự án đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "bao_dam_dau_tu",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Văn bản thỏa thuận giữa cơ quan nhà nước và nhà đầu tư về nghĩa vụ bảo đảm thực hiện dự án (ký quỹ hoặc bảo lãnh ngân hàng), áp dụng cho dự án có sử dụng đất được Nhà nước giao, cho thuê.",
        "key_clauses": ["Giá trị bảo đảm và hình thức (ký quỹ/bảo lãnh)", "Thời hạn bảo đảm", "Điều kiện giải phóng nghĩa vụ bảo đảm", "Xử lý khi vi phạm cam kết tiến độ"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 26, 27", "Nghị định 96/2026/NĐ-CP — Điều 27", "TT55/2026/TT-BTC"],
        "download_hint": "Ký kết giữa Sở KH&ĐT (hoặc Ban Quản lý KCN) và nhà đầu tư trước khi bàn giao mặt bằng.",
        "priority": 1,
    },
    # ── Mẫu I.2.10 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_10",
        "form_code": "I.2.10",
        "name": "Giấy chứng nhận đăng ký hoạt động văn phòng điều hành (cấp mới)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "van_phong_dieu_hanh",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Giấy chứng nhận cơ quan nhà nước cấp cho nhà đầu tư nước ngoài được thành lập văn phòng điều hành tại Việt Nam trong khuôn khổ hợp đồng hợp tác kinh doanh BCC.",
        "key_clauses": ["Tên và địa điểm văn phòng", "Người đứng đầu văn phòng", "Phạm vi hoạt động", "Thời hạn hoạt động"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 50", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Cơ quan đăng ký đầu tư cấp sau khi xem xét hồ sơ đăng ký văn phòng điều hành.",
        "priority": 2,
    },
    # ── Mẫu I.2.11 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_11",
        "form_code": "I.2.11",
        "name": "Giấy chứng nhận điều chỉnh đăng ký hoạt động văn phòng điều hành",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "van_phong_dieu_hanh",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Giấy chứng nhận điều chỉnh thông tin văn phòng điều hành BCC, cấp khi có thay đổi về địa điểm, người đứng đầu hoặc phạm vi hoạt động.",
        "key_clauses": ["Nội dung điều chỉnh", "Giấy chứng nhận cũ cần điều chỉnh"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Cơ quan nhà nước cấp sau khi xem xét hồ sơ điều chỉnh văn phòng điều hành.",
        "priority": 3,
    },
    # ── Mẫu I.2.12 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_12",
        "form_code": "I.2.12",
        "name": "Quyết định thu hồi Giấy chứng nhận đăng ký hoạt động văn phòng điều hành",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "thu_hoi_gcn",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Quyết định cơ quan nhà nước ban hành để thu hồi Giấy chứng nhận đăng ký hoạt động văn phòng điều hành trong hợp đồng BCC khi hợp đồng BCC chấm dứt hoặc vi phạm quy định pháp luật.",
        "key_clauses": ["Lý do thu hồi", "Thời điểm thu hồi có hiệu lực", "Nghĩa vụ của nhà đầu tư sau khi bị thu hồi"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Quyết định do cơ quan đăng ký đầu tư ban hành, nhà đầu tư nhận sau khi văn phòng bị thu hồi GCN.",
        "priority": 2,
    },
    # ── Mẫu I.2.14 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_14",
        "form_code": "I.2.14",
        "name": "Quyết định ngừng hoạt động dự án đầu tư (do cơ quan nhà nước quyết định)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "ngung_hoat_dong_du_an",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Quyết định cơ quan quản lý nhà nước về đầu tư ban hành để yêu cầu ngừng hoạt động dự án đầu tư khi phát hiện vi phạm pháp luật hoặc không đáp ứng điều kiện tiếp tục hoạt động.",
        "key_clauses": ["Lý do ngừng hoạt động", "Phạm vi ngừng (toàn bộ/một phần)", "Thời hạn ngừng", "Các biện pháp nhà đầu tư phải thực hiện", "Điều kiện khôi phục hoạt động"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 36", "Nghị định 96/2026/NĐ-CP — Điều 65", "TT55/2026/TT-BTC"],
        "download_hint": "Quyết định hành chính, nhà đầu tư có quyền khiếu nại trong 30 ngày kể từ ngày nhận.",
        "priority": 1,
    },
    # ── Mẫu I.2.15 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_15",
        "form_code": "I.2.15",
        "name": "Quyết định ngừng toàn bộ hoặc một phần hoạt động dự án (do Thủ tướng quyết định)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "ngung_hoat_dong_du_an",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Quyết định Thủ tướng Chính phủ ban hành để ngừng toàn bộ hoặc một phần hoạt động của dự án đầu tư quan trọng, ảnh hưởng đến an ninh quốc gia hoặc lợi ích công cộng.",
        "key_clauses": ["Dự án bị ngừng và lý do", "Phạm vi ngừng", "Thời hạn", "Giải pháp hỗ trợ nhà đầu tư"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 36", "Nghị định 96/2026/NĐ-CP — Điều 65", "TT55/2026/TT-BTC"],
        "download_hint": "Quyết định của Thủ tướng, áp dụng cho dự án quan trọng quốc gia.",
        "priority": 2,
    },
    # ── Mẫu I.2.16 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_16",
        "form_code": "I.2.16",
        "name": "Thông báo chấm dứt toàn bộ hoạt động dự án đầu tư (theo đề nghị của nhà đầu tư)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "cham_dut_dau_tu",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Thông báo cơ quan đăng ký đầu tư gửi nhà đầu tư xác nhận việc chấm dứt hoạt động dự án theo đề nghị của chính nhà đầu tư (nhà đầu tư tự nguyện chấm dứt và cơ quan xác nhận).",
        "key_clauses": ["Xác nhận việc chấm dứt theo đề nghị nhà đầu tư", "Thời điểm chấm dứt", "Nghĩa vụ tài chính còn lại", "Thủ tục thu hồi GCN"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 36", "Nghị định 96/2026/NĐ-CP — Điều 66", "TT55/2026/TT-BTC"],
        "download_hint": "Cơ quan đăng ký đầu tư ban hành sau khi nhà đầu tư nộp thông báo tự chấm dứt (Mẫu I.1.12).",
        "priority": 1,
    },
    # ── Mẫu I.2.17 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_17",
        "form_code": "I.2.17",
        "name": "Quyết định chấm dứt toàn bộ hoạt động dự án đầu tư (khoản 2 Điều 36 Luật Đầu tư)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "cham_dut_dau_tu",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Quyết định cơ quan nhà nước ban hành chấm dứt hoàn toàn dự án đầu tư theo quy định tại khoản 2 Điều 36 Luật Đầu tư (do vi phạm pháp luật, hết thời hạn mà không được gia hạn, hoặc theo yêu cầu quốc phòng - an ninh).",
        "key_clauses": ["Căn cứ pháp lý chấm dứt", "Hậu quả pháp lý và xử lý tài sản", "Thu hồi các quyền đất đai", "Bồi thường thiệt hại (nếu nhà nước quyết định)"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 36 khoản 2", "Nghị định 96/2026/NĐ-CP — Điều 66", "TT55/2026/TT-BTC"],
        "download_hint": "Quyết định hành chính buộc chấm dứt, nhà đầu tư có quyền khiếu nại hoặc khởi kiện hành chính.",
        "priority": 1,
    },
    # ── Mẫu I.2.18 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_18",
        "form_code": "I.2.18",
        "name": "Quyết định chấm dứt một phần hoạt động dự án đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "cham_dut_dau_tu",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Quyết định cơ quan nhà nước ban hành chấm dứt một phần hoạt động của dự án đầu tư (các hạng mục không thực hiện được), trong khi các hạng mục khác vẫn tiếp tục.",
        "key_clauses": ["Phần dự án bị chấm dứt", "Phần dự án còn tiếp tục", "Điều chỉnh GCN tương ứng"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 36", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Quyết định của cơ quan đăng ký đầu tư khi chấm dứt một phần dự án.",
        "priority": 2,
    },
    # ── Mẫu I.2.19 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_19",
        "form_code": "I.2.19",
        "name": "Biên bản xác nhận tình hình dự án (căn cứ xem xét ngừng/chấm dứt hoạt động)",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "xac_nhan_du_an",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Biên bản do cơ quan đăng ký đầu tư lập, ghi nhận tình hình thực tế của dự án tại thời điểm kiểm tra, làm căn cứ xem xét việc ngừng hoặc chấm dứt hoạt động dự án theo quy định.",
        "key_clauses": ["Tình hình thực hiện dự án tại thời điểm kiểm tra", "Vi phạm phát hiện (nếu có)", "Kiến nghị của cơ quan kiểm tra", "Ý kiến phản hồi của nhà đầu tư"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 36", "Nghị định 96/2026/NĐ-CP — Điều 65, 66, 67", "TT55/2026/TT-BTC"],
        "download_hint": "Cơ quan đăng ký đầu tư lập khi tiến hành kiểm tra dự án trước khi ra quyết định ngừng/chấm dứt.",
        "priority": 2,
    },
    # ── Mẫu I.2.20 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_20",
        "form_code": "I.2.20",
        "name": "Thông báo đáp ứng điều kiện góp vốn/mua cổ phần/mua phần vốn góp của nhà đầu tư nước ngoài",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "gop_von_nuoc_ngoai",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Thông báo của cơ quan đăng ký đầu tư gửi nhà đầu tư nước ngoài, xác nhận việc góp vốn/mua cổ phần/mua phần vốn góp đáp ứng các điều kiện pháp lý và được phép thực hiện.",
        "key_clauses": ["Xác nhận đáp ứng điều kiện", "Tỷ lệ vốn nước ngoài được phép", "Các điều kiện kèm theo (nếu có)"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 46", "Nghị định 96/2026/NĐ-CP — Điều 70–71", "TT55/2026/TT-BTC"],
        "download_hint": "Nhà đầu tư nước ngoài nhận thông báo này từ cơ quan đăng ký đầu tư trước khi thực hiện giao dịch M&A.",
        "priority": 1,
    },
    # ── Mẫu I.2.21 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_21",
        "form_code": "I.2.21",
        "name": "Văn bản đề nghị đăng tải thông báo trên Cổng thông tin quốc gia về đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "cong_bo_thong_tin",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Văn bản cơ quan đăng ký đầu tư gửi Cổng thông tin quốc gia về đầu tư để đăng tải các thông báo về dự án đầu tư (chấp thuận, điều chỉnh, chấm dứt...) công khai theo yêu cầu pháp luật về minh bạch đầu tư.",
        "key_clauses": ["Nội dung cần đăng tải", "Loại thông báo (cấp mới/điều chỉnh/chấm dứt)", "Thông tin dự án để công khai"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Cơ quan đăng ký đầu tư dùng để thực hiện nghĩa vụ công khai thông tin dự án đầu tư.",
        "priority": 3,
    },
    # ── Mẫu I.2.22 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_22",
        "form_code": "I.2.22",
        "name": "Thông báo từ chối cấp/điều chỉnh Quyết định chấp thuận, GCN đăng ký đầu tư",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "tu_choi_dau_tu",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Thông báo cơ quan nhà nước gửi nhà đầu tư khi từ chối cấp, điều chỉnh Quyết định chấp thuận chủ trương đầu tư, Quyết định chấp thuận nhà đầu tư, Giấy chứng nhận đăng ký đầu tư hoặc các văn bản hành chính khác về đầu tư. Phải nêu rõ lý do từ chối.",
        "key_clauses": ["Loại văn bản bị từ chối cấp/điều chỉnh", "Lý do từ chối (không đáp ứng điều kiện nào)", "Hướng dẫn nhà đầu tư bổ sung hồ sơ hoặc quyền khiếu nại"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Nghị định 96/2026/NĐ-CP", "Luật Khiếu nại 2011", "TT55/2026/TT-BTC"],
        "download_hint": "Nhà đầu tư có quyền khiếu nại hoặc khởi kiện hành chính trong 30 ngày kể từ ngày nhận thông báo từ chối.",
        "priority": 1,
    },
    # ── Mẫu I.2.24 ───────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_2_24",
        "form_code": "I.2.24",
        "name": "Giấy biên nhận hồ sơ",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "ho_so_dau_tu",
        "issuer": "co_quan_nha_nuoc",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu Giấy biên nhận hồ sơ do cơ quan đăng ký đầu tư cấp cho nhà đầu tư khi tiếp nhận hồ sơ đề nghị thực hiện các thủ tục đầu tư, ghi nhận ngày tiếp nhận, danh mục tài liệu và thời hạn xử lý.",
        "key_clauses": ["Danh mục hồ sơ đã tiếp nhận", "Ngày tiếp nhận", "Thời hạn xử lý", "Người tiếp nhận"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15", "Luật Thủ tục hành chính 2015", "Nghị định 96/2026/NĐ-CP", "TT55/2026/TT-BTC"],
        "download_hint": "Cơ quan đăng ký đầu tư cấp ngay khi tiếp nhận hồ sơ. Nhà đầu tư lưu để theo dõi tiến độ xử lý.",
        "priority": 2,
    },
    # ── Mẫu I.3.1 ────────────────────────────────────────────────────────────
    {
        "template_id": "tt55_I_3_1",
        "form_code": "I.3.1",
        "name": "Báo cáo tình hình thực hiện dự án đầu tư quý/năm",
        "template_type": "official_form",
        "industry": "dau_tu",
        "contract_type": "bao_cao_dau_tu",
        "issuer": "nha_dau_tu",
        "source_document": "TT55/2026/TT-BTC",
        "description": "Mẫu báo cáo định kỳ hàng quý và hàng năm nhà đầu tư gửi cơ quan đăng ký đầu tư về tình hình thực hiện dự án, bao gồm vốn đã giải ngân, doanh thu, lợi nhuận, số lao động, nghĩa vụ thuế và các vấn đề phát sinh.",
        "key_clauses": ["Vốn giải ngân trong kỳ và lũy kế", "Doanh thu và lợi nhuận trong kỳ", "Số lao động Việt Nam và nước ngoài", "Nghĩa vụ thuế đã nộp", "Tiến độ thực hiện và dự kiến", "Khó khăn, vướng mắc và kiến nghị"],
        "related_laws": ["Luật Đầu tư 143/2025/QH15 — Điều 72", "Nghị định 96/2026/NĐ-CP — Điều 76", "TT55/2026/TT-BTC"],
        "download_hint": "Nộp báo cáo quý trước ngày 15 của tháng đầu quý tiếp theo; báo cáo năm trước ngày 31/3 năm sau.",
        "priority": 1,
    },
]


# ---------------------------------------------------------------------------
# Seed runner
# ---------------------------------------------------------------------------


def seed_all(vector_storage: VectorStorage) -> dict:
    """
    Insert all templates, risks, checklists, legal cases, and official forms into MongoDB.
    Generates embeddings for vector search.
    Safe to re-run (upsert semantics). Returns counts dict.
    """
    logger.info("seed_data: seeding templates …")
    _seed_templates(vector_storage)

    logger.info("seed_data: seeding official forms (TT55/2026/TT-BTC) …")
    _seed_official_forms(vector_storage)

    logger.info("seed_data: seeding risks …")
    _seed_risks(vector_storage)

    logger.info("seed_data: seeding checklists …")
    _seed_checklists(vector_storage)

    logger.info("seed_data: seeding legal cases …")
    _seed_legal_cases(vector_storage)

    logger.info("seed_data: seeding user behavior interactions …")
    _seed_interactions(vector_storage)

    logger.info("seed_data: done.")
    return {
        "templates": len(_TEMPLATES),
        "official_forms": len(_OFFICIAL_FORMS),
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


def _seed_official_forms(vs: VectorStorage) -> None:
    for form in _OFFICIAL_FORMS:
        embed_text_for = form["name"] + " " + form["description"] + " " + " ".join(form["key_clauses"])
        emb = embed_text(embed_text_for)
        doc = dict(form)
        if emb:
            doc["embedding"] = emb
        vs.upsert_template(doc)
    logger.info("seed_data: %d official forms upserted.", len(_OFFICIAL_FORMS))


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


def _seed_interactions(vs: VectorStorage) -> None:
    from datetime import datetime, timedelta, timezone
    import random
    
    # Check if interactions already seeded to avoid duplication
    if vs.interactions.count_documents({"user_id": "demo_user_001"}) > 0:
        logger.info("seed_data: interactions already seeded.")
        return
        
    now = datetime.now(timezone.utc)
    
    # Seed 24 realistic interactions over the last 12 days
    actions = [
        ("situation_analysis", "dat_dai", "Tra cứu lấn chiếm đất đai xây dựng trái phép"),
        ("situation_analysis", "hop_dong", "Soát xét hợp đồng thuê nhà xưởng"),
        ("situation_analysis", "lao_dong", "Tranh chấp sa thải người lao động trái luật"),
        ("nba_click", "dat_dai", "Xem vụ việc tương tự tranh chấp đất đai"),
        ("nba_click", "hop_dong", "Phân tích điều khoản rủi ro hợp đồng"),
        ("view", "dat_dai", "Xem điều luật đất đai liên quan"),
        ("view", "hop_dong", "Xem mẫu hợp đồng thuê văn phòng"),
        ("download", "lao_dong", "Tải đơn khiếu nại lao động"),
        ("save", "dan_su", "Lưu kết quả phân tích tranh chấp dân sự"),
    ]
    
    seeded = 0
    for day in range(12, 0, -1):
        # 1-3 interactions per day to make active days look beautiful
        for i in range(random.randint(1, 3)):
            act, domain, snippet = random.choice(actions)
            ts = now - timedelta(days=day, hours=random.randint(1, 20), minutes=random.randint(1, 59))
            
            vs.interactions.insert_one({
                "user_id": "demo_user_001",
                "doc_id": f"doc_demo_{random.randint(100, 999)}",
                "action_type": act,
                "context": {
                    "law_type": domain,
                    "situation_snippet": snippet
                },
                "chunk_id": f"chunk_demo_{random.randint(1000, 9999)}",
                "timestamp": ts.isoformat()
            })
            seeded += 1
            
    logger.info("seed_data: %d user interactions seeded.", seeded)


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
