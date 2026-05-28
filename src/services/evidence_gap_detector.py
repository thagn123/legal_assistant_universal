from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class EvidenceItem:
    item: str
    priority: str  # "high" | "medium" | "low"
    category: str = ""


@dataclass
class EvidenceGapResult:
    domain: str
    missing_evidence: List[EvidenceItem]
    strong_evidence: List[str]
    weak_evidence: List[str]
    coverage_score: float  # 0.0 – 1.0
    priority_items: List[EvidenceItem]  # high-priority missing only
    advice: str = ""


_CHECKLISTS: Dict[str, List[EvidenceItem]] = {
    "dat_dai": [
        EvidenceItem("Giấy tờ chuyển nhượng quyền sử dụng đất (giấy tay hoặc công chứng)", "high", "title"),
        EvidenceItem("Biên lai hoặc chứng từ thanh toán tiền mua đất", "high", "payment"),
        EvidenceItem("Xác nhận của UBND xã/phường về quyền sử dụng đất", "high", "confirmation"),
        EvidenceItem("Sổ đỏ / Giấy chứng nhận quyền sử dụng đất", "high", "certificate"),
        EvidenceItem("Bản đồ địa chính / sơ đồ thửa đất", "medium", "map"),
        EvidenceItem("Nhân chứng tham gia giao dịch", "medium", "witness"),
        EvidenceItem("Ảnh chụp hiện trạng thửa đất", "medium", "photo"),
        EvidenceItem("Hợp đồng công chứng (nếu có)", "medium", "notarized"),
        EvidenceItem("Thông báo về tranh chấp gửi cơ quan có thẩm quyền", "low", "notice"),
    ],
    "hop_dong": [
        EvidenceItem("Bản hợp đồng gốc có chữ ký đầy đủ các bên", "high", "contract"),
        EvidenceItem("Phụ lục hợp đồng (nếu có)", "high", "appendix"),
        EvidenceItem("Chứng từ thanh toán / biên lai giao nhận tiền", "high", "payment"),
        EvidenceItem("Biên bản bàn giao hàng hoá hoặc dịch vụ", "high", "delivery"),
        EvidenceItem("Văn bản thông báo vi phạm hợp đồng", "high", "notice"),
        EvidenceItem("Email / tin nhắn trao đổi liên quan", "medium", "communication"),
        EvidenceItem("Hợp đồng công chứng tại văn phòng công chứng", "medium", "notarized"),
        EvidenceItem("Biên bản giám định chất lượng (nếu tranh chấp chất lượng)", "medium", "inspection"),
        EvidenceItem("Bảo lãnh thực hiện hợp đồng (nếu có)", "low", "guarantee"),
    ],
    "lao_dong": [
        EvidenceItem("Hợp đồng lao động / phụ lục hợp đồng", "high", "contract"),
        EvidenceItem("Quyết định sa thải hoặc chấm dứt hợp đồng", "high", "termination"),
        EvidenceItem("Bảng lương / phiếu lương các tháng", "high", "salary"),
        EvidenceItem("Sổ bảo hiểm xã hội", "high", "insurance"),
        EvidenceItem("Nội quy lao động đã đăng ký", "medium", "rules"),
        EvidenceItem("Biên bản họp xét kỷ luật", "medium", "disciplinary"),
        EvidenceItem("Thông báo nghỉ việc có chữ ký", "medium", "notice"),
        EvidenceItem("Chứng cứ về thời gian làm việc (chấm công)", "medium", "attendance"),
        EvidenceItem("Giấy khám sức khoẻ / biên bản tai nạn lao động (nếu liên quan)", "low", "health"),
    ],
    "doanh_nghiep": [
        EvidenceItem("Giấy chứng nhận đăng ký doanh nghiệp", "high", "registration"),
        EvidenceItem("Điều lệ công ty và các lần sửa đổi", "high", "charter"),
        EvidenceItem("Biên bản họp / Nghị quyết của HĐQT / ĐHĐCĐ", "high", "resolution"),
        EvidenceItem("Hợp đồng góp vốn / chuyển nhượng cổ phần", "high", "share_transfer"),
        EvidenceItem("Báo cáo tài chính đã kiểm toán", "medium", "financial"),
        EvidenceItem("Danh sách cổ đông / thành viên góp vốn", "medium", "shareholders"),
        EvidenceItem("Hồ sơ nộp thuế, khai thuế", "medium", "tax"),
        EvidenceItem("Văn bản uỷ quyền của người đại diện pháp luật", "low", "proxy"),
    ],
    "dan_su": [
        EvidenceItem("Giấy tờ tuỳ thân (CCCD/CMND) của các bên liên quan", "high", "identity"),
        EvidenceItem("Tài liệu chứng minh quyền sở hữu tài sản tranh chấp", "high", "ownership"),
        EvidenceItem("Di chúc hoặc văn bản thỏa thuận phân chia di sản", "high", "will"),
        EvidenceItem("Giấy khai sinh / giấy đăng ký kết hôn", "high", "family"),
        EvidenceItem("Chứng từ thanh toán / biên lai liên quan tài sản", "medium", "payment"),
        EvidenceItem("Nhân chứng biết về giao dịch hoặc sự kiện tranh chấp", "medium", "witness"),
        EvidenceItem("Văn bản thoả thuận hoặc thư từ giữa các bên", "medium", "agreement"),
        EvidenceItem("Giấy tờ chứng minh thiệt hại (hoa lợi, lợi tức bị mất)", "low", "damage"),
    ],
    "hinh_su": [
        EvidenceItem("Biên bản ghi nhận tại chỗ của cơ quan công an", "high", "police_report"),
        EvidenceItem("Biên bản giám định / kết luận giám định pháp y", "high", "forensic"),
        EvidenceItem("Chứng cứ vật chất (tang vật, vật chứng)", "high", "physical"),
        EvidenceItem("Lời khai của nhân chứng", "high", "testimony"),
        EvidenceItem("Camera / video / ảnh ghi lại sự việc", "high", "video"),
        EvidenceItem("Kết quả giám định ADN / dấu vân tay (nếu cần)", "medium", "dna"),
        EvidenceItem("Hồ sơ bệnh án / giấy chứng thương", "medium", "medical"),
        EvidenceItem("Thông tin trích xuất từ thiết bị điện tử", "medium", "digital"),
        EvidenceItem("Đơn tố cáo, khởi kiện đã nộp", "low", "complaint"),
    ],
    "hanh_chinh": [
        EvidenceItem("Quyết định hành chính bị khiếu nại", "high", "decision"),
        EvidenceItem("Đơn khiếu nại / khiếu kiện đã nộp và xác nhận tiếp nhận", "high", "complaint"),
        EvidenceItem("Văn bản trả lời của cơ quan nhà nước", "high", "response"),
        EvidenceItem("Chứng cứ thiệt hại do quyết định hành chính gây ra", "high", "damage"),
        EvidenceItem("Hồ sơ hành chính liên quan (giấy phép, đăng ký)", "medium", "admin_docs"),
        EvidenceItem("Biên bản thanh kiểm tra của cơ quan nhà nước", "medium", "inspection"),
        EvidenceItem("Căn cứ pháp lý mà quyết định hành chính vi phạm", "medium", "legal_basis"),
        EvidenceItem("Thời hạn khiếu nại còn trong hạn hay đã hết hạn", "low", "deadline"),
    ],
    "gia_dinh": [
        EvidenceItem("Giấy đăng ký kết hôn", "high", "marriage"),
        EvidenceItem("Giấy khai sinh của con", "high", "birth"),
        EvidenceItem("Bản thoả thuận ly hôn (nếu có) hoặc đơn ly hôn", "high", "divorce"),
        EvidenceItem("Tài liệu về tài sản chung (sổ đỏ, sổ tiết kiệm, xe)", "high", "assets"),
        EvidenceItem("Chứng cứ về hành vi bạo lực gia đình (nếu có)", "high", "abuse"),
        EvidenceItem("Thông tin thu nhập / tài chính của các bên", "medium", "income"),
        EvidenceItem("Đánh giá của cơ sở y tế về sức khoẻ tinh thần (nếu liên quan)", "medium", "health"),
        EvidenceItem("Bằng chứng về khả năng nuôi dưỡng con (nhà ở, thu nhập)", "medium", "custody"),
        EvidenceItem("Lịch sử liên lạc, tin nhắn liên quan đến mâu thuẫn", "low", "communication"),
    ],
    "general": [
        EvidenceItem("Giấy tờ tuỳ thân (CCCD/CMND) của người liên quan", "high", "identity"),
        EvidenceItem("Tài liệu, hợp đồng chứng minh quyền lợi bị xâm phạm", "high", "core_document"),
        EvidenceItem("Chứng cứ thiệt hại (tài chính hoặc phi tài chính)", "high", "damage"),
        EvidenceItem("Nhân chứng biết về sự việc", "medium", "witness"),
        EvidenceItem("Thư từ, email, tin nhắn giữa các bên", "medium", "communication"),
        EvidenceItem("Văn bản khiếu nại, tố cáo đã nộp trước đó", "low", "prior_complaint"),
    ],
}

