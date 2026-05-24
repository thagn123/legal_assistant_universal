import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const workbook = Workbook.create();

const employees = [
  { name: "Nguyễn Văn Hưng", role: "Manager", title: "Finance Manager" },
  { name: "Trần Thị Mai", role: "Senior", title: "Contract Lead" },
  { name: "Phạm Quốc Bảo", role: "Manager", title: "Operations Manager" },
  { name: "Đỗ Thu Hà", role: "Senior", title: "Senior Accountant" },
  { name: "Vũ Minh Khoa", role: "Senior", title: "Project Controls Senior" },
  { name: "Lê Minh Anh", role: "Intern", title: "Finance Intern" },
  { name: "Phạm Gia Huy", role: "Intern", title: "Contract Intern" },
  { name: "Ngô Thảo Vy", role: "Intern", title: "Accounting Intern" },
  { name: "Hoàng Đức Nam", role: "Intern", title: "Admin Intern" },
  { name: "Bùi Khánh Linh", role: "Intern", title: "Reporting Intern" },
];

const d = (iso) => {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
};

const taskPlanHeaders = [
  "Task ID",
  "Date",
  "Employee Name",
  "Role (Intern / Senior / Manager)",
  "Task Name",
  "Task Category (Contract / Finance / Reporting / Admin / Audit)",
  "Priority (High/Medium/Low)",
  "Estimated Time (hours)",
  "Status (Not Started / In Progress / Done / Blocked)",
  "Assigned By",
  "Notes",
];

