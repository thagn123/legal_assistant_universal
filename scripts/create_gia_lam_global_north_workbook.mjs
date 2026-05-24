import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const workbook = Workbook.create();

workbook.setColorScheme({
  name: "Gia Lam Construction Ops",
  themeColors: {
    accent1: "#1F4E5F",
    accent2: "#C87522",
    accent3: "#2F7D32",
    accent4: "#4357AD",
    accent5: "#0E7490",
    accent6: "#B42318",
    dk1: "#111827",
    lt1: "#FFFFFF",
    lt2: "#E5E7EB",
    hlink: "#1D4ED8",
    folHlink: "#6D28D9",
  },
});

const d = (iso) => {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
};

const company = {
  name: "Công ty CP Xây dựng & Vận hành Tài chính Gia Lâm",
  office: "Trụ sở vận hành: Gia Lâm, Hà Nội",
  scope: "Tuyến dự án chính: Quảng Bình - miền Bắc | Có báo cáo/đối tác toàn cầu",
  week: "Tuần vận hành: 18/05/2026 - 22/05/2026",
};

const people = [
  ["Nguyễn Văn Hưng", "Manager", "Giám đốc tài chính nội bộ"],
  ["Trần Thị Mai", "Senior", "Trưởng nhóm hợp đồng"],
  ["Phạm Quốc Bảo", "Manager", "Quản lý vận hành dự án"],
  ["Đỗ Thu Hà", "Senior", "Kế toán tổng hợp cao cấp"],
  ["Vũ Minh Khoa", "Senior", "Kiểm soát tiến độ & chi phí"],
  ["Lê Minh Anh", "Intern", "Thực tập sinh tài chính"],
  ["Phạm Gia Huy", "Intern", "Thực tập sinh hợp đồng"],
  ["Ngô Thảo Vy", "Intern", "Thực tập sinh kế toán"],
  ["Hoàng Đức Nam", "Intern", "Thực tập sinh hành chính dự án"],
  ["Bùi Khánh Linh", "Intern", "Thực tập sinh báo cáo"],
];

const interns = people.filter((p) => p[1] === "Intern").map((p) => p[0]);

const projects = [
  ["QB-LOG-26", "Trung tâm logistics Đồng Hới", "Quảng Bình", "Miền Trung ra Bắc", "Kho vận & hạ tầng", "Aster Global Logistics", "Quản lý hợp đồng EPC, thanh toán nhà thầu, hồ sơ nghiệm thu"],
  ["NA-IND-26", "Nhà xưởng phụ trợ VSIP Nghệ An", "Nghệ An", "Bắc Trung Bộ", "Công nghiệp", "NordBuild Asia", "Theo dõi chi phí vật liệu, nghiệm thu M&E, thanh toán theo milestone"],
  ["TH-HOU-26", "Khu nhà ở công nhân Nghi Sơn", "Thanh Hóa", "Bắc Trung Bộ", "Dân dụng", "BlueRiver Housing", "Chuẩn hóa phụ lục hợp đồng, đối soát công nợ nhà thầu phụ"],
  ["NB-ENE-26", "Trạm vận hành năng lượng Ninh Bình", "Ninh Bình", "Đồng bằng Bắc Bộ", "Năng lượng", "Korea E&C Services", "Báo cáo song ngữ, kiểm tra chứng từ ngân hàng, kiểm toán nội bộ"],
  ["HN-GL-26", "Văn phòng điều hành Gia Lâm", "Hà Nội", "Trụ sở", "Vận hành nội bộ", "Nội bộ công ty", "Điều phối hồ sơ, chuẩn hóa file Excel, quản trị task intern"],
  ["BN-ELC-26", "Nhà máy linh kiện điện tử Bắc Ninh", "Bắc Ninh", "Vùng công nghiệp Bắc Bộ", "Công nghiệp công nghệ cao", "Sakura Engineering", "Quản lý hợp đồng song ngữ, báo cáo chi phí cho đối tác quốc tế"],
  ["HP-CLD-26", "Kho lạnh cảng Hải Phòng", "Hải Phòng", "Duyên hải Bắc Bộ", "Logistics lạnh", "Global ColdChain APAC", "Đối soát thanh toán nhà thầu, chứng từ nhập khẩu thiết bị"],
  ["QN-INF-26", "Hạ tầng phụ trợ Cẩm Phả", "Quảng Ninh", "Đông Bắc Bộ", "Hạ tầng", "Pacific Infra Group", "Theo dõi nghiệm thu khối lượng, chi phí vận chuyển vật liệu"],
  ["LS-BDR-26", "Kho trung chuyển cửa khẩu Lạng Sơn", "Lạng Sơn", "Biên giới phía Bắc", "Kho bãi", "TransAsia Supply", "Hồ sơ pháp lý, thanh toán nhà thầu địa phương, báo cáo tiến độ"],
];