_DOMAIN_ADVICE = {
    "dat_dai": "Trong tranh chấp đất đai, sổ đỏ và chứng từ thanh toán là bằng chứng quan trọng nhất. Nếu thiếu, hãy thu thập sớm trước khi khởi kiện.",
    "hop_dong": "Hãy ưu tiên lưu giữ bản hợp đồng gốc và mọi trao đổi bằng văn bản. Email và tin nhắn đều có giá trị pháp lý.",
    "lao_dong": "Trong tranh chấp lao động, hợp đồng lao động và quyết định sa thải là căn cứ chính. Sổ bảo hiểm xã hội cũng cần thiết để tính trợ cấp.",
    "doanh_nghiep": "Điều lệ công ty và biên bản họp HĐQT là tài liệu thiết yếu cho mọi tranh chấp doanh nghiệp.",
    "dan_su": "Trong tranh chấp dân sự, cần xác định rõ quyền sở hữu và chứng minh thiệt hại thực tế.",
    "hinh_su": "Chứng cứ hình sự phải được thu thập đúng trình tự — không tự ý di chuyển tang vật, báo cáo ngay cho công an.",
    "hanh_chinh": "Lưu ý thời hạn khiếu nại hành chính: 90 ngày kể từ khi biết về quyết định. Hết hạn có thể mất quyền khiếu nại.",
    "gia_dinh": "Trong tranh chấp gia đình, cần chứng minh quyền lợi của trẻ em được đặt lên hàng đầu trong mọi phán quyết về quyền nuôi con.",
    "general": "Hãy xác định rõ lĩnh vực pháp lý của vụ việc để nhận được danh sách chứng cứ cụ thể hơn.",
}

