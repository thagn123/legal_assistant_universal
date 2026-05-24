"""
Contract Clause Coach — deterministic, <30ms, no LLM.

Analyzes a contract clause for risk patterns, suggests safer alternatives,
and identifies missing clauses based on contract type.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class ClauseRisk:
    id: str
    type: str
    description: str
    severity: str        # critical / high / medium / low
    law_basis: str
    matched_phrase: str


@dataclass
class SaferVersion:
    original_phrase: str
    suggested_phrase: str
    reason: str


@dataclass
class MissingClause:
    clause_type: str
    importance: str      # required / recommended / optional
    template: str
    law_basis: str


@dataclass
class ClauseCoachResult:
    clause_text: str
    clause_type: str
    clause_type_label: str
    risks: List[ClauseRisk]
    safer_versions: List[SaferVersion]
    missing_clauses: List[MissingClause]
    risk_score: float    # 0–100
    risk_level: str      # low / medium / high / critical
    summary: str


# ── Clause type detection ─────────────────────────────────────────────────────

_CLAUSE_TYPE_KEYWORDS: List[Tuple[str, str, str]] = [
    # (keywords, type_code, type_label)
    (["chấm dứt", "đơn phương", "hủy hợp đồng"],
     "termination", "Điều khoản chấm dứt hợp đồng"),
    (["phạt", "bồi thường", "vi phạm", "thiệt hại"],
     "penalty", "Điều khoản phạt / bồi thường"),
    (["bảo mật", "bí mật", "nda", "không tiết lộ"],
     "confidentiality", "Điều khoản bảo mật"),
    (["sở hữu trí tuệ", "bản quyền", "nhãn hiệu", "patent"],
     "intellectual_property", "Điều khoản sở hữu trí tuệ"),
    (["bất khả kháng", "force majeure", "thiên tai", "dịch bệnh"],
     "force_majeure", "Điều khoản bất khả kháng"),
    (["giải quyết tranh chấp", "trọng tài", "tòa án", "khởi kiện"],
     "dispute_resolution", "Điều khoản giải quyết tranh chấp"),
    (["thanh toán", "giá trị", "phí", "tiền công", "chi phí"],
     "payment", "Điều khoản thanh toán"),
    (["phạm vi", "công việc", "nhiệm vụ", "dịch vụ", "hàng hóa"],
     "scope", "Điều khoản phạm vi / đối tượng"),
    (["thời hạn", "hiệu lực", "ngày", "tháng", "năm"],
     "duration", "Điều khoản thời hạn hợp đồng"),
    (["bảo đảm", "bảo lãnh", "thế chấp", "cầm cố"],
     "security", "Điều khoản bảo đảm / bảo lãnh"),
    (["lao động", "nhân viên", "người lao động", "lương"],
     "employment", "Điều khoản lao động"),
]


def _detect_clause_type(text: str) -> Tuple[str, str]:
    lower = text.lower()
    for keywords, type_code, type_label in _CLAUSE_TYPE_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return type_code, type_label
    return "general", "Điều khoản chung"


# ── Risk patterns ─────────────────────────────────────────────────────────────
# Each entry: (id, type, keywords, description, severity, law_basis, safer_phrase, safer_reason)

_RISK_PATTERNS: List[Tuple[str, str, List[str], str, str, str, str, str]] = [
    (
        "r01", "Chấm dứt đơn phương không thông báo",
        ["đơn phương chấm dứt", "chấm dứt ngay lập tức", "chấm dứt không cần thông báo"],
        "Cho phép một bên chấm dứt hợp đồng mà không cần thông báo trước, gây bất lợi cho bên còn lại.",
        "high", "Bộ luật Dân sự 2015 Điều 428",
        "được quyền đơn phương chấm dứt hợp đồng với điều kiện thông báo trước ít nhất [X] ngày",
        "Cần quy định thời gian thông báo tối thiểu để bên kia có thời gian chuẩn bị",
    ),
    (
        "r02", "Trách nhiệm không giới hạn",
        ["mọi thiệt hại", "toàn bộ thiệt hại", "không giới hạn trách nhiệm",
         "chịu trách nhiệm vô hạn", "bất kỳ thiệt hại nào"],
        "Điều khoản buộc một bên chịu mọi thiệt hại không có giới hạn, có thể gây rủi ro tài chính nghiêm trọng.",
        "critical", "Bộ luật Dân sự 2015 Điều 302, 360",
        "chịu trách nhiệm bồi thường thiệt hại trực tiếp, tối đa không vượt quá [X]% giá trị hợp đồng",
        "Cần giới hạn mức trách nhiệm tối đa để kiểm soát rủi ro tài chính",
    ),
    (
        "r03", "Phạt vi phạm quá cao",
        ["phạt 50%", "phạt 80%", "phạt 100%", "phạt toàn bộ"],
        "Mức phạt vi phạm vượt quá giới hạn pháp luật cho phép (tối đa 8% giá trị nghĩa vụ vi phạm).",
        "high", "Luật Thương mại 2005 Điều 301",
        "phạt vi phạm với mức phạt không quá 8% giá trị phần nghĩa vụ hợp đồng bị vi phạm",
        "Luật Thương mại 2005 giới hạn mức phạt tối đa 8% giá trị vi phạm",
    ),
    (
        "r04", "Phạm vi công việc mơ hồ",
        ["theo thỏa thuận", "tùy trường hợp", "khi cần thiết", "theo yêu cầu"],
        "Phạm vi nghĩa vụ không rõ ràng, dễ phát sinh tranh chấp về phạm vi công việc.",
        "medium", "Bộ luật Dân sự 2015 Điều 398",
        "thực hiện các công việc cụ thể gồm: [liệt kê chi tiết], trong phạm vi [X], hoàn thành trước ngày [Y]",
        "Cần mô tả rõ ràng phạm vi, tiêu chí nghiệm thu, timeline cụ thể",
    ),
    (
        "r05", "Điều khoản bảo mật vô thời hạn",
        ["vĩnh viễn", "mãi mãi", "không thời hạn bảo mật", "bảo mật vô thời hạn"],
        "Nghĩa vụ bảo mật vô thời hạn có thể không có giá trị pháp lý và tạo gánh nặng không hợp lý.",
        "medium", "Bộ luật Dân sự 2015 Điều 3",
        "nghĩa vụ bảo mật có hiệu lực trong thời hạn [X] năm kể từ ngày chấm dứt hợp đồng",
        "Thời hạn bảo mật hợp lý thường từ 2–5 năm sau khi hợp đồng kết thúc",
    ),
    (
        "r06", "Chuyển nhượng IP một chiều",
        ["toàn bộ quyền sở hữu trí tuệ thuộc về", "chuyển giao mọi quyền ip",
         "không bảo lưu quyền sở hữu"],
        "Chuyển nhượng toàn bộ IP mà không được bồi thường hoặc giữ lại quyền sử dụng cơ bản.",
        "high", "Luật Sở hữu trí tuệ 2005 Điều 45",
        "quyền sở hữu trí tuệ đối với sản phẩm công việc thuộc về Bên [A], Bên [B] được cấp phép sử dụng miễn phí cho mục đích [X]",
        "Nên quy định rõ phạm vi chuyển nhượng và điều kiện bồi thường phù hợp",
    ),
    (
        "r07", "Điều khoản gia hạn tự động không giới hạn",
        ["tự động gia hạn", "mặc nhiên gia hạn", "gia hạn vô thời hạn"],
        "Gia hạn tự động không giới hạn có thể ràng buộc một bên không mong muốn tiếp tục hợp đồng.",
        "medium", "Bộ luật Dân sự 2015 Điều 404",
        "tự động gia hạn thêm [X] tháng nếu không có bên nào thông báo chấm dứt trong vòng [Y] ngày trước khi hết hạn",
        "Cần quy định số lần gia hạn tối đa hoặc thời gian thông báo không gia hạn",
    ),
    (
        "r08", "Luật áp dụng không rõ ràng",
        ["theo pháp luật hiện hành", "theo quy định của pháp luật", "luật áp dụng không xác định"],
        "Không chỉ rõ luật điều chỉnh có thể gây tranh chấp về phương án giải quyết.",
        "low", "Bộ luật Dân sự 2015 Điều 683",
        "hợp đồng này được điều chỉnh và giải thích theo pháp luật Việt Nam hiện hành",
        "Nên xác định rõ luật áp dụng, đặc biệt trong hợp đồng có yếu tố nước ngoài",
    ),
    (
        "r09", "Cấm cạnh tranh quá rộng",
        ["không được làm việc", "không được hợp tác", "cấm cạnh tranh toàn cầu",
         "không được tham gia bất kỳ"],
        "Điều khoản cấm cạnh tranh quá rộng về phạm vi địa lý, thời gian hoặc ngành nghề có thể vô hiệu.",
        "high", "Bộ luật Lao động 2019 Điều 9, Luật Cạnh tranh 2018",
        "không tham gia hoặc hỗ trợ các đối thủ cạnh tranh trực tiếp trong lĩnh vực [X] tại [địa bàn Y] trong thời hạn [Z] tháng",
        "Giới hạn phạm vi địa lý, thời gian (tối đa 1–2 năm) và ngành nghề cụ thể",
    ),
    (
        "r10", "Thanh toán chỉ khi hoàn thành 100%",
        ["chỉ thanh toán khi", "thanh toán sau khi hoàn thành toàn bộ",
         "thanh toán một lần khi nghiệm thu"],
        "Điều khoản thanh toán một lần sau khi hoàn thành có thể gây rủi ro thanh khoản cho bên cung cấp.",
        "medium", "Luật Thương mại 2005 Điều 50",
        "thanh toán theo tiến độ: [X]% khi ký kết, [Y]% khi đạt mốc [A], [Z]% sau khi nghiệm thu cuối cùng",
        "Thanh toán theo tiến độ bảo vệ cả hai bên và giảm rủi ro vỡ nợ",
    ),
]


# ── Missing clause templates by contract type ─────────────────────────────────

_MISSING_CLAUSE_TEMPLATES: Dict[str, List[Tuple[str, str, str, str]]] = {
    # (clause_type, importance, template, law_basis)
    "termination": [
        ("Thông báo chấm dứt", "required",
         "Mỗi bên có quyền chấm dứt hợp đồng này bằng văn bản thông báo trước ít nhất [X] ngày.",
         "Bộ luật Dân sự 2015 Điều 428"),
        ("Hậu quả chấm dứt", "required",
         "Khi hợp đồng chấm dứt, các bên phải hoàn trả tài sản/tài liệu đã nhận trong vòng [X] ngày.",
         "Bộ luật Dân sự 2015 Điều 422"),
    ],
    "penalty": [
        ("Giới hạn trách nhiệm", "required",
         "Tổng trách nhiệm của mỗi bên không vượt quá [X]% tổng giá trị hợp đồng, trừ trường hợp cố ý.",
         "Bộ luật Dân sự 2015 Điều 302"),
        ("Bất khả kháng", "required",
         "Không bên nào chịu trách nhiệm vi phạm hợp đồng do sự kiện bất khả kháng (thiên tai, dịch bệnh, lệnh nhà nước).",
         "Bộ luật Dân sự 2015 Điều 156"),
    ],
    "payment": [
        ("Phương thức thanh toán", "required",
         "Thanh toán qua chuyển khoản ngân hàng đến tài khoản: [số TK], ngân hàng [X], chủ tài khoản [Y].",
         "Luật Thương mại 2005 Điều 50"),
        ("Phạt chậm thanh toán", "recommended",
         "Nếu thanh toán trễ hơn [X] ngày, bên nợ phải trả lãi suất [Y]%/năm tính trên số tiền chậm.",
         "Bộ luật Dân sự 2015 Điều 357"),
    ],
    "scope": [
        ("Nghiệm thu", "required",
         "Bên B bàn giao sản phẩm, Bên A có [X] ngày để kiểm tra. Nếu không có phản hồi, sản phẩm được coi là chấp thuận.",
         "Luật Thương mại 2005 Điều 44"),
        ("Thay đổi phạm vi", "recommended",
         "Mọi thay đổi phạm vi công việc phải được hai bên đồng ý bằng văn bản trước khi thực hiện.",
         "Bộ luật Dân sự 2015 Điều 421"),
    ],
    "general": [
        ("Bất khả kháng", "required",
         "Không bên nào vi phạm hợp đồng nếu việc thực hiện bị cản trở bởi sự kiện bất khả kháng.",
         "Bộ luật Dân sự 2015 Điều 156"),
        ("Giải quyết tranh chấp", "required",
         "Tranh chấp phát sinh được giải quyết trước tiên bằng thương lượng. Nếu không thành, đưa ra Tòa án nhân dân có thẩm quyền.",
         "Bộ luật Tố tụng Dân sự 2015"),
        ("Điều khoản hoàn chỉnh", "recommended",
         "Hợp đồng này là toàn bộ thỏa thuận giữa các bên, thay thế mọi thỏa thuận trước đó về cùng vấn đề.",
         "Bộ luật Dân sự 2015 Điều 398"),
    ],
    "confidentiality": [
        ("Phạm vi thông tin bảo mật", "required",
         'Thông tin bảo mật bao gồm: tài liệu kỹ thuật, danh sách khách hàng, dữ liệu tài chính được đánh dấu "BẢO MẬT".',
         "Luật Sở hữu trí tuệ 2005"),
        ("Ngoại lệ bảo mật", "required",
         "Nghĩa vụ bảo mật không áp dụng với thông tin đã công khai, bắt buộc theo lệnh tòa, hoặc đã biết trước.",
         "Bộ luật Dân sự 2015 Điều 3"),
    ],
    "employment": [
        ("Thử việc", "recommended",
         "Thời gian thử việc không quá [30/60] ngày, lương thử việc ít nhất 85% lương chính thức.",
         "Bộ luật Lao động 2019 Điều 25, 26"),
        ("Chế độ phúc lợi", "required",
         "Người lao động được hưởng đầy đủ các chế độ BHXH, BHYT, BHTN theo quy định pháp luật.",
         "Luật BHXH 2014"),
    ],
}


# ── Service ───────────────────────────────────────────────────────────────────

class ClauseCoachService:
    """
    Phân tích clause hợp đồng, phát hiện rủi ro, gợi ý phiên bản an toàn hơn,
    và liệt kê điều khoản còn thiếu.  Deterministic, <30ms, không gọi LLM.
    """

    def analyze(
        self,
        clause_text: str,
        contract_type: Optional[str] = None,
    ) -> ClauseCoachResult:
        lower = clause_text.lower()
        clause_type, clause_type_label = _detect_clause_type(clause_text)

        # ── Detect risks ──────────────────────────────────────────────────────
        risks: List[ClauseRisk] = []
        safer_versions: List[SaferVersion] = []

        for rid, rtype, keywords, desc, severity, law_basis, safer_phrase, safer_reason in _RISK_PATTERNS:
            matched = next((kw for kw in keywords if kw in lower), None)
            if matched:
                risks.append(ClauseRisk(
                    id=rid, type=rtype, description=desc,
                    severity=severity, law_basis=law_basis,
                    matched_phrase=matched,
                ))
                safer_versions.append(SaferVersion(
                    original_phrase=matched,
                    suggested_phrase=safer_phrase,
                    reason=safer_reason,
                ))

        # ── Detect missing clauses ────────────────────────────────────────────
        # Use both clause_type and contract_type to determine applicable templates
        keys_to_check = {clause_type}
        if contract_type:
            keys_to_check.add(contract_type)
        keys_to_check.add("general")

        seen_clause_types: set = set()
        missing_clauses: List[MissingClause] = []
        for key in keys_to_check:
            for ct, importance, template, law_basis in _MISSING_CLAUSE_TEMPLATES.get(key, []):
                if ct in seen_clause_types:
                    continue
                # Check if already present via simple keyword match
                ct_lower = ct.lower()
                if not any(w in lower for w in ct_lower.split()):
                    seen_clause_types.add(ct)
                    missing_clauses.append(MissingClause(
                        clause_type=ct,
                        importance=importance,
                        template=template,
                        law_basis=law_basis,
                    ))

        # ── Risk score ────────────────────────────────────────────────────────
        severity_weights = {"critical": 30, "high": 20, "medium": 10, "low": 5}
        raw_score = sum(severity_weights.get(r.severity, 5) for r in risks)
        missing_penalty = sum(10 if m.importance == "required" else 3 for m in missing_clauses)
        risk_score = min(100.0, raw_score + missing_penalty * 0.5)

        risk_level = (
            "critical" if risk_score >= 70 else
            "high"     if risk_score >= 45 else
            "medium"   if risk_score >= 20 else
            "low"
        )

        # ── Summary ───────────────────────────────────────────────────────────
        if not risks and not missing_clauses:
            summary = "Điều khoản không phát hiện rủi ro đáng kể. Tuy nhiên nên tham khảo luật sư để xem xét toàn bộ hợp đồng."
        else:
            risk_labels = {"low": "thấp", "medium": "trung bình", "high": "cao", "critical": "rất cao"}
            critical_count = sum(1 for r in risks if r.severity == "critical")
            summary = (
                f"Phát hiện {len(risks)} rủi ro (trong đó {critical_count} nghiêm trọng) "
                f"và {len(missing_clauses)} điều khoản còn thiếu. "
                f"Mức rủi ro tổng thể: {risk_labels.get(risk_level, risk_level).upper()}."
            )

        return ClauseCoachResult(
            clause_text=clause_text,
            clause_type=clause_type,
            clause_type_label=clause_type_label,
            risks=risks,
            safer_versions=safer_versions,
            missing_clauses=missing_clauses,
            risk_score=round(risk_score, 1),
            risk_level=risk_level,
            summary=summary,
        )