const taskCatalog = [
  ["Hợp đồng", "Rà soát điều khoản thanh toán hợp đồng thi công", "Kiểm tra tạm ứng, giữ lại bảo hành, mốc nghiệm thu", "Trần Thị Mai", "Cao", 2.5],
  ["Tài chính", "Tạo lệnh chuyển tiền cho nhà thầu theo milestone", "Đối chiếu hạn mức duyệt, số tài khoản và mã dự án", "Nguyễn Văn Hưng", "Cao", 1.5],
  ["Tài chính", "Đối soát chi phí vật liệu với bảng nhập kho", "Tách thép, xi măng, cát đá, vật tư phụ", "Đỗ Thu Hà", "Cao", 3],
  ["Báo cáo", "Cập nhật báo cáo tiến độ chi phí gửi đối tác toàn cầu", "Chuẩn hóa tiếng Việt/tiếng Anh cho summary", "Vũ Minh Khoa", "Trung bình", 3],
  ["Kiểm toán", "Kiểm tra chứng từ ngân hàng cho khoản tạm ứng", "So khớp sao kê, phiếu đề nghị chi và phê duyệt", "Đỗ Thu Hà", "Cao", 2],
  ["Hành chính", "Scan và đặt tên bộ hồ sơ nghiệm thu theo mã dự án", "Đặt tên file theo chuẩn YYYYMMDD_Project_Vendor", "Vũ Minh Khoa", "Thấp", 2],
  ["Hợp đồng", "Chuẩn hóa phụ lục phát sinh khối lượng", "So sánh BOQ, phụ lục và bản hợp đồng ký", "Trần Thị Mai", "Trung bình", 2.5],
  ["Báo cáo", "Lập bảng tổng hợp công nợ nhà thầu phụ", "Nhóm theo dự án, hợp đồng, hạn thanh toán", "Nguyễn Văn Hưng", "Cao", 3.5],
  ["Kế toán", "Nhập hóa đơn đầu vào vào file kế toán nội bộ", "Kiểm tra MST, VAT, mã công trình", "Đỗ Thu Hà", "Trung bình", 3],
  ["Kiểm toán", "Tổng hợp danh mục chứng từ còn thiếu", "Ưu tiên giao dịch trên 200 triệu và hồ sơ thanh toán", "Đỗ Thu Hà", "Trung bình", 3],
];

const statusCycle = ["Hoàn thành", "Đang xử lý", "Chưa bắt đầu", "Bị chặn", "Chờ duyệt", "Chưa bắt đầu"];
const ownerCycle = ["Lê Minh Anh", "Phạm Gia Huy", "Ngô Thảo Vy", "Hoàng Đức Nam", "Bùi Khánh Linh", "Trần Thị Mai", "Đỗ Thu Hà", "Vũ Minh Khoa", "Nguyễn Văn Hưng", "Phạm Quốc Bảo"];
const dateCycle = [d("2026-05-18"), d("2026-05-19"), d("2026-05-20"), d("2026-05-21"), d("2026-05-22")];