# Phrase-level aliases per category — covers short Vietnamese terms that word-splitting misses.
# "sổ đỏ" (2+2 chars) would be filtered by len>3 word split, so must be matched as a phrase here.
_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "certificate":    ["sổ đỏ", "sổ hồng", "gcnqsd", "giấy chứng nhận quyền sử dụng đất",
                       "giấy chứng nhận qsd", "sổ đỏ/sổ hồng"],
    "payment":        ["biên lai", "chứng từ thanh toán", "hoá đơn", "hoa don", "biên nhận",
                       "chuyển khoản", "bien lai"],
    "title":          ["giấy chuyển nhượng", "giấy tay", "văn bản chuyển nhượng",
                       "hợp đồng mua bán đất", "giấy mua bán"],
    "confirmation":   ["xác nhận ubnd", "xác nhận ủy ban", "ubnd xã", "ubnd phường",
                       "xác nhận của ubnd"],
    "map":            ["bản đồ địa chính", "sơ đồ thửa đất", "bản đồ thửa", "địa chính"],
    "witness":        ["nhân chứng", "người làm chứng", "người chứng kiến"],
    "notarized":      ["công chứng", "hợp đồng công chứng", "văn phòng công chứng"],
    "photo":          ["ảnh chụp", "hình ảnh", "video hiện trạng"],
    "notice":         ["thông báo tranh chấp", "đơn thông báo", "văn bản thông báo"],
    # lao_dong
    "contract":       ["hợp đồng lao động", "hdlđ", "hợp đồng làm việc", "hợp đồng thử việc",
                       "hợp đồng gốc", "bản hợp đồng"],
    "termination":    ["quyết định sa thải", "quyết định chấm dứt", "thông báo sa thải",
                       "quyết định nghỉ việc", "sa thải", "chấm dứt hợp đồng"],
    "salary":         ["bảng lương", "phiếu lương", "bảng công", "bảng chấm công",
                       "slip lương", "phiếu công"],
    "insurance":      ["sổ bảo hiểm", "sổ bhxh", "bhxh", "bảo hiểm xã hội",
                       "sổ bảo hiểm xã hội"],
    "rules":          ["nội quy lao động", "nội quy công ty", "quy chế lao động"],
    "disciplinary":   ["biên bản kỷ luật", "biên bản họp kỷ luật", "quyết định kỷ luật"],
    "attendance":     ["chấm công", "bảng chấm công", "thẻ chấm công", "log chấm công"],
    # dan_su / gia_dinh
    "will":           ["di chúc", "văn bản chia thừa kế", "thoả thuận thừa kế",
                       "phân chia di sản", "di sản"],
    "family":         ["giấy khai sinh", "khai sinh", "giấy đăng ký kết hôn",
                       "đăng ký kết hôn", "giấy tờ gia đình"],
    "identity":       ["cccd", "cmnd", "căn cước công dân", "chứng minh nhân dân",
                       "hộ chiếu", "giấy tờ tuỳ thân"],
    "ownership":      ["chứng nhận sở hữu", "giấy sở hữu", "chứng từ sở hữu"],
    "marriage":       ["đăng ký kết hôn", "giấy đăng ký kết hôn", "hôn thú", "kết hôn"],
    "birth":          ["giấy khai sinh", "khai sinh", "giấy sinh"],
    "divorce":        ["đơn ly hôn", "thoả thuận ly hôn", "quyết định ly hôn", "ly hôn"],
    "assets":         ["sổ đỏ", "sổ tiết kiệm", "đăng ký xe", "đăng ký ô tô",
                       "tài sản chung", "tài sản hôn nhân"],
    "abuse":          ["bạo lực gia đình", "hành vi bạo lực", "chứng cứ bạo lực"],
    "custody":        ["quyền nuôi con", "nuôi dưỡng con", "chăm sóc con"],
    # hinh_su
    "police_report":  ["biên bản công an", "biên bản ghi nhận", "tường trình công an",
                       "báo cáo công an"],
    "forensic":       ["giám định pháp y", "kết luận giám định", "biên bản giám định"],
    "physical":       ["tang vật", "vật chứng", "hiện vật", "tang vật vụ án"],
    "testimony":      ["lời khai", "nhân chứng khai", "lời khai nhân chứng"],
    "video":          ["camera", "video", "clip", "ghi hình", "ảnh ghi lại"],
    "dna":            ["giám định adn", "dấu vân tay", "adn", "xét nghiệm adn"],
    "medical":        ["bệnh án", "giấy chứng thương", "hồ sơ y tế", "bệnh viện"],
    "digital":        ["thiết bị điện tử", "điện thoại", "máy tính", "trích xuất dữ liệu"],
    # hanh_chinh
    "decision":       ["quyết định hành chính", "quyết định của ubnd", "quyết định xử phạt"],
    "complaint":      ["đơn khiếu nại", "đơn tố cáo", "đơn khiếu kiện", "đơn kiện"],
    "response":       ["văn bản trả lời", "công văn trả lời", "trả lời khiếu nại"],
    "damage":         ["thiệt hại", "tổn thất", "chứng cứ thiệt hại"],
    "admin_docs":     ["giấy phép", "đăng ký hành chính", "hồ sơ hành chính"],
    "legal_basis":    ["căn cứ pháp lý", "điều khoản vi phạm", "quy định vi phạm"],
    # doanh_nghiep
    "registration":   ["đăng ký kinh doanh", "đăng ký doanh nghiệp", "giấy phép kinh doanh",
                       "mst", "mã số thuế"],
    "charter":        ["điều lệ công ty", "điều lệ doanh nghiệp"],
    "resolution":     ["biên bản họp hđqt", "nghị quyết hđqt", "biên bản đhđcđ",
                       "nghị quyết đại hội", "biên bản họp"],
    "share_transfer": ["chuyển nhượng cổ phần", "hợp đồng chuyển nhượng cổ phần",
                       "góp vốn", "chuyển nhượng vốn"],
    "financial":      ["báo cáo tài chính", "kiểm toán", "bctc"],
    "shareholders":   ["danh sách cổ đông", "danh sách thành viên", "sổ cổ đông"],
    "tax":            ["hồ sơ thuế", "khai thuế", "nộp thuế", "quyết toán thuế"],
    "proxy":          ["văn bản uỷ quyền", "giấy uỷ quyền", "uỷ quyền"],
    # general
    "core_document":  ["hợp đồng", "tài liệu gốc", "văn bản gốc", "chứng từ"],
    "prior_complaint":["đơn khiếu nại trước", "tố cáo trước đó", "đã khiếu nại"],
    "communication":  ["email", "tin nhắn", "zalo", "messenger", "chat", "trao đổi"],
    "income":         ["thu nhập", "lương", "bảng lương", "sao kê tài khoản"],
    "health":         ["khám sức khoẻ", "bệnh viện", "giấy y tế"],
    "appendix":       ["phụ lục hợp đồng", "phụ lục", "điều khoản bổ sung"],
    "delivery":       ["biên bản bàn giao", "bàn giao hàng", "biên bản nghiệm thu"],
    "inspection":     ["biên bản giám định", "giám định chất lượng", "kiểm tra chất lượng"],
    "guarantee":      ["bảo lãnh", "thư bảo lãnh", "ký quỹ"],
}

