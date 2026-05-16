"""
OpenAI tool/function definitions for the Legal Reasoning Agent.

These JSON schemas are passed to OpenAI's chat completions API.
The actual implementations live in src/agents/tools.py.

Usage:
    from src.llm.tool_calling import SITUATION_TOOLS, CONTRACT_TOOLS
    resp = client.chat_complete_with_tools(messages, tools=SITUATION_TOOLS)
"""

from __future__ import annotations

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Individual tool definitions
# ---------------------------------------------------------------------------

RETRIEVE_RELEVANT_LAWS: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "retrieve_relevant_laws",
        "description": (
            "Tìm kiếm các điều luật, quy định pháp lý liên quan đến tình huống "
            "sử dụng MongoDB $vectorSearch (tìm kiếm ngữ nghĩa). "
            "Trả về danh sách điều luật với nội dung và độ liên quan. "
            "Gọi tool này ĐẦU TIÊN trước khi phân tích."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Mô tả tình huống hoặc câu hỏi pháp lý cần tìm kiếm",
                },
                "law_type": {
                    "type": "string",
                    "description": (
                        "Lĩnh vực pháp lý để lọc kết quả. "
                        "Bỏ trống nếu không chắc."
                    ),
                    "enum": [
                        "dat_dai",
                        "hop_dong",
                        "lao_dong",
                        "doanh_nghiep",
                        "hinh_su",
                        "dan_su",
                    ],
                },
                "limit": {
                    "type": "integer",
                    "description": "Số điều luật trả về (mặc định 8, tối đa 15)",
                    "default": 8,
                },
            },
            "required": ["query"],
        },
    },
}

RETRIEVE_SIMILAR_CASES: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "retrieve_similar_cases",
        "description": (
            "Tìm kiếm các vụ kiện, tình huống pháp lý tương tự đã được ghi nhận "
            "trong hệ thống. Hữu ích để tham khảo kết quả và chiến lược của các vụ việc tương tự. "
            "Gọi sau retrieve_relevant_laws để bổ sung ngữ cảnh."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "situation": {
                    "type": "string",
                    "description": "Mô tả tình huống pháp lý cần tìm kiếm",
                },
                "law_type": {
                    "type": "string",
                    "description": "Lĩnh vực pháp lý để lọc kết quả (tùy chọn)",
                },
                "limit": {
                    "type": "integer",
                    "default": 5,
                },
            },
            "required": ["situation"],
        },
    },
}

ANALYZE_CONTRACT_RISKS: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "analyze_contract_risks",
        "description": (
            "Tìm kiếm các mẫu rủi ro hợp đồng tương tự từ cơ sở dữ liệu "
            "để hỗ trợ phân tích điều khoản hợp đồng. "
            "Sử dụng trước khi đánh giá rủi ro hợp đồng cụ thể."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "contract_text": {
                    "type": "string",
                    "description": "Đoạn trích nội dung hợp đồng cần phân tích (tối đa 1000 ký tự)",
                },
                "contract_type": {
                    "type": "string",
                    "description": "Loại hợp đồng: thue_nha, mua_ban_dat, lao_dong, dich_vu, thuong_mai",
                },
            },
            "required": ["contract_text"],
        },
    },
}

GENERATE_COMPLIANCE_CHECKLIST: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "generate_compliance_checklist",
        "description": (
            "Lấy danh sách kiểm tra tuân thủ pháp lý từ cơ sở dữ liệu "
            "cho loại doanh nghiệp hoặc giao dịch cụ thể."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "business_type": {
                    "type": "string",
                    "description": "Loại hình doanh nghiệp: tnhh, co_phan, ca_nhan, ho_kinh_doanh",
                },
                "transaction_type": {
                    "type": "string",
                    "description": "Loại giao dịch: thanh_lap_cong_ty, mua_ban_dat, thue_lao_dong",
                },
            },
            "required": [],
        },
    },
}

RETRIEVE_GRAPH_CONTEXT: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "retrieve_graph_context",
        "description": (
            "Mở rộng ngữ cảnh pháp lý từ knowledge graph: tìm các điều luật "
            "có quan hệ REFERENCES, APPLIES_TO, AMENDS với các điều đã xác định. "
            "Hữu ích để hiểu chuỗi pháp lý và các ngoại lệ."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "law_references": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Danh sách điều luật cần mở rộng ngữ cảnh "
                        "(ví dụ: ['Điều 168 Luật Đất đai 2024'])"
                    ),
                },
                "depth": {
                    "type": "integer",
                    "description": "Độ sâu traversal (1-3, mặc định 2)",
                    "default": 2,
                },
            },
            "required": ["law_references"],
        },
    },
}

# ---------------------------------------------------------------------------
# Tool sets for different workflows
# ---------------------------------------------------------------------------

# Situation analysis: needs laws, cases, and graph expansion
SITUATION_TOOLS: List[Dict[str, Any]] = [
    RETRIEVE_RELEVANT_LAWS,
    RETRIEVE_SIMILAR_CASES,
    RETRIEVE_GRAPH_CONTEXT,
]

# Contract analysis: needs risk patterns and relevant laws
CONTRACT_TOOLS: List[Dict[str, Any]] = [
    ANALYZE_CONTRACT_RISKS,
    RETRIEVE_RELEVANT_LAWS,
    GENERATE_COMPLIANCE_CHECKLIST,
]

# Full toolkit for general legal queries
ALL_LEGAL_TOOLS: List[Dict[str, Any]] = [
    RETRIEVE_RELEVANT_LAWS,
    RETRIEVE_SIMILAR_CASES,
    ANALYZE_CONTRACT_RISKS,
    GENERATE_COMPLIANCE_CHECKLIST,
    RETRIEVE_GRAPH_CONTEXT,
]