const tasks = [
  ["DP-001", d("2026-05-18"), "Trần Thị Mai", "Senior", "Rà soát điều khoản thanh toán Hợp đồng thi công Khu A", "Contract", "High", 2.5, "Done", "Phạm Quốc Bảo", "Ưu tiên điều khoản tạm ứng và bảo lãnh thực hiện hợp đồng"],
  ["DP-002", d("2026-05-18"), "Phạm Gia Huy", "Intern", "Định dạng lại phụ lục khối lượng phát sinh dự án Riverside", "Contract", "Medium", 2, "Done", "Trần Thị Mai", "Dùng template hợp đồng phiên bản 2026"],
  ["DP-003", d("2026-05-18"), "Lê Minh Anh", "Intern", "Phân loại báo cáo chi phí vật liệu tuần 20 theo công trình", "Finance", "High", 3, "Done", "Nguyễn Văn Hưng", "Tách xi măng, thép, cát đá và vật tư phụ"],
  ["DP-004", d("2026-05-18"), "Ngô Thảo Vy", "Intern", "Nhập hóa đơn xi măng và thép vào file kế toán nội bộ", "Finance", "Medium", 3.5, "In Progress", "Đỗ Thu Hà", "Cần kiểm tra lại mã nhà cung cấp"],
  ["DP-005", d("2026-05-18"), "Hoàng Đức Nam", "Intern", "Scan bộ hồ sơ nghiệm thu hạng mục móng Nhà xưởng Bình Dương", "Admin", "Low", 2, "Done", "Vũ Minh Khoa", "Đặt tên file theo mã dự án BD-FA-2026"],
  ["DP-006", d("2026-05-18"), "Bùi Khánh Linh", "Intern", "Tổng hợp báo cáo tài chính tuần gửi Finance Manager", "Reporting", "High", 3, "In Progress", "Nguyễn Văn Hưng", "Chờ số liệu công nợ cuối ngày"],
  ["DP-007", d("2026-05-18"), "Đỗ Thu Hà", "Senior", "Kiểm tra chứng từ ngân hàng khoản tạm ứng công trình Long Thành", "Audit", "High", 2, "Done", "Nguyễn Văn Hưng", "Đối chiếu sao kê VPBank và phiếu chi"],
  ["DP-008", d("2026-05-18"), "Vũ Minh Khoa", "Senior", "Đối soát khối lượng nghiệm thu với nhật ký công trường dự án Khu B", "Audit", "High", 3, "Blocked", "Phạm Quốc Bảo", "Thiếu nhật ký ngày 16/05 từ đội thi công"],
  ["DP-009", d("2026-05-18"), "Nguyễn Văn Hưng", "Manager", "Phê duyệt lịch thanh toán nhà thầu điện M&E đợt 2", "Finance", "High", 1.5, "Done", "Phạm Quốc Bảo", "Giữ lại 5% theo điều khoản bảo hành"],
  ["DP-010", d("2026-05-19"), "Phạm Quốc Bảo", "Manager", "Lập kế hoạch ưu tiên hồ sơ hợp đồng và thanh toán trong tuần", "Admin", "High", 1.5, "Done", "Nguyễn Văn Hưng", "Chốt thứ tự xử lý trước 10:00"],
  ["DP-011", d("2026-05-19"), "Lê Minh Anh", "Intern", "Tạo lệnh chuyển tiền cho nhà thầu cốt pha An Phú", "Finance", "High", 1.5, "In Progress", "Nguyễn Văn Hưng", "Cần xác nhận số tài khoản mới"],
  ["DP-012", d("2026-05-19"), "Phạm Gia Huy", "Intern", "Soát lỗi chính tả và mã điều khoản trong hợp đồng nhà thầu phụ PCCC", "Contract", "Medium", 2.5, "Done", "Trần Thị Mai", "Dùng track changes khi chỉnh sửa"],
  ["DP-013", d("2026-05-19"), "Ngô Thảo Vy", "Intern", "Đối chiếu hóa đơn vật liệu với bảng nhập kho dự án Riverside", "Finance", "High", 3, "Blocked", "Đỗ Thu Hà", "Thiếu phiếu nhập kho lô thép Hòa Phát"],
  ["DP-014", d("2026-05-19"), "Hoàng Đức Nam", "Intern", "Chuẩn hóa thư mục chứng từ ngân hàng tháng 05", "Admin", "Medium", 2, "In Progress", "Đỗ Thu Hà", "Sắp xếp theo ngày giao dịch và mã công trình"],
  ["DP-015", d("2026-05-19"), "Bùi Khánh Linh", "Intern", "Cập nhật dashboard tiến độ chi phí vật liệu theo dự án", "Reporting", "Medium", 3, "Not Started", "Vũ Minh Khoa", "Nguồn dữ liệu từ file Cost_Tracking_May"],
  ["DP-016", d("2026-05-19"), "Trần Thị Mai", "Senior", "Review phụ lục gia hạn tiến độ công trình Long Thành", "Contract", "High", 2, "In Progress", "Phạm Quốc Bảo", "Cần bổ sung căn cứ pháp lý về thời tiết"],
  ["DP-017", d("2026-05-19"), "Đỗ Thu Hà", "Senior", "Kiểm tra bảng phân bổ chi phí nhân công công trường", "Finance", "Medium", 2.5, "Done", "Nguyễn Văn Hưng", "Đối chiếu với bảng chấm công đội thi công"],
  ["DP-018", d("2026-05-19"), "Vũ Minh Khoa", "Senior", "Tổng hợp rủi ro lệch dự toán vật liệu quý II", "Reporting", "High", 3.5, "In Progress", "Phạm Quốc Bảo", "Đánh dấu các hạng mục vượt trên 8%"],
  ["DP-019", d("2026-05-19"), "Nguyễn Văn Hưng", "Manager", "Duyệt hạn mức thanh toán tuần cho nhóm Finance Ops", "Finance", "High", 1, "Done", "Phạm Quốc Bảo", "Ưu tiên khoản đến hạn trong 3 ngày"],
  ["DP-020", d("2026-05-20"), "Lê Minh Anh", "Intern", "Đối soát công nợ nhà cung cấp Sơn Nam", "Finance", "High", 3, "Not Started", "Đỗ Thu Hà", "Đánh dấu chênh lệch trên 500.000 VND"],
  ["DP-021", d("2026-05-20"), "Phạm Gia Huy", "Intern", "Chuẩn hóa bảng so sánh phiên bản hợp đồng PCCC", "Contract", "Medium", 2, "Not Started", "Trần Thị Mai", "Tách thay đổi giá trị và tiến độ"],
  ["DP-022", d("2026-05-20"), "Ngô Thảo Vy", "Intern", "Nhập dữ liệu hóa đơn thuê máy móc vào master accounting file", "Finance", "Medium", 3, "Not Started", "Đỗ Thu Hà", "Kiểm tra MST trước khi nhập"],
  ["DP-023", d("2026-05-20"), "Hoàng Đức Nam", "Intern", "Scan và gộp PDF biên bản bàn giao vật tư", "Admin", "Low", 2, "Not Started", "Vũ Minh Khoa", "Một file PDF cho mỗi ngày bàn giao"],
  ["DP-024", d("2026-05-20"), "Bùi Khánh Linh", "Intern", "Lập bảng tóm tắt chi phí nhà thầu phụ theo dự án", "Reporting", "High", 3.5, "Not Started", "Nguyễn Văn Hưng", "Cần phân nhóm theo hợp đồng và hạng mục"],
  ["DP-025", d("2026-05-20"), "Trần Thị Mai", "Senior", "Kiểm tra rủi ro điều khoản phạt chậm tiến độ trong hợp đồng facade", "Contract", "High", 2.5, "Not Started", "Phạm Quốc Bảo", "So sánh với hợp đồng mẫu đã duyệt"],
  ["DP-026", d("2026-05-20"), "Đỗ Thu Hà", "Senior", "Review chứng từ thanh toán nhà thầu điện M&E đợt 2", "Audit", "High", 2, "Not Started", "Nguyễn Văn Hưng", "Kiểm tra hóa đơn VAT và biên bản nghiệm thu"],
  ["DP-027", d("2026-05-20"), "Vũ Minh Khoa", "Senior", "Đối chiếu tiến độ nghiệm thu với kế hoạch dòng tiền", "Reporting", "Medium", 2.5, "Not Started", "Phạm Quốc Bảo", "Cập nhật milestone tuần 20"],
  ["DP-028", d("2026-05-20"), "Phạm Quốc Bảo", "Manager", "Họp nhanh với Contract Lead về hợp đồng phát sinh", "Admin", "Medium", 1, "Not Started", "Nguyễn Văn Hưng", "Chuẩn bị danh sách issue trước cuộc họp"],
  ["DP-029", d("2026-05-21"), "Lê Minh Anh", "Intern", "Kiểm tra lệnh chuyển tiền sau khi ngân hàng xác nhận", "Audit", "High", 2, "Not Started", "Nguyễn Văn Hưng", "Lưu mã giao dịch vào payment log"],
  ["DP-030", d("2026-05-21"), "Phạm Gia Huy", "Intern", "Tổng hợp các điều khoản cần senior xác nhận trong hợp đồng facade", "Contract", "Medium", 2.5, "Not Started", "Trần Thị Mai", "Gắn link tới trang hợp đồng liên quan"],
  ["DP-031", d("2026-05-21"), "Ngô Thảo Vy", "Intern", "Đối chiếu dữ liệu thuế VAT với file hóa đơn đầu vào", "Finance", "High", 3, "Not Started", "Đỗ Thu Hà", "Lọc các hóa đơn chưa có mã tra cứu"],
  ["DP-032", d("2026-05-21"), "Hoàng Đức Nam", "Intern", "Tổng hợp danh mục hồ sơ còn thiếu cho kiểm toán nội bộ", "Audit", "Medium", 3, "Not Started", "Đỗ Thu Hà", "Ưu tiên hồ sơ thanh toán trên 200 triệu"],
  ["DP-033", d("2026-05-21"), "Bùi Khánh Linh", "Intern", "Chuẩn hóa file Excel báo cáo chi phí theo mẫu mới", "Reporting", "Medium", 2.5, "Not Started", "Vũ Minh Khoa", "Không đổi tên sheet nguồn"],
  ["DP-034", d("2026-05-21"), "Trần Thị Mai", "Senior", "Review hợp đồng bảo trì thiết bị công trường", "Contract", "Medium", 2, "Not Started", "Phạm Quốc Bảo", "Chú ý điều khoản thời gian phản hồi sự cố"],
  ["DP-035", d("2026-05-21"), "Đỗ Thu Hà", "Senior", "Kiểm tra đối ứng tài khoản kế toán cho chi phí vật liệu", "Finance", "High", 2.5, "Not Started", "Nguyễn Văn Hưng", "Chỉ flag các bút toán lệch tài khoản"],
  ["DP-036", d("2026-05-21"), "Vũ Minh Khoa", "Senior", "Cập nhật báo cáo sai lệch dự toán cho Operations Manager", "Reporting", "High", 2.5, "Not Started", "Phạm Quốc Bảo", "Nêu nguyên nhân chính cho top 5 hạng mục"],
  ["DP-037", d("2026-05-21"), "Nguyễn Văn Hưng", "Manager", "Review báo cáo cash-out dự kiến tuần 21", "Finance", "High", 1.5, "Not Started", "Phạm Quốc Bảo", "Chuẩn bị trước cuộc họp quản trị dòng tiền"],
  ["DP-038", d("2026-05-22"), "Lê Minh Anh", "Intern", "Cập nhật trạng thái thanh toán vào payment tracker", "Finance", "Medium", 2, "Not Started", "Nguyễn Văn Hưng", "Ghi rõ thanh toán một phần/toàn phần"],
  ["DP-039", d("2026-05-22"), "Phạm Gia Huy", "Intern", "Lưu trữ bản hợp đồng đã ký theo mã dự án", "Admin", "Low", 2, "Not Started", "Trần Thị Mai", "Tách bản scan và bản Word chỉnh sửa"],
  ["DP-040", d("2026-05-22"), "Ngô Thảo Vy", "Intern", "Kiểm tra chứng từ ngân hàng cho khoản hoàn ứng", "Audit", "High", 2.5, "Not Started", "Đỗ Thu Hà", "Đối chiếu với phiếu đề nghị hoàn ứng"],
  ["DP-041", d("2026-05-22"), "Hoàng Đức Nam", "Intern", "Tổng hợp file scan biên bản nghiệm thu tuần 20", "Admin", "Medium", 2.5, "Not Started", "Vũ Minh Khoa", "Gửi link thư mục cho Project Controls"],
  ["DP-042", d("2026-05-22"), "Bùi Khánh Linh", "Intern", "Chuẩn bị báo cáo tuần về tiến độ xử lý hồ sơ intern", "Reporting", "Medium", 3, "Not Started", "Phạm Quốc Bảo", "Tách task done, blocked, cần review"],
  ["DP-043", d("2026-05-22"), "Trần Thị Mai", "Senior", "Chốt checklist review hợp đồng cho nhóm intern", "Contract", "Medium", 1.5, "Not Started", "Phạm Quốc Bảo", "Đưa ví dụ lỗi thường gặp"],
  ["DP-044", d("2026-05-22"), "Đỗ Thu Hà", "Senior", "Chốt danh sách chứng từ cần bổ sung cho kiểm toán nội bộ", "Audit", "High", 2, "Not Started", "Nguyễn Văn Hưng", "Gửi danh sách trước 16:30"],
  ["DP-045", d("2026-05-22"), "Vũ Minh Khoa", "Senior", "Review file báo cáo chi phí đã chuẩn hóa", "Reporting", "Medium", 2, "Not Started", "Phạm Quốc Bảo", "Kiểm tra pivot và định dạng số tiền"],
];

const checklistHeaders = [
  "Task ID",
  "Task Name",
  "Step-by-step checklist",
  "Required files (Excel/PDF/Contract/etc.)",
  "Validation criteria",
  "Responsible person",
  "Review status (Pending / Approved / Rejected)",
];

