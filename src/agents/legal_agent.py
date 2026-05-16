"""
Legal Reasoning Agent — OpenAI tool-calling workflow.

This is the "brain" of the recommendation engine. It orchestrates:
1. Entity + intent extraction from the user's legal query (LLM call 1)
2. Tool-calling loop: retrieve laws → retrieve cases → graph expansion (up to 4 rounds)
3. LLM synthesis of all evidence into a structured assessment (LLM call 2)

Graceful degradation:
    If OPENAI_API_KEY is absent or openai package missing, falls back to the
    deterministic SituationAnalyzer (src/recommenders/situation_analyzer.py).
    The API contract is identical in both modes.

Usage:
    agent = LegalAgent(vector_storage)

    # Situation analysis
    result = agent.analyze_situation(
        situation="Hàng xóm xây tường lấn 50cm đất sổ đỏ của tôi",
        user_id="u_123",
        user_role="nguyen_don",
        law_type="dat_dai",
    )

    # Contract analysis
    result = agent.analyze_contract(
        contract_text="...",
        user_id="u_123",
        contract_type="thue_nha",
    )
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agents.tools import dispatch_tool
from src.llm import client as llm
from src.llm.prompts import (
    CONTRACT_ANALYSIS_PROMPT,
    LEGAL_SYSTEM_PROMPT,
    SITUATION_ANALYSIS_PROMPT,
)
from src.llm.tool_calling import CONTRACT_TOOLS, SITUATION_TOOLS

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 4  # Maximum tool-calling iterations per request


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------


@dataclass
class LegalAgentResult:
    """
    Structured result returned by LegalAgent for any analysis type.
    Compatible with both LLM and deterministic fallback modes.
    """

    session_id: str
    situation_summary: str

    # Legal position
    legal_position_strength: str  # "Mạnh" | "Trung bình" | "Yếu" | "Chưa xác định"
    position_score: float  # 0.0–1.0
    position_reasoning: str

    # Retrieved evidence
    relevant_laws: List[Dict[str, Any]]  # from retrieve_relevant_laws
    similar_cases: List[Dict[str, Any]]  # from retrieve_similar_cases

    # Recommendations
    recommended_actions: List[str]
    warnings: List[str]
    risk_assessment: Dict[str, Any]

    # Full narrative
    full_assessment: str
    citations: List[str]

    # Metadata
    is_grounded: bool  # True when real law chunks were found
    used_llm: bool  # True when OpenAI API was used
    tool_calls_made: List[str]  # Names of tools invoked


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class LegalAgent:
    """
    Orchestrates legal analysis using OpenAI tool calling + MongoDB retrieval.
    Thread-safe: no mutable shared state after __init__.
    """

    def __init__(self, vector_storage) -> None:
        self._vs = vector_storage

    # ── Public interface ─────────────────────────────────────────────────────

    def analyze_situation(
        self,
        situation: str,
        user_id: str,
        user_role: str = "nguyen_don",
        law_type: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> LegalAgentResult:
        """
        Full legal situation analysis.
        Uses LLM tool-calling when available; deterministic fallback otherwise.
        """
        sid = session_id or ("agent_" + uuid.uuid4().hex[:8])

        # ── Orchestrator delegation ───────────────────────────────────────────
        try:
            from src.engine.orchestrator import LegalIntelligenceOrchestrator
            orch = LegalIntelligenceOrchestrator(self._vs)
            intel = orch.analyze(
                situation=situation, user_id=user_id, user_role=user_role,
                law_type=law_type, session_id=sid,
            )
            return LegalAgentResult(
                session_id=intel.session_id,
                situation_summary=intel.situation_summary,
                legal_position_strength=intel.legal_position_strength,
                position_score=intel.position_score,
                position_reasoning=intel.position_reasoning,
                relevant_laws=intel.relevant_laws,
                similar_cases=intel.similar_cases,
                recommended_actions=intel.recommended_actions,
                warnings=intel.warnings,
                risk_assessment=intel.risk_assessment,
                full_assessment=intel.full_assessment,
                citations=intel.citations,
                is_grounded=intel.is_grounded,
                used_llm=intel.used_llm,
                tool_calls_made=intel.tool_calls_made,
            )
        except ImportError:
            logger.debug("LegalIntelligenceOrchestrator not available, using legacy agent")
        except Exception as exc:
            logger.warning("Orchestrator failed (%s), falling back to legacy agent", exc)

        if llm.is_available():
            return self._llm_analyze_situation(
                situation, user_id, user_role, law_type, sid
            )
        logger.info(
            "LLM unavailable — deterministic fallback for session %s", sid
        )
        return self._deterministic_analyze(
            situation, user_id, user_role, law_type, sid
        )

    def analyze_contract(
        self,
        contract_text: str,
        user_id: str,
        contract_type: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> LegalAgentResult:
        """
        Contract analysis: clause classification, risk detection,
        compliance score, and recommended improvements.
        """
        sid = session_id or ("contract_" + uuid.uuid4().hex[:8])

        if llm.is_available():
            return self._llm_analyze_contract(
                contract_text, user_id, contract_type, sid
            )
        return self._deterministic_contract_analyze(
            contract_text, user_id, contract_type, sid
        )

    # ── LLM-powered situation analysis ───────────────────────────────────────

    def _llm_analyze_situation(
        self,
        situation: str,
        user_id: str,
        user_role: str,
        law_type: Optional[str],
        session_id: str,
    ) -> LegalAgentResult:
        role_label = _role_label(user_role)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": LEGAL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Phân tích tình huống pháp lý sau:\n\n"
                    f"**TÌNH HUỐNG:** {situation}\n"
                    f"**VAI TRÒ:** {role_label}\n"
                    + (f"**LĨNH VỰC:** {law_type}\n" if law_type else "")
                    + "\nHãy dùng tool `retrieve_relevant_laws` và `retrieve_similar_cases` "
                    "để thu thập bằng chứng trước khi phân tích."
                ),
            },
        ]

        tool_calls_made: List[str] = []
        retrieved_laws: List[Dict] = []
        similar_cases: List[Dict] = []

        # ── Tool-calling loop ─────────────────────────────────────────────────
        for _round in range(_MAX_TOOL_ROUNDS):
            resp = llm.chat_complete_with_tools(
                messages=messages,
                tools=SITUATION_TOOLS,
                temperature=0.1,
            )
            if resp is None:
                break

            choice = resp.choices[0]
            msg = choice.message

            if not msg.tool_calls:
                break  # Model decided to stop calling tools

            # Append the assistant message (with tool_calls) to history
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except Exception:
                    fn_args = {}

                tool_calls_made.append(fn_name)
                logger.debug("Tool call: %s(%s)", fn_name, fn_args)

                result_str = dispatch_tool(fn_name, fn_args, self._vs)

                # Collect structured data for post-processing
                try:
                    data = json.loads(result_str)
                    if fn_name == "retrieve_relevant_laws":
                        retrieved_laws = data.get("laws", [])
                    elif fn_name == "retrieve_similar_cases":
                        similar_cases = data.get("cases", [])
                except Exception:
                    pass

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    }
                )

        # ── Final synthesis ───────────────────────────────────────────────────
        law_context = _format_laws_for_prompt(retrieved_laws)
        case_context = _format_cases_for_prompt(similar_cases)

        synthesis_user_msg = SITUATION_ANALYSIS_PROMPT.format(
            situation=situation,
            role_label=role_label,
            law_type=law_type or "Tổng hợp (chưa xác định lĩnh vực)",
            law_context=law_context or "Chưa tìm được điều luật cụ thể trong hệ thống.",
            case_context=case_context or "Chưa có vụ việc tương tự trong hệ thống.",
        )
        messages.append({"role": "user", "content": synthesis_user_msg})

        full_assessment = llm.chat_complete(messages, temperature=0.2)
        if not full_assessment:
            full_assessment = (
                "Không thể tạo phân tích chi tiết. "
                "Vui lòng kiểm tra kết nối và thử lại."
            )

        # ── Parse structured fields ───────────────────────────────────────────
        strength, score = _parse_position_strength(full_assessment)
        actions = _parse_recommended_actions(full_assessment, law_type)
        warnings = _parse_warnings(full_assessment)
        citations = _extract_citations(full_assessment, retrieved_laws)

        # Log for collaborative filtering
        self._vs.log_interaction(
            user_id=user_id,
            doc_id="__agent__",
            action_type="agent_situation_analysis",
            context={
                "situation": situation[:300],
                "law_type": law_type,
                "user_role": user_role,
                "tools_used": tool_calls_made,
                "laws_found": len(retrieved_laws),
                "cases_found": len(similar_cases),
            },
        )

        return LegalAgentResult(
            session_id=session_id,
            situation_summary=_summarise(situation),
            legal_position_strength=strength,
            position_score=score,
            position_reasoning=_extract_position_reasoning(full_assessment),
            relevant_laws=retrieved_laws[:8],
            similar_cases=similar_cases[:5],
            recommended_actions=actions,
            warnings=warnings,
            risk_assessment=_build_risk_assessment(full_assessment),
            full_assessment=full_assessment,
            citations=citations,
            is_grounded=len(retrieved_laws) > 0,
            used_llm=True,
            tool_calls_made=tool_calls_made,
        )

    # ── LLM-powered contract analysis ────────────────────────────────────────

    def _llm_analyze_contract(
        self,
        contract_text: str,
        user_id: str,
        contract_type: Optional[str],
        session_id: str,
    ) -> LegalAgentResult:
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": LEGAL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Phân tích hợp đồng sau và tìm kiếm các điều luật/rủi ro liên quan:\n\n"
                    f"**LOẠI HỢP ĐỒNG:** {contract_type or 'Không xác định'}\n\n"
                    f"**NỘI DUNG:**\n{contract_text[:3000]}"
                ),
            },
        ]

        tool_calls_made: List[str] = []
        retrieved_laws: List[Dict] = []
        risk_context = ""

        for _round in range(2):
            resp = llm.chat_complete_with_tools(
                messages=messages,
                tools=CONTRACT_TOOLS,
                temperature=0.1,
            )
            if resp is None:
                break

            msg = resp.choices[0].message
            if not msg.tool_calls:
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except Exception:
                    fn_args = {}

                tool_calls_made.append(fn_name)
                result_str = dispatch_tool(fn_name, fn_args, self._vs)

                try:
                    data = json.loads(result_str)
                    if fn_name == "retrieve_relevant_laws":
                        retrieved_laws = data.get("laws", [])
                    elif fn_name == "analyze_contract_risks":
                        risks = data.get("similar_risks_from_db", [])
                        risk_context = _format_risks_for_prompt(risks)
                except Exception:
                    pass

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    }
                )

        # Synthesis
        synthesis = CONTRACT_ANALYSIS_PROMPT.format(
            contract_text=contract_text[:3000],
            contract_type=contract_type or "Hợp đồng chung",
            risk_context=risk_context or "Không có dữ liệu rủi ro tương tự.",
        )
        messages.append({"role": "user", "content": synthesis})
        full_assessment = llm.chat_complete(messages, temperature=0.2) or (
            "Không thể phân tích hợp đồng. Vui lòng thử lại."
        )

        self._vs.log_interaction(
            user_id=user_id,
            doc_id="__contract_analysis__",
            action_type="contract_analysis",
            context={
                "contract_type": contract_type,
                "tools_used": tool_calls_made,
                "laws_found": len(retrieved_laws),
            },
        )

        return LegalAgentResult(
            session_id=session_id,
            situation_summary=f"Phân tích hợp đồng: {contract_type or 'loại chung'}",
            legal_position_strength="Trung bình",
            position_score=0.5,
            position_reasoning="Xem chi tiết phân tích hợp đồng trong full_assessment.",
            relevant_laws=retrieved_laws[:5],
            similar_cases=[],
            recommended_actions=_parse_recommended_actions(full_assessment),
            warnings=_parse_warnings(full_assessment),
            risk_assessment=_build_risk_assessment(full_assessment),
            full_assessment=full_assessment,
            citations=_extract_citations(full_assessment, retrieved_laws),
            is_grounded=len(retrieved_laws) > 0,
            used_llm=True,
            tool_calls_made=tool_calls_made,
        )

    # ── Deterministic fallbacks ───────────────────────────────────────────────

    def _deterministic_analyze(
        self,
        situation: str,
        user_id: str,
        user_role: str,
        law_type: Optional[str],
        session_id: str,
    ) -> LegalAgentResult:
        """Delegate to the existing SituationAnalyzer when LLM is unavailable."""
        from src.recommenders.situation_analyzer import SituationAnalyzer

        analyzer = SituationAnalyzer(self._vs)
        r = analyzer.analyze(
            situation=situation,
            user_id=user_id,
            user_role=user_role,
            law_type=law_type,
            situation_id=session_id,
        )
        return LegalAgentResult(
            session_id=session_id,
            situation_summary=r.situation_summary,
            legal_position_strength=r.legal_position_strength,
            position_score=r.position_score,
            position_reasoning=r.position_reasoning,
            relevant_laws=[
                {
                    "chunk_id": law.chunk_id,
                    "law_reference": law.law_reference,
                    "content": law.content,
                    "relevance_score": law.relevance_score,
                    "applicability": law.applicability,
                }
                for law in r.relevant_laws
            ],
            similar_cases=[],
            recommended_actions=r.recommended_actions,
            warnings=r.warnings,
            risk_assessment={},
            full_assessment=r.full_assessment,
            citations=r.citations,
            is_grounded=r.is_grounded,
            used_llm=False,
            tool_calls_made=[],
        )

    def _deterministic_contract_analyze(
        self,
        contract_text: str,
        user_id: str,
        contract_type: Optional[str],
        session_id: str,
    ) -> LegalAgentResult:
        """Minimal contract analysis without LLM."""
        from src.contract.clause_extractor import extract_clauses

        clauses = extract_clauses(contract_text, contract_type)
        high_risk = [c for c in clauses if c.risk_level == "cao"]
        warnings = [
            f"Điều khoản rủi ro cao: {c.title} — {c.risk_reason}"
            for c in high_risk
            if c.risk_reason
        ]
        return LegalAgentResult(
            session_id=session_id,
            situation_summary=f"Phân tích hợp đồng ({contract_type or 'loại chung'})"
            f" — {len(clauses)} điều khoản, {len(high_risk)} rủi ro cao",
            legal_position_strength="Trung bình",
            position_score=0.5,
            position_reasoning=(
                "Kết quả từ phân tích cú pháp (không có LLM). "
                "Cấu hình OPENAI_API_KEY để nhận phân tích đầy đủ."
            ),
            relevant_laws=[],
            similar_cases=[],
            recommended_actions=[
                "Đọc kỹ toàn bộ hợp đồng trước khi ký.",
                "Chú ý điều khoản phạt vi phạm và giải quyết tranh chấp.",
                "Tham khảo luật sư trước khi ký hợp đồng có giá trị lớn.",
            ],
            warnings=warnings or ["Không phát hiện điều khoản rủi ro rõ ràng."],
            risk_assessment={
                "clauses_extracted": len(clauses),
                "high_risk_clauses": len(high_risk),
            },
            full_assessment=(
                f"Đã trích xuất {len(clauses)} điều khoản. "
                f"Phát hiện {len(high_risk)} điều khoản có rủi ro cao. "
                "Cấu hình OPENAI_API_KEY để nhận phân tích chi tiết từ AI."
            ),
            citations=[],
            is_grounded=False,
            used_llm=False,
            tool_calls_made=[],
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _role_label(user_role: str) -> str:
    return {
        "nguyen_don": "nguyên đơn (người khởi kiện)",
        "bi_don": "bị đơn (người bị kiện)",
        "tu_van": "người cần tư vấn pháp lý",
    }.get(user_role, user_role)


def _format_laws_for_prompt(laws: List[Dict]) -> str:
    if not laws:
        return ""
    parts = []
    for i, law in enumerate(laws[:8], 1):
        ref = law.get("law_reference", "Không rõ nguồn")
        content = law.get("content", "")[:500]
        score = law.get("relevance_score", 0)
        path = law.get("hierarchy_path", "")
        parts.append(
            f"{i}. **{ref}** (relevance: {score:.2f})"
            + (f" — {path}" if path else "")
            + f"\n   {content}"
        )
    return "\n\n".join(parts)


def _format_cases_for_prompt(cases: List[Dict]) -> str:
    if not cases:
        return ""
    parts = []
    for i, c in enumerate(cases[:4], 1):
        title = c.get("title", "Vụ việc không rõ tên")
        situation = c.get("situation", "")[:300]
        outcome = c.get("outcome", "")
        result = c.get("result", "")
        score = c.get("similarity_score", 0)
        parts.append(
            f"{i}. **{title}** (tương đồng: {score:.0%})\n"
            f"   Tình huống: {situation}\n"
            + (f"   Kết quả: {outcome}\n" if outcome else "")
            + (f"   Phán quyết: {result}" if result else "")
        )
    return "\n\n".join(parts)


def _format_risks_for_prompt(risks: List[Dict]) -> str:
    if not risks:
        return ""
    parts = []
    for r in risks[:5]:
        parts.append(
            f"- **{r.get('name', '')}** [{r.get('severity', '')}]: "
            f"{r.get('description', '')}"
        )
    return "\n".join(parts)


def _parse_position_strength(text: str) -> tuple[str, float]:
    text_lower = text.lower()
    if "**mạnh**" in text_lower or "mức độ:** mạnh" in text_lower or ": mạnh" in text_lower:
        return "Mạnh", 0.82
    if "trung bình" in text_lower:
        return "Trung bình", 0.52
    if "yếu" in text_lower:
        return "Yếu", 0.25
    return "Chưa xác định", 0.1


def _parse_recommended_actions(text: str, law_type: Optional[str] = None) -> List[str]:
    actions: List[str] = []
    lines = text.split("\n")
    in_section = False
    for line in lines:
        stripped = line.strip()
        if "hành động" in stripped.lower() and "đề xuất" in stripped.lower():
            in_section = True
            continue
        if in_section:
            if re.match(r"^[1-9]\.", stripped) or re.match(r"^[-*•]", stripped):
                action = re.sub(r"^[1-9]\.\s*|^[-*•]\s*", "", stripped).strip()
                if len(action) > 10:
                    actions.append(action)
            elif stripped.startswith("##") and actions:
                break
    if not actions:
        actions = [
            "Thu thập và bảo quản tất cả tài liệu liên quan (bản gốc + bản sao).",
            "Tham khảo ý kiến luật sư chuyên ngành.",
            "Xem xét phương án hòa giải trước khi khởi kiện.",
        ]
    return actions[:6]


def _parse_warnings(text: str) -> List[str]:
    warnings: List[str] = []
    lines = text.split("\n")
    in_section = False
    for line in lines:
        stripped = line.strip()
        if "cảnh báo" in stripped.lower() or "rủi ro" in stripped.lower():
            in_section = True
            continue
        if in_section:
            if re.match(r"^[-*•⏰⚠️📁]", stripped):
                w = re.sub(r"^[-*•⏰⚠️📁]\s*", "", stripped).strip()
                if len(w) > 5:
                    warnings.append(w)
            elif stripped.startswith("##") and warnings:
                break
    return warnings[:6]


def _extract_position_reasoning(text: str) -> str:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "vị thế pháp lý" in line.lower() or "đánh giá" in line.lower():
            reasoning_lines: List[str] = []
            for j in range(i + 1, min(i + 8, len(lines))):
                l = lines[j].strip()
                if l and not l.startswith("##"):
                    reasoning_lines.append(l)
                elif l.startswith("##"):
                    break
            if reasoning_lines:
                return " ".join(reasoning_lines)[:500]
    return text[:300] if text else "Xem phần phân tích đầy đủ."


def _extract_citations(text: str, laws: List[Dict]) -> List[str]:
    citations = [
        law.get("law_reference", "")
        for law in laws
        if law.get("law_reference")
    ]
    inline = re.findall(
        r"(?:Điều|Khoản|Điểm|Luật|Nghị định|Thông tư)\s+[\d\w]+(?:\s+[\w\d]+){0,4}",
        text,
    )
    for c in inline[:8]:
        cleaned = c.strip()
        if cleaned and cleaned not in citations:
            citations.append(cleaned)
    return citations[:12]


def _build_risk_assessment(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    if any(w in text_lower for w in ["rủi ro cao", "nguy cơ cao", "nghiêm trọng"]):
        level = "cao"
        score = 0.75
    elif "trung bình" in text_lower:
        level = "trung_binh"
        score = 0.5
    else:
        level = "thap"
        score = 0.25
    return {
        "overall_risk_level": level,
        "risk_score": score,
        "source": "llm_text_analysis",
    }


def _summarise(situation: str, max_len: int = 200) -> str:
    s = situation.strip()
    return s if len(s) <= max_len else s[:max_len].rsplit(" ", 1)[0] + "…"