function roleOf(name) {
  return people.find((p) => p[0] === name)?.[1] ?? "Senior";
}

function nextAction(status, priority) {
  if (status === "Bị chặn") return "Escalate chứng từ thiếu và chốt người chịu trách nhiệm trong ngày";
  if (status === "Đang xử lý") return priority === "Cao" ? "Gửi bản nháp cho senior trước 15:00" : "Cập nhật tiến độ trước standup";
  if (status === "Chờ duyệt") return "Chờ reviewer xác nhận, chuẩn bị file nguồn để đối chiếu";
  if (status === "Hoàn thành") return "Lưu bằng chứng hoàn thành và chuyển QA đóng task";
  return priority === "Cao" ? "Bắt đầu trong ngày, ưu tiên hồ sơ thanh toán/đối tác" : "Xếp lịch xử lý và xác nhận file đầu vào";
}

const projectTasks = Array.from({ length: 48 }, (_, i) => {
  const project = projects[i % projects.length];
  const catalog = taskCatalog[i % taskCatalog.length];
  const owner = ownerCycle[i % ownerCycle.length];
  const status = statusCycle[(i + Math.floor(i / 7)) % statusCycle.length];
  const taskId = `GL-${String(i + 1).padStart(3, "0")}`;
  return [
    taskId,
    project[0],
    project[1],
    project[2],
    project[3],
    catalog[0],
    `${catalog[1]} - ${project[1]}`,
    owner,
    roleOf(owner),
    catalog[4],
    catalog[5],
    status,
    dateCycle[i % dateCycle.length],
    catalog[3],
    nextAction(status, catalog[4]),
    catalog[2],
  ];
});

const dailyTasks = projectTasks.map((row) => [
  row[0],
  row[12],
  row[1],
  row[3],
  row[7],
  row[8],
  row[6],
  row[5],
  row[9],
  row[10],
  row[11],
  row[13],
  row[15],
]);

const checklistRows = projectTasks.slice(0, 20).map((row) => [
  row[0],
  row[6],
  `1. Mở file nguồn và kiểm tra đúng mã dự án ${row[1]}\n2. Đối chiếu hợp đồng, chứng từ hoặc bảng Excel liên quan\n3. Ghi rõ dòng lệch, số tiền lệch hoặc điều khoản cần sửa\n4. Lưu bản working và bản final vào thư mục dự án\n5. Gửi senior review kèm link file`,
  row[5] === "Hợp đồng" ? "Hợp đồng DOCX/PDF, phụ lục, BOQ Excel" : row[5] === "Tài chính" || row[5] === "Kế toán" ? "Excel kế toán, hóa đơn PDF, sao kê ngân hàng" : "Excel báo cáo, PDF chứng từ, folder dự án",
  row[5] === "Báo cáo" ? "Số liệu khớp file nguồn; có ghi ngày chốt dữ liệu và người xác nhận" : "Không thiếu mã dự án; số tiền/ngày/chứng từ khớp 100%; có note cho mọi ngoại lệ",
  row[7],
  row[11] === "Hoàn thành" ? "Đã duyệt" : row[11] === "Bị chặn" ? "Từ chối tạm thời" : "Chờ duyệt",
]);

const standupRows = people.flatMap(([name, role], personIndex) =>
  dateCycle.map((date, dayIndex) => {
    const related = projectTasks[(personIndex * 5 + dayIndex) % projectTasks.length];
    return [
      date,
      name,
      role,
      `Đã xử lý ${related[0]} cho ${related[2]}`,
      `Tiếp tục ${related[5].toLowerCase()} và cập nhật trạng thái task liên quan`,
      related[11] === "Bị chặn" ? "Thiếu chứng từ từ nhà thầu/ban dự án địa phương" : "Không có vướng mắc lớn",
      role === "Intern" ? "Cần senior kiểm tra file trước khi gửi manager" : "Cần team cập nhật file nguồn đúng giờ",
      role === "Manager" ? "Theo dõi task cao ưu tiên và blocker trong ngày" : "Cập nhật trước 16:30, ghi rõ mã dự án",
    ];
  }),
);