const checklists = [
  ["DP-001", "Rà soát điều khoản thanh toán Hợp đồng thi công Khu A", "1. Mở bản Word hợp đồng mới nhất\n2. Kiểm tra điều khoản tạm ứng, nghiệm thu, giữ lại bảo hành\n3. So sánh với hợp đồng mẫu\n4. Ghi comment các điểm cần manager duyệt", "Contract DOCX, phụ lục thanh toán, hợp đồng mẫu PDF", "Không còn điều khoản thiếu số ngày thanh toán; comment rõ trang/điều khoản", "Trần Thị Mai", "Approved"],
  ["DP-002", "Định dạng lại phụ lục khối lượng phát sinh dự án Riverside", "1. Nhận file phụ lục từ Contract Lead\n2. Chuẩn hóa font, header, mã hạng mục\n3. Kiểm tra tổng giá trị từng hạng mục\n4. Lưu bản clean và bản track changes", "Contract DOCX, BOQ Excel", "Tổng giá trị khớp BOQ; không mất dòng/hạng mục", "Phạm Gia Huy", "Approved"],
  ["DP-003", "Phân loại báo cáo chi phí vật liệu tuần 20", "1. Lọc dữ liệu theo mã dự án\n2. Phân loại theo xi măng, thép, cát đá, vật tư phụ\n3. Đánh dấu chi phí chưa có hóa đơn\n4. Xuất summary theo công trình", "Cost report Excel, hóa đơn PDF", "Tổng chi phí sau phân loại bằng tổng file nguồn; không có category trống", "Lê Minh Anh", "Approved"],
  ["DP-004", "Nhập hóa đơn xi măng và thép vào file kế toán nội bộ", "1. Kiểm tra số hóa đơn và MST\n2. Nhập ngày, nhà cung cấp, số tiền trước VAT, VAT\n3. Gắn mã công trình\n4. Highlight hóa đơn thiếu chứng từ", "Invoice PDF, Accounting Master Excel", "Không trùng số hóa đơn; VAT tính đúng 8%/10% theo chứng từ", "Ngô Thảo Vy", "Pending"],
  ["DP-007", "Kiểm tra chứng từ ngân hàng khoản tạm ứng Long Thành", "1. Tải sao kê ngân hàng\n2. Đối chiếu phiếu đề nghị tạm ứng\n3. Kiểm tra chữ ký phê duyệt\n4. Lưu bằng chứng đối soát", "Bank statement PDF, payment request PDF", "Số tiền, ngày giao dịch và người thụ hưởng khớp 100%", "Đỗ Thu Hà", "Approved"],
  ["DP-011", "Tạo lệnh chuyển tiền cho nhà thầu cốt pha An Phú", "1. Kiểm tra thông tin nhà thầu\n2. Đối chiếu hạn mức thanh toán\n3. Tạo payment order nháp\n4. Gửi Finance Manager duyệt", "Vendor master Excel, payment request PDF, bank portal screenshot", "Số tài khoản đúng vendor master; số tiền không vượt hạn mức duyệt", "Lê Minh Anh", "Pending"],
  ["DP-012", "Soát lỗi hợp đồng nhà thầu phụ PCCC", "1. Kiểm tra mã hợp đồng và tên pháp nhân\n2. Soát lỗi chính tả, định dạng, đánh số điều khoản\n3. Ghi chú điều khoản cần senior xác nhận\n4. Xuất bản Word track changes", "PCCC Contract DOCX, checklist hợp đồng", "Không còn lỗi đánh số; mọi chỉnh sửa dùng track changes", "Phạm Gia Huy", "Approved"],
  ["DP-013", "Đối chiếu hóa đơn vật liệu với bảng nhập kho Riverside", "1. Lọc hóa đơn theo mã dự án\n2. Match số lượng và đơn giá với phiếu nhập kho\n3. Ghi chênh lệch theo từng mã vật tư\n4. Báo cáo chứng từ còn thiếu", "Invoice PDF, warehouse receiving Excel", "Các dòng lệch trên 1% có note nguyên nhân", "Ngô Thảo Vy", "Rejected"],
  ["DP-014", "Chuẩn hóa thư mục chứng từ ngân hàng tháng 05", "1. Gom chứng từ theo ngày giao dịch\n2. Đổi tên file theo quy ước YYYYMMDD_Project_Vendor\n3. Tách giao dịch nội bộ và nhà thầu\n4. Cập nhật file index", "Bank PDFs, folder index Excel", "100% file có mã ngày và mã dự án; không có file duplicate", "Hoàng Đức Nam", "Pending"],
  ["DP-018", "Tổng hợp rủi ro lệch dự toán vật liệu quý II", "1. Trích dữ liệu actual cost\n2. So sánh với budget baseline\n3. Lọc hạng mục lệch trên 8%\n4. Ghi nguyên nhân và đề xuất follow-up", "Budget baseline Excel, actual cost tracker", "Top variance có số tiền, %, nguyên nhân và owner", "Vũ Minh Khoa", "Pending"],
  ["DP-020", "Đối soát công nợ nhà cung cấp Sơn Nam", "1. Lấy statement từ nhà cung cấp\n2. Match hóa đơn, thanh toán, credit note\n3. Tách khoản quá hạn\n4. Lập bảng chênh lệch", "Vendor statement PDF, AP ledger Excel", "Chênh lệch trên 500.000 VND có giải thích", "Lê Minh Anh", "Pending"],
  ["DP-021", "Chuẩn hóa bảng so sánh phiên bản hợp đồng PCCC", "1. Tạo bảng version control\n2. Liệt kê thay đổi giá trị, tiến độ, bảo hành\n3. Gắn nguồn trang/điều khoản\n4. Gửi Contract Lead review", "Contract versions DOCX/PDF, comparison Excel", "Mỗi thay đổi có nguồn và trạng thái review", "Phạm Gia Huy", "Pending"],
  ["DP-024", "Lập bảng tóm tắt chi phí nhà thầu phụ theo dự án", "1. Lọc dữ liệu theo mã nhà thầu\n2. Group theo dự án và hạng mục\n3. Tính tổng đã thanh toán và còn phải trả\n4. Kiểm tra định dạng VND", "Subcontractor payment Excel, AP ledger", "Tổng theo dự án khớp ledger; không có mã dự án trống", "Bùi Khánh Linh", "Pending"],
  ["DP-026", "Review chứng từ thanh toán nhà thầu điện M&E đợt 2", "1. Kiểm tra hóa đơn VAT\n2. Kiểm tra biên bản nghiệm thu\n3. Đối chiếu hợp đồng và giá trị giữ lại\n4. Ghi kết luận review", "VAT invoice PDF, acceptance minutes PDF, contract PDF", "Đủ chữ ký, số tiền khớp hợp đồng và giữ lại 5%", "Đỗ Thu Hà", "Pending"],
  ["DP-031", "Đối chiếu dữ liệu thuế VAT với file hóa đơn đầu vào", "1. Lọc hóa đơn tháng 05\n2. Kiểm tra mã tra cứu hóa đơn\n3. Đối chiếu VAT với bảng kê thuế\n4. Flag hóa đơn thiếu thông tin", "VAT ledger Excel, invoice PDFs", "Không có hóa đơn thiếu mã tra cứu trong danh sách final", "Ngô Thảo Vy", "Pending"],
  ["DP-032", "Tổng hợp danh mục hồ sơ còn thiếu cho kiểm toán nội bộ", "1. Lấy danh sách giao dịch trên 200 triệu\n2. Kiểm tra đủ hợp đồng, hóa đơn, nghiệm thu, lệnh chi\n3. Lập danh mục missing docs\n4. Gửi Senior Accountant", "Audit request list Excel, contract/invoice/payment PDFs", "Mỗi dòng thiếu chứng từ có owner và deadline", "Hoàng Đức Nam", "Pending"],
  ["DP-033", "Chuẩn hóa file Excel báo cáo chi phí theo mẫu mới", "1. Giữ nguyên sheet nguồn\n2. Tạo sheet report theo template mới\n3. Chuẩn hóa định dạng tiền, ngày, mã dự án\n4. Kiểm tra pivot summary", "Cost report Excel, reporting template XLSX", "Pivot không lỗi; tổng tiền khớp sheet nguồn", "Bùi Khánh Linh", "Pending"],
  ["DP-042", "Chuẩn bị báo cáo tuần về tiến độ xử lý hồ sơ intern", "1. Tổng hợp task theo intern\n2. Tách trạng thái done, blocked, needs review\n3. Viết nhận xét ngắn theo từng nhóm việc\n4. Gửi Operations Manager", "Daily plan Excel, QA tracker", "Báo cáo có số lượng task, blocker và đề xuất hỗ trợ", "Bùi Khánh Linh", "Pending"],
];