# Regex patterns to extract "I already have X" claims from the situation narrative.
_HAS_CLAIM_PATTERNS = [
    r"(?:tôi|mình|chúng tôi)\s+(?:đã\s+)?(?:có|sẵn có|đang có|đang giữ|giữ|lưu giữ)\s+([^,.\n]{4,80})",
    r"(?:đã có|hiện có|sẵn có|đang có|hiện đang có)\s+([^,.\n]{4,80})",
    r"(?:có sẵn|đã lưu giữ|đang lưu giữ)\s+([^,.\n]{4,80})",
    r"(?:tôi|mình)\s+(?:vẫn|đang)\s+(?:giữ|có)\s+([^,.\n]{4,80})",
]


def _extract_claimed_evidence(situation: str) -> List[str]:
    """Extract evidence the user claims to already possess from the situation narrative."""
    claimed: List[str] = []
    for pattern in _HAS_CLAIM_PATTERNS:
        for m in re.finditer(pattern, situation, re.IGNORECASE):
            val = m.group(1).strip().rstrip(".,;")
            if val:
                claimed.append(val)
    return claimed


def _phrase_in_text(text: str, phrases: List[str]) -> bool:
    """Return True if any phrase appears verbatim in text (case-insensitive)."""
    text_l = text.lower()
    return any(p.lower() in text_l for p in phrases)


