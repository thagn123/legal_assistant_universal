from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, List, Optional

from src.evidence.evidence_schemas import EvidenceSchema


def fold_vietnamese(text: str) -> str:
    """Lowercase and remove Vietnamese accents while preserving word shape."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return stripped.replace("đ", "d")


def normalize_text(text: str) -> str:
    folded = fold_vietnamese(text)
    folded = re.sub(r"[^\w\s/.-]", " ", folded, flags=re.UNICODE)
    return re.sub(r"\s+", " ", folded).strip()


DOMAIN_ALIASES: Dict[str, str] = {
    "land": "dat_dai",
    "dat_dai": "dat_dai",
    "dat dai": "dat_dai",
    "đất đai": "dat_dai",
    "dat dai / bds": "dat_dai",
    "đất đai / bđs": "dat_dai",
    "bat dong san": "dat_dai",
    "bds": "dat_dai",
    "real estate": "dat_dai",
    "family": "gia_dinh",
    "gia_dinh": "gia_dinh",
    "gia dinh": "gia_dinh",
    "hon nhan gia dinh": "gia_dinh",
    "hôn nhân gia đình": "gia_dinh",
    "marriage": "gia_dinh",
    "ly hon": "gia_dinh",
    "nuoi con": "gia_dinh",
    "labor": "lao_dong",
    "labour": "lao_dong",
    "lao_dong": "lao_dong",
    "lao dong": "lao_dong",
    "employment": "lao_dong",
    "sa thai": "lao_dong",
    "contract": "hop_dong",
    "hop_dong": "hop_dong",
    "hop dong": "hop_dong",
    "sme": "hop_dong",
    "doanh_nghiep": "doanh_nghiep",
    "doanh nghiep": "doanh_nghiep",
    "business": "doanh_nghiep",
    "corporate": "doanh_nghiep",
    "dan_su": "dan_su",
    "dan su": "dan_su",
    "civil": "dan_su",
    "thua ke": "dan_su",
    "di chuc": "dan_su",
    "hinh_su": "hinh_su",
    "hinh su": "hinh_su",
    "criminal": "hinh_su",
    "toi pham": "hinh_su",
    "hanh_chinh": "hanh_chinh",
    "hanh chinh": "hanh_chinh",
    "administrative": "hanh_chinh",
    "khieu nai hanh chinh": "hanh_chinh",
    "general": "general",
}


def normalize_domain(domain: Optional[str]) -> str:
    if not domain:
        return "general"
    raw = str(domain).strip()
    if raw in DOMAIN_ALIASES:
        return DOMAIN_ALIASES[raw]
    folded = normalize_text(raw)
    return DOMAIN_ALIASES.get(folded, raw if raw in REQUIRED_EVIDENCE else "general")


REQUIRED_EVIDENCE: Dict[str, List[EvidenceSchema]] = {
    "dat_dai": [
        EvidenceSchema(
            evidence_id="transfer_document",
            title="Giấy tờ chuyển nhượng quyền sử dụng đất",
            category="title",
            domain="land",
            priority="high",
            aliases=[
                "giấy chuyển nhượng",
                "hợp đồng chuyển nhượng",
                "giấy mua bán viết tay",
                "giấy mua bán",
                "hợp đồng mua bán đất",
                "hợp đồng mua bán",
                "văn bản chuyển nhượng",
                "giấy tay",
            ],
        ),
        EvidenceSchema(
            evidence_id="payment_proof",
            title="Biên lai hoặc chứng từ thanh toán tiền mua đất",
            category="payment",
            domain="land",
            priority="high",
            aliases=[
                "biên lai",
                "chứng từ thanh toán",
                "giấy chuyển tiền",
                "sao kê",
                "ủy nhiệm chi",
                "phiếu thu",
                "biên nhận tiền",
                "giấy nhận tiền",
                "chuyển khoản",
                "thanh toán tiền mua đất",
            ],
        ),
        EvidenceSchema(
            evidence_id="local_confirmation",
            title="Xác nhận của UBND xã/phường về quyền sử dụng đất",
            category="confirmation",
            domain="land",
            priority="high",
            aliases=[
                "xác nhận ubnd",
                "xác nhận của ubnd",
                "ubnd xã xác nhận",
                "ubnd phường xác nhận",
                "xác nhận của ủy ban",
                "xác nhận quyền sử dụng đất",
                "xác nhận địa phương",
            ],
        ),
        EvidenceSchema(
            evidence_id="land_certificate",
            title="Sổ đỏ / Giấy chứng nhận quyền sử dụng đất",
            category="certificate",
            domain="land",
            priority="high",
            aliases=[
                "sổ đỏ",
                "so do",
                "sổ hồng",
                "so hong",
                "bìa hồng",
                "bia hong",
                "giấy chứng nhận quyền sử dụng đất",
                "giay chung nhan quyen su dung dat",
                "gcn qsdđ",
                "gcn qsdd",
                "gcnqsdđ",
                "gcnqsdd",
                "giấy chứng nhận qsdđ",
                "giay chung nhan qsdd",
                "giấy cn qsdd",
                "giay cn quyen su dung dat",
                "bìa đỏ",
                "bia do",
                "giấy chứng nhận nhà đất",
                "giấy chứng thực quyền sử dụng đất",
                "giấy nhà đất",
                "chứng nhận sử dụng đất",
            ],
        ),
        EvidenceSchema(
            evidence_id="land_map",
            title="Bản đồ địa chính / sơ đồ thửa đất",
            category="map",
            domain="land",
            priority="medium",
            aliases=[
                "bản đồ địa chính",
                "sơ đồ thửa đất",
                "trích lục bản đồ",
                "trích đo địa chính",
                "bản đồ thửa đất",
            ],
        ),
        EvidenceSchema(
            evidence_id="witness",
            title="Nhân chứng tham gia giao dịch",
            category="witness",
            domain="land",
            priority="medium",
            aliases=[
                "nhân chứng",
                "người làm chứng",
                "người chứng kiến",
                "hàng xóm xác nhận",
                "người chứng kiến giao dịch",
            ],
        ),
    ],
    "gia_dinh": [
        EvidenceSchema(
            "marriage_certificate",
            "Giấy đăng ký kết hôn",
            "marriage",
            "family",
            "high",
            ["giấy đăng ký kết hôn", "đăng ký kết hôn", "giấy kết hôn"],
        ),
        EvidenceSchema(
            "child_birth_certificate",
            "Giấy khai sinh của con",
            "birth",
            "family",
            "high",
            ["giấy khai sinh", "khai sinh của con", "giấy khai sinh của con"],
        ),
        EvidenceSchema(
            "income_proof",
            "Chứng minh thu nhập",
            "income",
            "family",
            "high",
            ["bảng lương", "sao kê lương", "hợp đồng lao động", "chứng minh thu nhập", "sao kê tài khoản"],
        ),
        EvidenceSchema(
            "custody_conditions",
            "Chứng cứ về điều kiện chăm sóc, nơi ở và học tập của con",
            "custody",
            "family",
            "medium",
            ["thời gian chăm sóc con", "nơi ở", "điều kiện học tập", "trường học", "người trực tiếp chăm sóc"],
        ),
        EvidenceSchema(
            "shared_assets",
            "Tài liệu về tài sản chung/vợ chồng",
            "ownership",
            "family",
            "medium",
            ["tài sản chung", "sổ đỏ", "sổ tiết kiệm", "đăng ký xe", "tài sản vợ chồng"],
        ),
    ],
    "lao_dong": [
        EvidenceSchema(
            "labor_contract",
            "Hợp đồng lao động",
            "contract",
            "labor",
            "high",
            ["hợp đồng lao động", "hđlđ", "hdld", "offer letter", "quyết định tuyển dụng", "hợp đồng làm việc"],
        ),
        EvidenceSchema(
            "termination_decision",
            "Quyết định hoặc thông báo chấm dứt hợp đồng",
            "termination",
            "labor",
            "high",
            [
                "quyết định sa thải",
                "quyết định chấm dứt hợp đồng",
                "thông báo nghỉ việc",
                "email chấm dứt",
                "email thông báo nghỉ việc",
                "thông báo sa thải",
                "thư sa thải",
                "quyết định nghỉ việc",
            ],
        ),
        EvidenceSchema(
            "salary_proof",
            "Bảng lương / chứng từ trả lương",
            "salary",
            "labor",
            "high",
            ["bảng lương", "sao kê lương", "phiếu lương", "tin nhắn trả lương", "chứng từ lương"],
        ),
        EvidenceSchema(
            "attendance_proof",
            "Chứng cứ về thời gian làm việc / chấm công",
            "salary",
            "labor",
            "medium",
            ["bảng chấm công", "chấm công", "ca làm", "lịch làm việc", "email phân ca"],
        ),
        EvidenceSchema(
            "social_insurance",
            "Sổ bảo hiểm xã hội / dữ liệu BHXH",
            "insurance",
            "labor",
            "medium",
            ["sổ bảo hiểm xã hội", "sổ bhxh", "bhxh", "bảo hiểm xã hội"],
        ),
    ],
    "hop_dong": [
        EvidenceSchema(
            "contract",
            "Hợp đồng / bản thỏa thuận",
            "contract",
            "contract",
            "high",
            ["hợp đồng", "bản thỏa thuận", "phụ lục hợp đồng", "thỏa thuận"],
        ),
        EvidenceSchema(
            "payment_clause",
            "Điều khoản thanh toán",
            "clause",
            "contract",
            "high",
            ["điều khoản thanh toán", "lịch thanh toán", "phương thức thanh toán"],
        ),
        EvidenceSchema(
            "penalty_clause",
            "Điều khoản phạt vi phạm / bồi thường",
            "clause",
            "contract",
            "medium",
            ["điều khoản phạt", "phạt vi phạm", "bồi thường thiệt hại", "điều khoản bồi thường"],
        ),
        EvidenceSchema(
            "payment_proof",
            "Chứng từ thanh toán / biên lai giao nhận tiền",
            "payment",
            "contract",
            "high",
            ["chứng từ thanh toán", "biên lai", "phiếu thu", "sao kê", "ủy nhiệm chi", "biên nhận tiền"],
        ),
        EvidenceSchema(
            "communication",
            "Email / tin nhắn trao đổi liên quan",
            "communication",
            "contract",
            "medium",
            ["email", "tin nhắn", "zalo", "messenger", "trao đổi", "thông báo vi phạm"],
        ),
    ],
    "dan_su": [
        EvidenceSchema(
            "identity",
            "Giấy tờ tùy thân của các bên liên quan",
            "identity",
            "civil",
            "high",
            ["cccd", "cmnd", "căn cước công dân", "chứng minh nhân dân", "hộ chiếu"],
        ),
        EvidenceSchema(
            "ownership",
            "Tài liệu chứng minh quyền sở hữu tài sản tranh chấp",
            "ownership",
            "civil",
            "high",
            ["quyền sở hữu", "giấy tờ sở hữu", "sổ đỏ", "giấy chứng nhận", "đăng ký xe"],
        ),
        EvidenceSchema(
            "will",
            "Di chúc hoặc văn bản thỏa thuận phân chia di sản",
            "will",
            "civil",
            "high",
            ["di chúc", "văn bản chia thừa kế", "thỏa thuận thừa kế", "phân chia di sản"],
        ),
        EvidenceSchema(
            "payment_proof",
            "Chứng từ thanh toán / biên lai liên quan tài sản",
            "payment",
            "civil",
            "medium",
            ["chứng từ thanh toán", "biên lai", "biên nhận tiền", "sao kê"],
        ),
        EvidenceSchema(
            "witness",
            "Nhân chứng biết về giao dịch hoặc sự kiện tranh chấp",
            "witness",
            "civil",
            "medium",
            ["nhân chứng", "người làm chứng", "người chứng kiến"],
        ),
    ],
    "general": [
        EvidenceSchema(
            "identity",
            "Giấy tờ tùy thân của người liên quan",
            "identity",
            "general",
            "high",
            ["cccd", "cmnd", "căn cước công dân", "hộ chiếu", "giấy tờ tùy thân"],
        ),
        EvidenceSchema(
            "core_document",
            "Tài liệu chính chứng minh quyền lợi bị xâm phạm",
            "other",
            "general",
            "high",
            ["hợp đồng", "tài liệu gốc", "văn bản gốc", "chứng từ", "giấy tờ"],
        ),
        EvidenceSchema(
            "communication",
            "Tin nhắn / email / trao đổi giữa các bên",
            "communication",
            "general",
            "medium",
            ["tin nhắn", "email", "zalo", "messenger", "trao đổi"],
        ),
        EvidenceSchema(
            "witness",
            "Nhân chứng biết về sự việc",
            "witness",
            "general",
            "medium",
            ["nhân chứng", "người làm chứng", "người chứng kiến"],
        ),
    ],
}


def get_required_evidence(domain: Optional[str], situation: str = "") -> List[EvidenceSchema]:
    normalized = normalize_domain(domain)
    if normalized == "general" and situation:
        normalized = infer_domain_from_text(situation)
    return list(REQUIRED_EVIDENCE.get(normalized, REQUIRED_EVIDENCE["general"]))


def all_evidence_schemas() -> List[EvidenceSchema]:
    seen: set[str] = set()
    items: List[EvidenceSchema] = []
    for schemas in REQUIRED_EVIDENCE.values():
        for schema in schemas:
            key = f"{schema.domain}:{schema.evidence_id}"
            if key not in seen:
                seen.add(key)
                items.append(schema)
    return items


def infer_domain_from_text(text: str) -> str:
    folded = normalize_text(text)
    scores = {
        "dat_dai": ["dat", "so do", "so hong", "bia hong", "quyen su dung dat", "thua dat", "bat dong san", "gcn qsdd"],
        "gia_dinh": ["ly hon", "nuoi con", "ket hon", "vo chong", "cap duong", "hon nhan", "chia tai san vo chong"],
        "lao_dong": ["lao dong", "sa thai", "nghi viec", "bang luong", "bhxh", "hop dong lao dong", "ngo luong"],
        "hop_dong": ["hop dong", "thoa thuan", "phat vi pham", "thanh toan", "vi pham hop dong"],
        "dan_su": ["thua ke", "di chuc", "tai san", "dan su", "chia thua ke", "nguoi thua ke"],
        "hinh_su": ["hinh su", "toi pham", "bi can", "truy to", "bat giam", "canh sat", "vu an hinh su", "to cao"],
        "hanh_chinh": ["hanh chinh", "quyet dinh hanh chinh", "khieu nai", "ubnd", "co quan hanh chinh", "xin phep xay"],
        "doanh_nghiep": ["cong ty", "co dong", "pha san", "von dieu le", "hdqt", "giam doc", "thanh vien cong ty"],
    }
    ranked = {
        domain: sum(1 for needle in needles if needle in folded)
        for domain, needles in scores.items()
    }
    best = max(ranked, key=ranked.get)
    return best if ranked[best] > 0 else "general"


def aliases_for_schema(schema: EvidenceSchema) -> List[str]:
    values = [schema.title, schema.evidence_id.replace("_", " "), *schema.aliases]
    return list(dict.fromkeys(v for v in values if v))


def find_schema_by_id(evidence_id: str, domain: Optional[str] = None) -> Optional[EvidenceSchema]:
    candidates: Iterable[EvidenceSchema]
    if domain:
        candidates = get_required_evidence(domain)
    else:
        candidates = all_evidence_schemas()
    for schema in candidates:
        if schema.evidence_id == evidence_id:
            return schema
    return None


def find_schemas_by_titles_or_ids(values: Iterable[object]) -> List[EvidenceSchema]:
    folded_values = {normalize_text(str(v)) for v in values if v}
    matches: List[EvidenceSchema] = []
    for schema in all_evidence_schemas():
        aliases = {normalize_text(a) for a in aliases_for_schema(schema)}
        if folded_values.intersection(aliases) or normalize_text(schema.evidence_id) in folded_values:
            matches.append(schema)
    return matches


def alias_matches_text(text: str, aliases: Iterable[str]) -> bool:
    folded = normalize_text(text)
    for alias in aliases:
        needle = normalize_text(alias)
        if needle and re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", folded):
            return True
    return False