const standupHeaders = [
  "Date",
  "Employee Name",
  "Yesterday Done",
  "Today Plan",
  "Blockers",
  "Support Needed",
  "Manager Comment",
];

const standupTemplates = {
  "Nguyễn Văn Hưng": [
    ["Chốt hạn mức thanh toán tuần trước", "Duyệt payment order và rà soát cash-out", "Không có", "Cần số liệu AP cuối ngày", "Ưu tiên khoản đến hạn cao"],
    ["Duyệt lịch thanh toán M&E", "Review báo cáo chi phí vật liệu", "Chờ xác nhận từ ngân hàng", "Finance intern cập nhật payment log", "Theo dõi sát giao dịch bị pending"],
    ["Review công nợ vendor trọng điểm", "Chuẩn bị meeting dòng tiền", "Thiếu forecast từ Project Controls", "Khoa gửi variance trước 15:00", "OK, nhắc team cập nhật status"],
    ["Xác nhận ngân sách thanh toán tuần", "Review cash-out tuần 21", "Không có", "Cần QA payment order đã duyệt", "Giữ format báo cáo ngắn gọn"],
    ["Chốt danh sách khoản ưu tiên", "Gửi summary cho Operations Manager", "Không có", "Không cần thêm", "Hoàn tất trước 17:00"],
  ],
  "Trần Thị Mai": [
    ["Review hợp đồng Khu A", "Rà soát phụ lục tiến độ Long Thành", "Thiếu phụ lục bản ký", "Gia Huy chuẩn hóa comparison", "Cập nhật issue log"],
    ["Chốt lỗi hợp đồng PCCC", "Review hợp đồng facade", "Một điều khoản chưa rõ trách nhiệm bảo hành", "Cần Bảo xác nhận risk level", "Tập trung điều khoản phạt"],
    ["Gửi comment hợp đồng PCCC", "Tạo checklist review cho intern", "Không có", "Gia Huy lọc thay đổi trọng yếu", "OK"],
    ["Review hợp đồng bảo trì thiết bị", "Chốt checklist review hợp đồng", "Chờ bản scan hợp đồng đã ký", "Nam hỗ trợ lưu trữ bản scan", "Kiểm tra version control"],
    ["Cập nhật template hợp đồng", "Handover danh sách điểm cần duyệt", "Không có", "Không cần thêm", "Đóng các issue đã xử lý"],
  ],
  "Phạm Quốc Bảo": [
    ["Sắp xếp thứ tự ưu tiên task tuần", "Họp nhanh với Contract Lead", "Thiếu input từ công trường", "Khoa cập nhật nhật ký nghiệm thu", "Theo dõi blocker DP-008"],
    ["Chốt scope xử lý hợp đồng phát sinh", "Review rủi ro tiến độ và dòng tiền", "Không có", "Cần Finance gửi cash-out", "OK"],
    ["Phân bổ owner cho hồ sơ blocked", "Kiểm tra báo cáo variance", "Chưa có nhật ký ngày 16/05", "Nhắc đội thi công bổ sung", "Escalate nếu quá 15:00"],
    ["Review kế hoạch ưu tiên QA", "Chuẩn bị weekly ops summary", "Không có", "Linh gửi intern progress", "Giữ comment cụ thể"],
    ["Chốt danh sách follow-up tuần sau", "Gửi summary nội bộ", "Không có", "Không cần thêm", "Hoàn tất cuối ngày"],
  ],
  "Đỗ Thu Hà": [
    ["Kiểm tra chứng từ tạm ứng Long Thành", "Review hóa đơn và AP ledger", "Một số hóa đơn thiếu phiếu nhập", "Vy kiểm tra lô thép Hòa Phát", "Cập nhật danh sách thiếu chứng từ"],
    ["Review phân bổ chi phí nhân công", "Kiểm tra chứng từ M&E đợt 2", "Chờ biên bản nghiệm thu bản ký", "Nam scan bản ký khi nhận", "Ưu tiên giao dịch trên 200 triệu"],
    ["Kiểm tra VAT đầu vào", "Chốt danh sách chứng từ audit", "Một vendor gửi file mờ", "Yêu cầu vendor gửi lại PDF", "OK"],
    ["Review bút toán chi phí vật liệu", "Kiểm tra chứng từ hoàn ứng", "Không có", "Vy tổng hợp mã tra cứu thiếu", "Tập trung lỗi MST"],
    ["Chốt danh sách thiếu hồ sơ", "Gửi Finance Manager review", "Không có", "Không cần thêm", "Gửi trước 16:30"],
  ],
  "Vũ Minh Khoa": [
    ["Đối soát nghiệm thu Khu B", "Tổng hợp variance vật liệu", "Thiếu nhật ký công trường", "Bảo hỗ trợ yêu cầu công trường", "Cập nhật blocker rõ deadline"],
    ["Cập nhật dashboard chi phí", "Review file cost report template", "Chờ actual cost mới nhất", "Linh cập nhật nguồn dữ liệu", "OK"],
    ["Tổng hợp rủi ro lệch dự toán", "Đối chiếu tiến độ với cash flow", "Không có", "Cần Finance xác nhận thanh toán M&E", "Tách top 5 variance"],
    ["Review báo cáo sai lệch dự toán", "Kiểm tra pivot cost report", "Một sheet nguồn thiếu mã dự án", "Linh chuẩn hóa trước review", "Không đổi sheet nguồn"],
    ["Chốt variance report", "Gửi Operations Manager", "Không có", "Không cần thêm", "Hoàn tất bản final"],
  ],
  "Lê Minh Anh": [
    ["Phân loại chi phí vật liệu tuần 20", "Tạo payment order An Phú", "Chưa xác nhận số tài khoản mới", "Anh Hưng xác nhận vendor master", "Cập nhật ngay khi có xác nhận"],
    ["Tạo payment order nháp", "Đối soát công nợ Sơn Nam", "Thiếu credit note từ vendor", "Chị Hà kiểm tra AP ledger", "Flag chênh lệch rõ số tiền"],
    ["Đối soát công nợ", "Kiểm tra lệnh chuyển tiền ngân hàng", "Không có", "Cần sao kê mới nhất", "Lưu mã giao dịch vào log"],
    ["Kiểm tra giao dịch ngân hàng", "Cập nhật payment tracker", "Một giao dịch pending", "Finance Manager xác nhận ngân hàng", "Theo dõi đến cuối ngày"],
    ["Cập nhật payment tracker", "Chuẩn bị summary task Finance Intern", "Không có", "Không cần thêm", "Tốt, giữ format ổn định"],
  ],
  "Phạm Gia Huy": [
    ["Chuẩn hóa phụ lục Riverside", "Soát hợp đồng PCCC", "Không có", "Chị Mai xác nhận điều khoản bảo hành", "Track changes đầy đủ"],
    ["Soát lỗi hợp đồng PCCC", "Chuẩn hóa comparison hợp đồng", "Chưa có bản PDF ký", "Nam kiểm tra thư mục scan", "Gắn link điều khoản"],
    ["Lập bảng version control", "Tổng hợp điều khoản facade cần review", "Một số trang scan mờ", "Contract Lead cung cấp bản Word", "OK"],
    ["Tổng hợp issue hợp đồng facade", "Lưu trữ hợp đồng đã ký", "Không có", "Cần mã dự án chính xác", "Tách scan và Word"],
    ["Lưu trữ hợp đồng", "Cập nhật danh sách hợp đồng chờ review", "Không có", "Không cần thêm", "Hoàn tất folder structure"],
  ],
  "Ngô Thảo Vy": [
    ["Nhập hóa đơn xi măng/thép", "Đối chiếu hóa đơn Riverside", "Thiếu phiếu nhập kho lô thép", "Chị Hà hỗ trợ lấy phiếu nhập", "Không nhập dòng chưa đủ chứng từ"],
    ["Đối chiếu hóa đơn vật liệu", "Nhập hóa đơn thuê máy móc", "Một MST chưa khớp", "Senior Accountant xác nhận vendor", "Flag lỗi MST"],
    ["Nhập dữ liệu thuê máy", "Đối chiếu VAT đầu vào", "Thiếu mã tra cứu hóa đơn", "Vendor gửi lại thông tin", "Cập nhật danh sách thiếu"],
    ["Đối chiếu VAT", "Kiểm tra chứng từ hoàn ứng", "Không có", "Cần payment request PDF", "Tập trung giao dịch trên 50 triệu"],
    ["Kiểm tra chứng từ hoàn ứng", "Cập nhật issue list hóa đơn", "Không có", "Không cần thêm", "Gửi bản final cho chị Hà"],
  ],
  "Hoàng Đức Nam": [
    ["Scan hồ sơ nghiệm thu móng", "Chuẩn hóa thư mục chứng từ ngân hàng", "Không có", "Cần quy ước đặt tên final", "Dùng mã dự án trong file name"],
    ["Chuẩn hóa chứng từ ngân hàng", "Scan biên bản bàn giao vật tư", "Một số file scan bị nghiêng", "Scan lại trang lỗi", "Kiểm tra chất lượng PDF"],
    ["Gộp PDF bàn giao vật tư", "Tổng hợp hồ sơ thiếu cho audit", "Thiếu hợp đồng bản ký", "Gia Huy kiểm tra thư mục hợp đồng", "Ưu tiên giao dịch lớn"],
    ["Tổng hợp missing docs", "Tổng hợp scan nghiệm thu tuần 20", "Không có", "Cần link folder từ công trường", "Cập nhật index"],
    ["Tổng hợp scan nghiệm thu", "Dọn thư mục hồ sơ theo tuần", "Không có", "Không cần thêm", "Giữ naming convention"],
  ],
  "Bùi Khánh Linh": [
    ["Tổng hợp báo cáo tài chính tuần", "Cập nhật dashboard chi phí", "Chờ số liệu công nợ cuối ngày", "Anh Hưng gửi AP aging", "Ghi nguồn dữ liệu"],
    ["Cập nhật dashboard", "Lập bảng tóm tắt chi phí nhà thầu phụ", "Thiếu mã hợp đồng một vendor", "Finance cung cấp vendor master", "Không để mã dự án trống"],
    ["Tóm tắt chi phí nhà thầu", "Chuẩn hóa file báo cáo chi phí", "Không có", "Khoa xác nhận template mới", "Kiểm tra pivot"],
    ["Chuẩn hóa file Excel", "Chuẩn bị báo cáo tiến độ task intern", "Một pivot lỗi dữ liệu rỗng", "Khoa review file nguồn", "Không đổi sheet nguồn"],
    ["Chuẩn bị báo cáo intern", "Gửi weekly summary cho Ops Manager", "Không có", "Không cần thêm", "Báo cáo ngắn, có số liệu"],
  ],
};