const qaRows = projectTasks.slice(0, 32).map((row, idx) => {
  const result = row[11] === "Hoàn thành" ? "Đạt" : row[11] === "Bị chặn" ? "Chưa đạt" : idx % 3 === 0 ? "Cần sửa" : "Đang review";
  return [
    row[0],
    idx % 2 === 0 ? "Đỗ Thu Hà" : idx % 3 === 0 ? "Trần Thị Mai" : "Vũ Minh Khoa",
    result,
    result === "Đạt"
      ? "Hồ sơ đầy đủ, số liệu khớp và đã lưu bằng chứng review."
      : result === "Chưa đạt"
        ? "Thiếu chứng từ hoặc xác nhận từ dự án địa phương; chưa được đóng task."
        : "Bổ sung nguồn dữ liệu, link file và ghi rõ ngoại lệ trước khi nộp lại.",
    result === "Đạt" ? "" : dateCycle[(idx + 2) % dateCycle.length],
    result === "Đạt" ? "Đóng" : result === "Chưa đạt" ? "Mở lại" : "Chờ nộp lại",
    row[7],
  ];
});

const internComments = {
  "Lê Minh Anh": "Nắm luồng thanh toán tốt, cần kiểm tra kỹ thông tin tài khoản nhà thầu trước khi tạo lệnh.",
  "Phạm Gia Huy": "Cẩn thận với hợp đồng và phụ lục, nên gắn nguồn điều khoản rõ hơn khi gửi senior.",
  "Ngô Thảo Vy": "Nhập liệu đều, cần checklist MST/VAT/chứng từ kho trước khi chốt file.",
  "Hoàng Đức Nam": "Hỗ trợ scan và lưu trữ tốt, cần kiểm tra chất lượng PDF và quy ước đặt tên.",
  "Bùi Khánh Linh": "Có tư duy báo cáo, cần khóa nguồn dữ liệu và kiểm tra pivot trước khi gửi quản lý.",
};

const performanceRows = interns.map((name) => [name, null, null, null, null, null, internComments[name]]);

function columnLetter(index) {
  let n = index;
  let result = "";
  while (n > 0) {
    const m = (n - 1) % 26;
    result = String.fromCharCode(65 + m) + result;
    n = Math.floor((n - m) / 26);
  }
  return result;
}

function setWidths(sheet, widths) {
  widths.forEach((width, idx) => {
    sheet.getRange(`${columnLetter(idx + 1)}:${columnLetter(idx + 1)}`).format.columnWidthPx = width;
  });
}

function addDataSheet(name, headers, rows, color, tableName, widths) {
  const sheet = workbook.worksheets.add(name);
  const lastCol = columnLetter(headers.length);
  const lastRow = rows.length + 1;
  sheet.getRange(`A1:${lastCol}${lastRow}`).values = [headers, ...rows];
  const used = sheet.getRange(`A1:${lastCol}${lastRow}`);
  used.format = {
    font: { name: "Arial", size: 10, color: "#111827" },
    verticalAlignment: "top",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#D1D5DB" },
  };
  sheet.getRange(`A1:${lastCol}1`).format = {
    fill: color,
    font: { name: "Arial", size: 10, color: "#FFFFFF", bold: true },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#9CA3AF" },
  };
  const table = sheet.tables.add(used, true);
  table.name = tableName;
  table.style = "TableStyleMedium2";
  setWidths(sheet, widths);
  sheet.freezePanes.freezeRows(1);
  used.format.autofitRows();
  return sheet;
}

const projectSheet = addDataSheet(
  "02_DANH_MUC_DU_AN",
  ["Mã dự án", "Tên dự án", "Tỉnh/Thành", "Vùng", "Loại dự án", "Đối tác/khách hàng", "Phạm vi vận hành nội bộ"],
  projects,
  "#1F4E5F",
  "tblDanhMucDuAn",
  [95, 240, 120, 155, 150, 190, 420],
);