def _bigrams(words: List[str]) -> List[str]:
    return [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]


def _keywords_match(fact: str, item: EvidenceItem) -> bool:
    fact_lower = fact.lower()

    # 1. Category alias phrases — covers short terms like "sổ đỏ", "di chúc", "bhxh"
    if item.category and item.category in _CATEGORY_KEYWORDS:
        if _phrase_in_text(fact_lower, _CATEGORY_KEYWORDS[item.category]):
            return True

    item_lower = item.item.lower()

    # 2. Full item name substring match
    if item_lower in fact_lower:
        return True

    # 3. Bigram match on content words (len > 2) from item name
    content_words = [w for w in item_lower.split() if len(w) > 2 and w not in ("/", "-", "(", ")")]
    if len(content_words) >= 2:
        for bg in _bigrams(content_words):
            if bg in fact_lower:
                return True

    # 4. Word-fragment fallback (original logic) — for single-word or long items
    key_fragments = [w for w in item_lower.split() if len(w) > 3]
    if item.category:
        key_fragments.append(item.category)
    if not key_fragments:
        return False
    matches = sum(1 for kw in key_fragments if kw in fact_lower)
    return matches >= max(1, len(key_fragments) // 3)


class EvidenceGapDetector:
    def detect_gaps(
        self,
        domain: str,
        facts: List[str],
        situation: str = "",
    ) -> EvidenceGapResult:
        checklist = _CHECKLISTS.get(domain, _CHECKLISTS["general"])

        # Merge explicit facts with evidence claimed in the situation narrative
        claimed = _extract_claimed_evidence(situation)
        all_facts = facts + claimed

        facts_lower = [f.lower() for f in all_facts]
        all_facts_text = " ".join(facts_lower) + " " + situation.lower()

        strong_evidence: List[str] = []
        weak_evidence: List[str] = []
        missing_evidence: List[EvidenceItem] = []

        for item in checklist:
            matched_facts = [f for f in all_facts if _keywords_match(f, item)]
            if matched_facts:
                if item.priority == "high":
                    strong_evidence.extend(matched_facts)
                else:
                    weak_evidence.extend(matched_facts)
            else:
                # Broader fallback: check full situation text (catches inline mentions)
                if _keywords_match(all_facts_text, item):
                    weak_evidence.append(item.item)
                else:
                    missing_evidence.append(item)

        total = len(checklist)
        covered = total - len(missing_evidence)
        coverage_score = round(covered / total, 2) if total > 0 else 0.0

        priority_items = [m for m in missing_evidence if m.priority == "high"]

        return EvidenceGapResult(
            domain=domain,
            missing_evidence=missing_evidence,
            strong_evidence=list(dict.fromkeys(strong_evidence)),
            weak_evidence=list(dict.fromkeys(weak_evidence)),
            coverage_score=coverage_score,
            priority_items=priority_items,
            advice=_DOMAIN_ADVICE.get(domain, _DOMAIN_ADVICE["general"]),
        )