const dates = [d("2026-05-18"), d("2026-05-19"), d("2026-05-20"), d("2026-05-21"), d("2026-05-22")];
const standups = employees.flatMap((employee) =>
  dates.map((date, index) => {
    const [yesterday, today, blocker, support, comment] = standupTemplates[employee.name][index];
    return [date, employee.name, yesterday, today, blocker, support, comment];
  }),
);

const qaHeaders = [
  "Task ID",
  "Reviewer (Senior staff)",
  "Review result (Approved / Needs Fix / Rejected)",
  "Feedback detail",
  "Re-submission deadline",
  "Final status",
  "Responsible person",
];

const qaRows = [
  ["DP-001", "Trần Thị Mai", "Approved", "Điều khoản thanh toán rõ, chỉ cần giữ lại comment tham chiếu hợp đồng mẫu.", "", "Closed", "Trần Thị Mai"],
  ["DP-002", "Trần Thị Mai", "Approved", "Format sạch, tổng giá trị phụ lục khớp BOQ.", "", "Closed", "Phạm Gia Huy"],
  ["DP-003", "Nguyễn Văn Hưng", "Approved", "Phân loại đúng nhóm vật liệu, summary dễ đọc.", "", "Closed", "Lê Minh Anh"],
  ["DP-004", "Đỗ Thu Hà", "Needs Fix", "Thiếu kiểm tra MST cho 2 hóa đơn thép và một dòng chưa gắn mã công trình.", d("2026-05-20"), "Pending Resubmission", "Ngô Thảo Vy"],
  ["DP-005", "Vũ Minh Khoa", "Approved", "File scan rõ, đặt tên đúng mã dự án.", "", "Closed", "Hoàng Đức Nam"],
  ["DP-006", "Nguyễn Văn Hưng", "Needs Fix", "Bổ sung nguồn số liệu công nợ và ngày chốt dữ liệu.", d("2026-05-20"), "Pending Resubmission", "Bùi Khánh Linh"],
  ["DP-007", "Đỗ Thu Hà", "Approved", "Chứng từ ngân hàng khớp số tiền và ngày giao dịch.", "", "Closed", "Đỗ Thu Hà"],
  ["DP-008", "Vũ Minh Khoa", "Needs Fix", "Cần bổ sung nhật ký công trường ngày 16/05 trước khi kết luận.", d("2026-05-20"), "Waiting for Field Input", "Vũ Minh Khoa"],
  ["DP-011", "Nguyễn Văn Hưng", "Needs Fix", "Không được submit lệnh chuyển tiền trước khi xác nhận số tài khoản mới.", d("2026-05-20"), "Pending Resubmission", "Lê Minh Anh"],
  ["DP-012", "Trần Thị Mai", "Approved", "Soát lỗi tốt, track changes đầy đủ.", "", "Closed", "Phạm Gia Huy"],
  ["DP-013", "Đỗ Thu Hà", "Rejected", "Không thể đối chiếu vì thiếu phiếu nhập kho; cần làm lại sau khi có chứng từ.", d("2026-05-21"), "Rework Required", "Ngô Thảo Vy"],
  ["DP-014", "Đỗ Thu Hà", "Needs Fix", "Một số file chưa theo quy ước YYYYMMDD_Project_Vendor.", d("2026-05-20"), "Pending Resubmission", "Hoàng Đức Nam"],
  ["DP-015", "Vũ Minh Khoa", "Needs Fix", "Dashboard chưa có nguồn dữ liệu và chưa tách dự án.", d("2026-05-21"), "Pending Resubmission", "Bùi Khánh Linh"],
  ["DP-016", "Trần Thị Mai", "Needs Fix", "Bổ sung căn cứ gia hạn do điều kiện thời tiết.", d("2026-05-20"), "In Review", "Trần Thị Mai"],
  ["DP-017", "Đỗ Thu Hà", "Approved", "Phân bổ nhân công khớp bảng chấm công.", "", "Closed", "Đỗ Thu Hà"],
  ["DP-018", "Phạm Quốc Bảo", "Needs Fix", "Cần thêm owner cho từng variance trên 8%.", d("2026-05-21"), "Pending Resubmission", "Vũ Minh Khoa"],
  ["DP-020", "Đỗ Thu Hà", "Approved", "Bảng chênh lệch công nợ rõ, có note cho khoản trên 500.000 VND.", "", "Closed", "Lê Minh Anh"],
  ["DP-021", "Trần Thị Mai", "Approved", "Version control rõ thay đổi giá trị và tiến độ.", "", "Closed", "Phạm Gia Huy"],
  ["DP-022", "Đỗ Thu Hà", "Needs Fix", "Bổ sung kiểm tra MST trước khi nhập final.", d("2026-05-21"), "Pending Resubmission", "Ngô Thảo Vy"],
  ["DP-023", "Vũ Minh Khoa", "Approved", "PDF gộp đúng theo từng ngày bàn giao.", "", "Closed", "Hoàng Đức Nam"],
  ["DP-024", "Nguyễn Văn Hưng", "Approved", "Bảng tổng hợp nhà thầu phụ khớp AP ledger.", "", "Closed", "Bùi Khánh Linh"],
  ["DP-026", "Đỗ Thu Hà", "Approved", "Chứng từ M&E đủ hóa đơn, nghiệm thu và giữ lại bảo hành.", "", "Closed", "Đỗ Thu Hà"],
  ["DP-029", "Nguyễn Văn Hưng", "Approved", "Mã giao dịch đã lưu đúng payment log.", "", "Closed", "Lê Minh Anh"],
  ["DP-030", "Trần Thị Mai", "Needs Fix", "Gắn link tới trang hợp đồng cho từng điều khoản cần xác nhận.", d("2026-05-22"), "Pending Resubmission", "Phạm Gia Huy"],
  ["DP-031", "Đỗ Thu Hà", "Needs Fix", "Còn 3 hóa đơn thiếu mã tra cứu.", d("2026-05-22"), "Pending Resubmission", "Ngô Thảo Vy"],
  ["DP-032", "Đỗ Thu Hà", "Approved", "Danh mục hồ sơ thiếu có owner và deadline.", "", "Closed", "Hoàng Đức Nam"],
  ["DP-033", "Vũ Minh Khoa", "Needs Fix", "Pivot summary cần kiểm tra lại dòng dữ liệu rỗng.", d("2026-05-22"), "Pending Resubmission", "Bùi Khánh Linh"],
  ["DP-042", "Phạm Quốc Bảo", "Approved", "Báo cáo tiến độ intern có số liệu, blocker và đề xuất hỗ trợ.", "", "Closed", "Bùi Khánh Linh"],
];