const taskSheet = addDataSheet(
  "03_PROJECT_TASKS",
  ["Task ID", "Mã dự án", "Tên dự án", "Tỉnh/Thành", "Vùng", "Nhóm việc", "Tên công việc", "Người phụ trách", "Vai trò", "Ưu tiên", "Giờ dự kiến", "Trạng thái", "Hạn xử lý", "Người giao", "Hành động tiếp theo", "Ghi chú nghiệp vụ"],
  projectTasks,
  "#244C5A",
  "tblProjectTasks",
  [78, 95, 230, 105, 150, 105, 330, 150, 95, 85, 85, 115, 95, 150, 330, 310],
);
taskSheet.getRange("K2:K49").format.numberFormat = "0.0";
taskSheet.getRange("M2:M49").format.numberFormat = "yyyy-mm-dd";
taskSheet.getRange("J2:J49").conditionalFormats.add("containsText", { text: "Cao", format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } } });
taskSheet.getRange("L2:L49").conditionalFormats.add("containsText", { text: "Hoàn thành", format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } } });
taskSheet.getRange("L2:L49").conditionalFormats.add("containsText", { text: "Bị chặn", format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } } });
taskSheet.getRange("L2:L49").conditionalFormats.add("containsText", { text: "Đang xử lý", format: { fill: "#DBEAFE", font: { color: "#1D4ED8" } } });

const dailySheet = addDataSheet(
  "04_KE_HOACH_NGAY",
  ["Task ID", "Ngày", "Mã dự án", "Tỉnh/Thành", "Tên nhân sự", "Vai trò", "Tên công việc", "Nhóm việc", "Ưu tiên", "Giờ dự kiến", "Trạng thái", "Người giao", "Ghi chú"],
  dailyTasks,
  "#1F4E78",
  "tblKeHoachNgay",
  [78, 95, 95, 105, 150, 95, 330, 105, 85, 85, 115, 150, 330],
);
dailySheet.getRange("B2:B49").format.numberFormat = "yyyy-mm-dd";
dailySheet.getRange("J2:J49").format.numberFormat = "0.0";

const checklistSheet = addDataSheet(
  "05_CHECKLIST_CHI_TIET",
  ["Task ID", "Tên công việc", "Checklist từng bước", "Hồ sơ bắt buộc", "Tiêu chí nghiệm thu", "Người phụ trách", "Trạng thái review"],
  checklistRows,
  "#C87522",
  "tblChecklistChiTiet",
  [78, 300, 440, 270, 360, 150, 130],
);

const standupSheet = addDataSheet(
  "06_STANDUP_HANG_NGAY",
  ["Ngày", "Tên nhân sự", "Vai trò", "Hôm qua đã làm", "Kế hoạch hôm nay", "Vướng mắc", "Cần hỗ trợ", "Nhận xét quản lý"],
  standupRows,
  "#2F7D32",
  "tblStandupHangNgay",
  [95, 150, 95, 270, 280, 260, 260, 260],
);
standupSheet.getRange("A2:A51").format.numberFormat = "yyyy-mm-dd";

const qaSheet = addDataSheet(
  "07_QA_REVIEW",
  ["Task ID", "Reviewer", "Kết quả review", "Feedback chi tiết", "Hạn nộp lại", "Trạng thái cuối", "Người phụ trách"],
  qaRows,
  "#B42318",
  "tblQAReview",
  [78, 150, 125, 380, 100, 135, 150],
);
qaSheet.getRange("E2:E33").format.numberFormat = "yyyy-mm-dd";
qaSheet.getRange("C2:C33").conditionalFormats.add("containsText", { text: "Đạt", format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } } });
qaSheet.getRange("C2:C33").conditionalFormats.add("containsText", { text: "Cần sửa", format: { fill: "#FEF3C7", font: { color: "#92400E", bold: true } } });
qaSheet.getRange("C2:C33").conditionalFormats.add("containsText", { text: "Chưa đạt", format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } } });

const performanceSheet = addDataSheet(
  "08_HIEU_SUAT_INTERN",
  ["Tên intern", "Tổng task được giao", "Task hoàn thành", "Thời gian hoàn thành TB", "Tỷ lệ lỗi/rework", "Điểm review (1-10)", "Nhận xét tuần từ quản lý"],
  performanceRows,
  "#4357AD",
  "tblHieuSuatIntern",
  [150, 120, 110, 135, 110, 120, 460],
);

const formulas = interns.map((_, idx) => {
  const row = idx + 2;
  return [
    `=COUNTIF('03_PROJECT_TASKS'!H2:H49,A${row})`,
    `=COUNTIFS('03_PROJECT_TASKS'!H2:H49,A${row},'03_PROJECT_TASKS'!L2:L49,"Hoàn thành")`,
    `=IFERROR(AVERAGEIFS('03_PROJECT_TASKS'!K2:K49,'03_PROJECT_TASKS'!H2:H49,A${row},'03_PROJECT_TASKS'!L2:L49,"Hoàn thành"),0)`,
    `=IFERROR((COUNTIFS('07_QA_REVIEW'!G2:G33,A${row},'07_QA_REVIEW'!C2:C33,"Cần sửa")+COUNTIFS('07_QA_REVIEW'!G2:G33,A${row},'07_QA_REVIEW'!C2:C33,"Chưa đạt"))/COUNTIF('07_QA_REVIEW'!G2:G33,A${row}),0)`,
    `=IFERROR(ROUND(MIN(10,MAX(1,7+(C${row}/B${row})*2.5-E${row}*5)),1),0)`,
  ];
});
performanceSheet.getRange("B2:F6").formulas = formulas;
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

const dashboard = workbook.worksheets.add("01_TONG_QUAN_DIEU_HANH");
setWidths(dashboard, [135, 95, 24, 135, 95, 24, 135, 95, 24, 135, 95, 24, 150, 120, 120, 120]);
dashboard.getRange("A1:P1").format = { fill: "#1F4E5F", font: { name: "Arial", size: 16, color: "#FFFFFF", bold: true }, verticalAlignment: "center", wrapText: true };
dashboard.getRange("A1").values = [[company.name]];
dashboard.getRange("A2:P2").format = { fill: "#E5E7EB", font: { name: "Arial", size: 10, color: "#374151", italic: true }, wrapText: true };
dashboard.getRange("A2").values = [[`${company.office} | ${company.scope} | ${company.week}`]];

dashboard.getRange("A4:K5").values = [
  ["Tổng task", "", "Tỷ lệ hoàn thành", "", "Task bị chặn", "", "Task ưu tiên cao", "", "Tổng giờ dự kiến", ""],
  [null, "", null, "", null, "", null, "", null, ""],
];
dashboard.getRange("A5").formulas = [["=COUNTA('03_PROJECT_TASKS'!A2:A49)"]];
dashboard.getRange("C5").formulas = [["=IFERROR(COUNTIF('03_PROJECT_TASKS'!L2:L49,\"Hoàn thành\")/COUNTA('03_PROJECT_TASKS'!A2:A49),0)"]];
dashboard.getRange("E5").formulas = [["=COUNTIF('03_PROJECT_TASKS'!L2:L49,\"Bị chặn\")"]];
dashboard.getRange("G5").formulas = [["=COUNTIF('03_PROJECT_TASKS'!J2:J49,\"Cao\")"]];
dashboard.getRange("I5").formulas = [["=SUM('03_PROJECT_TASKS'!K2:K49)"]];
dashboard.getRange("A4:K5").format = {
  fill: "#F8FAFC",
  font: { name: "Arial", size: 10, color: "#111827", bold: true },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  borders: { preset: "all", style: "thin", color: "#CBD5E1" },
};
dashboard.getRange("A5:K5").format.font = { name: "Arial", size: 16, color: "#1F4E5F", bold: true };
dashboard.getRange("C5").format.numberFormat = "0%";
dashboard.getRange("I5").format.numberFormat = "0.0";