const performanceHeaders = [
  "Intern Name",
  "Total Tasks Assigned",
  "Completed Tasks",
  "Average Completion Time",
  "Error Rate",
  "Review Score (1-10)",
  "Weekly Comment from Manager",
];

const internComments = [
  ["Lê Minh Anh", "Nắm nghiệp vụ finance nhanh, cần kiểm tra vendor bank detail kỹ hơn trước khi submit payment order."],
  ["Phạm Gia Huy", "Làm hợp đồng cẩn thận, track changes tốt; cần gắn nguồn điều khoản đầy đủ hơn."],
  ["Ngô Thảo Vy", "Chăm nhập liệu nhưng cần checklist MST, VAT và chứng từ kho trước khi chốt file."],
  ["Hoàng Đức Nam", "Hỗ trợ admin và scan ổn định, nên kiểm tra naming convention trước khi gửi review."],
  ["Bùi Khánh Linh", "Có tư duy reporting tốt, cần khóa nguồn dữ liệu và kiểm tra pivot trước khi gửi senior."],
];

workbook.setColorScheme({
  name: "Construction Ops",
  themeColors: {
    accent1: "#244C5A",
    accent2: "#D97706",
    accent3: "#2F7D32",
    accent4: "#7C3AED",
    accent5: "#0E7490",
    accent6: "#BE123C",
    dk1: "#111827",
    lt1: "#FFFFFF",
    lt2: "#E5E7EB",
    hlink: "#2563EB",
    folHlink: "#6D28D9",
  },
});

const projectHeaders = [
  "Project Code",
  "Project Name",
  "Task ID",
  "Workstream",
  "Task Name",
  "Owner",
  "Role",
  "Priority",
  "Status",
  "Due Date",
  "Estimated Hours",
  "Assigned By",
  "Next Action",
  "Source Sheet",
];

const projectPool = [
  ["RIV-26", "Riverside Apartment Fit-out", "Cost Control"],
  ["LTP-26", "Long Thanh Industrial Park", "Finance Operations"],
  ["BD-FA", "Binh Duong Factory Extension", "Site Documentation"],
  ["KHU-A", "Khu A Commercial Block", "Contract Management"],
  ["KHU-B", "Khu B Infrastructure Works", "Project Controls"],
  ["OPS-FO", "Internal Finance Operations", "Finance Shared Services"],
];

function nextActionFor(status, priority) {
  if (status === "Blocked") return "Escalate blocker and confirm missing document owner";
  if (status === "In Progress") return priority === "High" ? "Submit interim version for same-day review" : "Update progress before standup";
  if (status === "Done") return "Archive evidence and wait for QA close-out";
  return priority === "High" ? "Start today and prepare review evidence" : "Schedule with owner and confirm input files";
}

const projectTasks = tasks.map((task, index) => {
  const project = projectPool[index % projectPool.length];
  return [
    project[0],
    project[1],
    task[0],
    project[2],
    task[4],
    task[2],
    task[3],
    task[6],
    task[8],
    task[1],
    task[7],
    task[9],
    nextActionFor(task[8], task[6]),
    "DAILY TASK PLAN",
  ];
});

function addSheet(name, headers, rows, headerColor, tableName = null) {
  const sheet = workbook.worksheets.add(name);
  const allRows = [headers, ...rows];
  const lastCol = columnLetter(headers.length);
  sheet.getRange(`A1:${lastCol}${allRows.length}`).values = allRows;
  const used = sheet.getRange(`A1:${lastCol}${allRows.length}`);
  used.format = {
    font: { name: "Arial", size: 10, color: "#111827" },
    verticalAlignment: "top",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#D1D5DB" },
  };
  const header = sheet.getRange(`A1:${lastCol}1`);
  header.format = {
    fill: headerColor,
    font: { name: "Arial", size: 10, color: "#FFFFFF", bold: true },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#9CA3AF" },
  };
  if (tableName) {
    const table = sheet.tables.add(used, true);
    table.name = tableName;
    table.style = "TableStyleMedium2";
  }
  sheet.freezePanes.freezeRows(1);
  used.format.autofitRows();
  return sheet;
}

function columnLetter(index) {
  let n = index;
  let s = "";
  while (n > 0) {
    const m = (n - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    n = Math.floor((n - m) / 26);
  }
  return s;
}

function setWidths(sheet, widths) {
  widths.forEach((width, idx) => {
    const col = columnLetter(idx + 1);
    sheet.getRange(`${col}:${col}`).format.columnWidthPx = width;
  });
}

function addSmallTable(sheet, range, name) {
  const table = sheet.tables.add(sheet.getRange(range), true);
  table.name = name;
  table.style = "TableStyleMedium4";
  return table;
}

const dashboardSheet = workbook.worksheets.add("PROJECT TASKS DASHBOARD");

const projectSheet = addSheet("PROJECT TASKS", projectHeaders, projectTasks, "#244C5A", "tblProjectTasks");
setWidths(projectSheet, [100, 210, 78, 150, 320, 150, 110, 90, 130, 92, 95, 150, 330, 130]);
projectSheet.getRange("J2:J46").format.numberFormat = "yyyy-mm-dd";
projectSheet.getRange("K2:K46").format.numberFormat = "0.0";
projectSheet.getRange("H2:H46").conditionalFormats.add("containsText", { text: "High", format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } } });
projectSheet.getRange("I2:I46").conditionalFormats.add("containsText", { text: "Done", format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } } });
projectSheet.getRange("I2:I46").conditionalFormats.add("containsText", { text: "Blocked", format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } } });

const dailySheet = addSheet("DAILY TASK PLAN", taskPlanHeaders, tasks, "#1F4E78", "tblDailyTaskPlan");
setWidths(dailySheet, [78, 92, 150, 120, 300, 150, 100, 92, 140, 150, 280]);
dailySheet.getRange("B2:B46").format.numberFormat = "yyyy-mm-dd";
dailySheet.getRange("H2:H46").format.numberFormat = "0.0";
dailySheet.getRange("G2:G46").conditionalFormats.add("containsText", { text: "High", format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } } });
dailySheet.getRange("G2:G46").conditionalFormats.add("containsText", { text: "Medium", format: { fill: "#FEF3C7", font: { color: "#92400E" } } });
dailySheet.getRange("I2:I46").conditionalFormats.add("containsText", { text: "Done", format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } } });
dailySheet.getRange("I2:I46").conditionalFormats.add("containsText", { text: "Blocked", format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } } });
dailySheet.getRange("I2:I46").conditionalFormats.add("containsText", { text: "In Progress", format: { fill: "#DBEAFE", font: { color: "#1D4ED8" } } });

const checklistSheet = addSheet("CHECKLIST TASK DETAIL", checklistHeaders, checklists, "#B7791F", "tblChecklistTaskDetail");
setWidths(checklistSheet, [78, 260, 420, 250, 310, 145, 120]);

const standupSheet = addSheet("DAILY STANDUP LOG", standupHeaders, standups, "#2F7D32", "tblDailyStandupLog");
setWidths(standupSheet, [92, 150, 260, 260, 230, 230, 230]);
standupSheet.getRange("A2:A51").format.numberFormat = "yyyy-mm-dd";

const qaSheet = addSheet("TASK REVIEW - QA", qaHeaders, qaRows, "#9A3412", "tblTaskReviewQA");
setWidths(qaSheet, [78, 155, 150, 360, 120, 155, 150]);
qaSheet.getRange("E2:E29").format.numberFormat = "yyyy-mm-dd";
qaSheet.getRange("C2:C29").conditionalFormats.add("containsText", { text: "Approved", format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } } });
qaSheet.getRange("C2:C29").conditionalFormats.add("containsText", { text: "Needs Fix", format: { fill: "#FEF3C7", font: { color: "#92400E", bold: true } } });
qaSheet.getRange("C2:C29").conditionalFormats.add("containsText", { text: "Rejected", format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } } });

const performanceRows = internComments.map(([name, comment]) => [name, null, null, null, null, null, comment]);
const performanceSheet = addSheet("INTERNS PERFORMANCE TRACKING", performanceHeaders, performanceRows, "#6B46C1", "tblInternPerformance");
setWidths(performanceSheet, [160, 120, 110, 140, 105, 120, 430]);
const performanceFormulas = internComments.map(([name], idx) => {
  const row = idx + 2;
  return [
    `=COUNTIF('DAILY TASK PLAN'!C2:C46,A${row})`,
    `=COUNTIFS('DAILY TASK PLAN'!C2:C46,A${row},'DAILY TASK PLAN'!I2:I46,"Done")`,
    `=IFERROR(AVERAGEIFS('DAILY TASK PLAN'!H2:H46,'DAILY TASK PLAN'!C2:C46,A${row},'DAILY TASK PLAN'!I2:I46,"Done"),0)`,
    `=IFERROR((COUNTIFS('TASK REVIEW - QA'!G2:G29,A${row},'TASK REVIEW - QA'!C2:C29,"Needs Fix")+COUNTIFS('TASK REVIEW - QA'!G2:G29,A${row},'TASK REVIEW - QA'!C2:C29,"Rejected"))/COUNTIF('TASK REVIEW - QA'!G2:G29,A${row}),0)`,
    `=IFERROR(ROUND(MIN(10,MAX(1,7+(C${row}/B${row})*2.5-E${row}*5)),1),0)`,
  ];
});
performanceSheet.getRange("B2:F6").formulas = performanceFormulas;
performanceSheet.getRange("D2:D6").format.numberFormat = "0.0";
performanceSheet.getRange("E2:E6").format.numberFormat = "0%";
performanceSheet.getRange("F2:F6").format.numberFormat = "0.0";
performanceSheet.getRange("E2:E6").conditionalFormats.add("colorScale", {
  criteria: [
    { type: "lowestValue", color: "#DCFCE7" },
    { type: "percentile", value: 50, color: "#FEF3C7" },
    { type: "highestValue", color: "#FCA5A5" },
  ],
});
performanceSheet.getRange("F2:F6").conditionalFormats.add("colorScale", {
  criteria: [
    { type: "lowestValue", color: "#FCA5A5" },
    { type: "percentile", value: 50, color: "#FEF3C7" },
    { type: "highestValue", color: "#DCFCE7" },
  ],
});

setWidths(dashboardSheet, [120, 92, 26, 140, 95, 26, 130, 90, 90, 90, 90, 110, 24, 110, 110, 110]);
dashboardSheet.getRange("A1:P1").format = {
  fill: "#244C5A",
  font: { name: "Arial", size: 16, color: "#FFFFFF", bold: true },
  verticalAlignment: "center",
  wrapText: true,
};
dashboardSheet.getRange("A1").values = [["CONSTRUCTION FINANCE OPS - PROJECT TASKS DASHBOARD"]];
dashboardSheet.getRange("A2:P2").format = {
  fill: "#E5E7EB",
  font: { name: "Arial", size: 10, color: "#374151", italic: true },
};
dashboardSheet.getRange("A2").values = [["Internship task management tracker | Week of 2026-05-18 | Source tables: tblProjectTasks, tblDailyTaskPlan"]];

dashboardSheet.getRange("A4:L5").values = [
  ["Total Tasks", "", "Completion Rate", "", "Open Tasks", "", "Blocked", "", "High Priority", "", "Intern Tasks", ""],
  [null, "", null, "", null, "", null, "", null, "", null, ""],
];
dashboardSheet.getRange("A5").formulas = [["=COUNTA('DAILY TASK PLAN'!A2:A46)"]];
dashboardSheet.getRange("C5").formulas = [["=IFERROR(COUNTIF('DAILY TASK PLAN'!I2:I46,\"Done\")/COUNTA('DAILY TASK PLAN'!A2:A46),0)"]];
dashboardSheet.getRange("E5").formulas = [["=COUNTIFS('DAILY TASK PLAN'!I2:I46,\"<>Done\")"]];
dashboardSheet.getRange("G5").formulas = [["=COUNTIF('DAILY TASK PLAN'!I2:I46,\"Blocked\")"]];
dashboardSheet.getRange("I5").formulas = [["=COUNTIF('DAILY TASK PLAN'!G2:G46,\"High\")"]];
dashboardSheet.getRange("K5").formulas = [["=COUNTIF('DAILY TASK PLAN'!D2:D46,\"Intern\")"]];
dashboardSheet.getRange("A4:L5").format = {
  fill: "#F8FAFC",
  font: { name: "Arial", size: 10, color: "#111827", bold: true },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  borders: { preset: "all", style: "thin", color: "#CBD5E1" },
};
dashboardSheet.getRange("A5:K5").format.font = { name: "Arial", size: 16, color: "#244C5A", bold: true };
dashboardSheet.getRange("C5").format.numberFormat = "0%";