dashboard.getRange("A8:C13").values = [
  ["Trạng thái", "Số task", "Tỷ trọng"],
  ["Chưa bắt đầu", null, null],
  ["Đang xử lý", null, null],
  ["Chờ duyệt", null, null],
  ["Hoàn thành", null, null],
  ["Bị chặn", null, null],
];
dashboard.getRange("B9:B13").formulas = [["=COUNTIF('03_PROJECT_TASKS'!L2:L49,A9)"], ["=COUNTIF('03_PROJECT_TASKS'!L2:L49,A10)"], ["=COUNTIF('03_PROJECT_TASKS'!L2:L49,A11)"], ["=COUNTIF('03_PROJECT_TASKS'!L2:L49,A12)"], ["=COUNTIF('03_PROJECT_TASKS'!L2:L49,A13)"]];
dashboard.getRange("C9:C13").formulas = [["=IFERROR(B9/SUM($B$9:$B$13),0)"], ["=IFERROR(B10/SUM($B$9:$B$13),0)"], ["=IFERROR(B11/SUM($B$9:$B$13),0)"], ["=IFERROR(B12/SUM($B$9:$B$13),0)"], ["=IFERROR(B13/SUM($B$9:$B$13),0)"]];
dashboard.getRange("C9:C13").format.numberFormat = "0%";

dashboard.getRange("E8:H17").values = [
  ["Tỉnh/Thành", "Số task", "Ưu tiên cao", "Bị chặn"],
  ...projects.map((project) => [project[2], null, null, null]),
];
dashboard.getRange("F9:H17").formulas = projects.map((_, idx) => {
  const row = idx + 9;
  return [
    `=COUNTIF('03_PROJECT_TASKS'!D2:D49,E${row})`,
    `=COUNTIFS('03_PROJECT_TASKS'!D2:D49,E${row},'03_PROJECT_TASKS'!J2:J49,"Cao")`,
    `=COUNTIFS('03_PROJECT_TASKS'!D2:D49,E${row},'03_PROJECT_TASKS'!L2:L49,"Bị chặn")`,
  ];
});

dashboard.getRange("J8:O13").values = [["Intern", "Tổng task", "Hoàn thành", "Bị chặn", "Tỷ lệ lỗi", "Điểm"], ...interns.map((name) => [name, null, null, null, null, null])];
dashboard.getRange("K9:O13").formulas = interns.map((_, idx) => {
  const row = idx + 9;
  return [
    `=COUNTIF('03_PROJECT_TASKS'!H2:H49,J${row})`,
    `=COUNTIFS('03_PROJECT_TASKS'!H2:H49,J${row},'03_PROJECT_TASKS'!L2:L49,"Hoàn thành")`,
    `=COUNTIFS('03_PROJECT_TASKS'!H2:H49,J${row},'03_PROJECT_TASKS'!L2:L49,"Bị chặn")`,
    `=IFERROR(VLOOKUP(J${row},'08_HIEU_SUAT_INTERN'!A2:F6,5,FALSE),0)`,
    `=IFERROR(VLOOKUP(J${row},'08_HIEU_SUAT_INTERN'!A2:F6,6,FALSE),0)`,
  ];
});
dashboard.getRange("N9:N13").format.numberFormat = "0%";
dashboard.getRange("O9:O13").format.numberFormat = "0.0";

const dashboardTables = ["A8:C13", "E8:H17", "J8:O13"];
for (const range of dashboardTables) {
  dashboard.getRange(range).format = {
    font: { name: "Arial", size: 10, color: "#111827" },
    verticalAlignment: "top",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#CBD5E1" },
  };
}
dashboard.getRange("A8:C8").format.fill = "#1F4E5F";
dashboard.getRange("E8:H8").format.fill = "#C87522";
dashboard.getRange("J8:O8").format.fill = "#4357AD";
dashboard.getRange("A8:C8").format.font = { name: "Arial", size: 10, color: "#FFFFFF", bold: true };
dashboard.getRange("E8:H8").format.font = { name: "Arial", size: 10, color: "#FFFFFF", bold: true };
dashboard.getRange("J8:O8").format.font = { name: "Arial", size: 10, color: "#FFFFFF", bold: true };

const urgent = projectTasks
  .filter((row) => row[9] === "Cao" && row[11] !== "Hoàn thành")
  .slice(0, 9)
  .map((row) => [row[0], row[1], row[3], row[5], row[7], row[11], row[12], row[14]]);
dashboard.getRange("A20:H20").values = [["Task ID", "Mã dự án", "Tỉnh/Thành", "Nhóm việc", "Phụ trách", "Trạng thái", "Hạn xử lý", "Hành động tiếp theo"]];
dashboard.getRange(`A21:H${20 + urgent.length}`).values = urgent;
dashboard.getRange(`G21:G${20 + urgent.length}`).format.numberFormat = "yyyy-mm-dd";
dashboard.getRange("A20:H29").format = {
  font: { name: "Arial", size: 10, color: "#111827" },
  verticalAlignment: "top",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#CBD5E1" },
};
dashboard.getRange("A20:H20").format = {
  fill: "#B42318",
  font: { name: "Arial", size: 10, color: "#FFFFFF", bold: true },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
dashboard.getRange("A1:P29").format.autofitRows();
dashboard.freezePanes.freezeRows(2);

dashboard.charts.add("ColumnClustered", {
  title: "Task theo trạng thái",
  categories: ["Chưa bắt đầu", "Đang xử lý", "Chờ duyệt", "Hoàn thành", "Bị chặn"],
  series: [{
    name: "Số task",
    values: ["Chưa bắt đầu", "Đang xử lý", "Chờ duyệt", "Hoàn thành", "Bị chặn"].map((status) => projectTasks.filter((row) => row[11] === status).length),
  }],
  hasLegend: false,
  from: { row: 18, col: 9 },
  extent: { widthPx: 520, heightPx: 260 },
  barOptions: { direction: "column", grouping: "clustered", gapWidth: 80 },
});

const checks = [
  await workbook.inspect({ kind: "table", range: "01_TONG_QUAN_DIEU_HANH!A1:O13", include: "values,formulas", tableMaxRows: 13, tableMaxCols: 15 }),
  await workbook.inspect({ kind: "sheet,table", search: "PROJECT_TASKS|KE_HOACH|HIEU_SUAT", include: "values", tableMaxRows: 3, tableMaxCols: 8, maxChars: 6000 }),
  await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" }),
];

for (const sheetName of [
  "01_TONG_QUAN_DIEU_HANH",
  "02_DANH_MUC_DU_AN",
  "03_PROJECT_TASKS",
  "04_KE_HOACH_NGAY",
  "05_CHECKLIST_CHI_TIET",
  "06_STANDUP_HANG_NGAY",
  "07_QA_REVIEW",
  "08_HIEU_SUAT_INTERN",
]) {
  await workbook.render({ sheetName, range: sheetName === "06_STANDUP_HANG_NGAY" ? "A1:H18" : undefined, scale: 1 });
}

const outputDir = path.resolve("outputs", "daily-plan-construction-internship");
await fs.mkdir(outputDir, { recursive: true });
const outputPath = path.join(outputDir, "ke_hoach_cong_viec_gia_lam_global_mien_bac.xlsx");
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);

console.log(JSON.stringify({
  outputPath,
  sheetCount: 8,
  projectCount: projects.length,
  taskCount: projectTasks.length,
  checklistCount: checklistRows.length,
  standupCount: standupRows.length,
  qaCount: qaRows.length,
  verification: checks.map((check) => check.ndjson.split("\n")[0]),
}, null, 2));