const statusSummary = [
  ["Status", "Count", "Share"],
  ["Not Started", null, null],
  ["In Progress", null, null],
  ["Done", null, null],
  ["Blocked", null, null],
  ["Total", null, null],
];
dashboardSheet.getRange("A8:C13").values = statusSummary;
dashboardSheet.getRange("B9:B12").formulas = [["=COUNTIF('DAILY TASK PLAN'!I2:I46,A9)"], ["=COUNTIF('DAILY TASK PLAN'!I2:I46,A10)"], ["=COUNTIF('DAILY TASK PLAN'!I2:I46,A11)"], ["=COUNTIF('DAILY TASK PLAN'!I2:I46,A12)"]];
dashboardSheet.getRange("B13").formulas = [["=SUM(B9:B12)"]];
dashboardSheet.getRange("C9:C13").formulas = [["=IFERROR(B9/$B$13,0)"], ["=IFERROR(B10/$B$13,0)"], ["=IFERROR(B11/$B$13,0)"], ["=IFERROR(B12/$B$13,0)"], ["=1"]];
dashboardSheet.getRange("C9:C13").format.numberFormat = "0%";
addSmallTable(dashboardSheet, "A8:C13", "tblDashboardStatus");

const categorySummary = [
  ["Category", "Tasks", "Est. Hours"],
  ["Contract", null, null],
  ["Finance", null, null],
  ["Reporting", null, null],
  ["Admin", null, null],
  ["Audit", null, null],
];
dashboardSheet.getRange("D8:F13").values = categorySummary;
dashboardSheet.getRange("E9:E13").formulas = [["=COUNTIF('DAILY TASK PLAN'!F2:F46,D9)"], ["=COUNTIF('DAILY TASK PLAN'!F2:F46,D10)"], ["=COUNTIF('DAILY TASK PLAN'!F2:F46,D11)"], ["=COUNTIF('DAILY TASK PLAN'!F2:F46,D12)"], ["=COUNTIF('DAILY TASK PLAN'!F2:F46,D13)"]];
dashboardSheet.getRange("F9:F13").formulas = [["=SUMIF('DAILY TASK PLAN'!F2:F46,D9,'DAILY TASK PLAN'!H2:H46)"], ["=SUMIF('DAILY TASK PLAN'!F2:F46,D10,'DAILY TASK PLAN'!H2:H46)"], ["=SUMIF('DAILY TASK PLAN'!F2:F46,D11,'DAILY TASK PLAN'!H2:H46)"], ["=SUMIF('DAILY TASK PLAN'!F2:F46,D12,'DAILY TASK PLAN'!H2:H46)"], ["=SUMIF('DAILY TASK PLAN'!F2:F46,D13,'DAILY TASK PLAN'!H2:H46)"]];
dashboardSheet.getRange("F9:F13").format.numberFormat = "0.0";
addSmallTable(dashboardSheet, "D8:F13", "tblDashboardCategory");

dashboardSheet.getRange("H8:M13").values = [["Intern", "Assigned", "Done", "Blocked", "Error Rate", "Score"], ...internComments.map(([name]) => [name, null, null, null, null, null])];
dashboardSheet.getRange("I9:M13").formulas = internComments.map((_, idx) => {
  const row = idx + 9;
  return [
    `=COUNTIF('DAILY TASK PLAN'!C2:C46,H${row})`,
    `=COUNTIFS('DAILY TASK PLAN'!C2:C46,H${row},'DAILY TASK PLAN'!I2:I46,"Done")`,
    `=COUNTIFS('DAILY TASK PLAN'!C2:C46,H${row},'DAILY TASK PLAN'!I2:I46,"Blocked")`,
    `=IFERROR(VLOOKUP(H${row},'INTERNS PERFORMANCE TRACKING'!A2:F6,5,FALSE),0)`,
    `=IFERROR(VLOOKUP(H${row},'INTERNS PERFORMANCE TRACKING'!A2:F6,6,FALSE),0)`,
  ];
});
dashboardSheet.getRange("L9:L13").format.numberFormat = "0%";
dashboardSheet.getRange("M9:M13").format.numberFormat = "0.0";
addSmallTable(dashboardSheet, "H8:M13", "tblDashboardInterns");

const criticalTasks = tasks
  .filter((task) => task[6] === "High" && task[8] !== "Done")
  .slice(0, 8)
  .map((task) => [task[0], task[1], task[2], task[5], task[6], task[8], task[9], nextActionFor(task[8], task[6]), task[10], "Open"]);
dashboardSheet.getRange("A16:J16").values = [["Task ID", "Due Date", "Owner", "Category", "Priority", "Status", "Assigned By", "Next Action", "Notes", "Follow-up"]];
dashboardSheet.getRange(`A17:J${16 + criticalTasks.length}`).values = criticalTasks;
dashboardSheet.getRange(`B17:B${16 + criticalTasks.length}`).format.numberFormat = "yyyy-mm-dd";
dashboardSheet.getRange("A16:J24").format = {
  font: { name: "Arial", size: 10, color: "#111827" },
  verticalAlignment: "top",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#CBD5E1" },
};
addSmallTable(dashboardSheet, "A16:J24", "tblCriticalOpenTasks");
dashboardSheet.getRange("A16:J16").format = {
  fill: "#244C5A",
  font: { name: "Arial", size: 10, color: "#FFFFFF", bold: true },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
dashboardSheet.getRange("A4:L24").format.autofitRows();
dashboardSheet.freezePanes.freezeRows(2);

const statusChartCounts = ["Not Started", "In Progress", "Done", "Blocked"].map((status) =>
  tasks.filter((task) => task[8] === status).length,
);
dashboardSheet.charts.add("ColumnClustered", {
  title: "Tasks by Status",
  categories: ["Not Started", "In Progress", "Done", "Blocked"],
  series: [{ name: "Tasks", values: statusChartCounts }],
  hasLegend: false,
  from: { row: 15, col: 12 },
  extent: { widthPx: 430, heightPx: 240 },
  barOptions: { direction: "column", grouping: "clustered", gapWidth: 90 },
});

const checks = [
  await workbook.inspect({ kind: "sheet,table", search: "tblProjectTasks|tblDailyTaskPlan|tblCriticalOpenTasks", include: "values", tableMaxRows: 4, tableMaxCols: 8 }),
  await workbook.inspect({ kind: "table", range: "PROJECT TASKS DASHBOARD!A1:M13", include: "values,formulas", tableMaxRows: 13, tableMaxCols: 13 }),
  await workbook.inspect({ kind: "table", range: "DAILY TASK PLAN!A1:K8", include: "values,formulas", tableMaxRows: 8, tableMaxCols: 11 }),
  await workbook.inspect({ kind: "table", range: "INTERNS PERFORMANCE TRACKING!A1:G6", include: "values,formulas", tableMaxRows: 6, tableMaxCols: 7 }),
  await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" }),
];

for (const sheetName of [
  "PROJECT TASKS DASHBOARD",
  "PROJECT TASKS",
  "DAILY TASK PLAN",
  "CHECKLIST TASK DETAIL",
  "DAILY STANDUP LOG",
  "TASK REVIEW - QA",
  "INTERNS PERFORMANCE TRACKING",
]) {
  await workbook.render({ sheetName, range: sheetName === "DAILY STANDUP LOG" ? "A1:G18" : undefined, scale: 1 });
}

const outputDir = path.resolve("outputs", "daily-plan-construction-internship");
await fs.mkdir(outputDir, { recursive: true });
const outputPath = path.join(outputDir, "daily_plan_construction_project_tasks_professional.xlsx");
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);

console.log(JSON.stringify({
  outputPath,
  sheetCount: 7,
  taskCount: tasks.length,
  projectTaskCount: projectTasks.length,
  checklistCount: checklists.length,
  standupCount: standups.length,
  qaCount: qaRows.length,
  verification: checks.map((check) => check.ndjson.split("\n")[0]),
}, null, 2));
