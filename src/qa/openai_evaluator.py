from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIQAEvaluator:
    """
    Adapter kết nối với OpenAI API để đóng vai trò làm AI QA Evaluator chấm điểm các kịch bản test.
    Đọc cấu hình duy nhất từ biến môi trường (trong file .env của dự án).
    """

    def __init__(self, model: Optional[str] = None):
        # Đọc OpenAI API Key
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError(
                "❌ Không tìm thấy biến môi trường 'OPENAI_API_KEY'. "
                "Vui lòng thiết lập khóa OpenAI API của bạn trong file .env ở dự án gốc."
            )

        # Đọc cấu hình model từ .env, fallback về gpt-4o-mini
        self.model = model or os.getenv("OPENAI_QA_MODEL", "gpt-4o-mini").strip()
        self.client = OpenAI(api_key=self.api_key)

        # Đọc prompt đánh giá hệ thống
        prompt_path = Path(__file__).parent.parent.parent / "qa" / "ai_user_simulation_prompt.md"
        if prompt_path.exists():
            self.system_prompt = prompt_path.read_text(encoding="utf-8")
        else:
            self.system_prompt = (
                "Bạn là AI QA Evaluator cho sản phẩm LexAI. "
                "Bạn cần đánh giá chất lượng phản hồi pháp lý và chấm điểm MVP theo định dạng JSON."
            )

    def _sanitize_data(self, data: Any) -> Any:
        """
        Làm sạch dữ liệu quan sát được (observed data) trước khi gửi lên OpenAI API.
        Loại bỏ token, cookie, khóa bí mật hoặc thông tin nhạy cảm nếu có.
        """
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                # Bỏ qua hoặc giấu các trường bảo mật thông dụng
                k_lower = k.lower()
                # Do not redact functional fields like 'key_laws'
                if any(sec in k_lower for sec in ["token", "cookie", "auth", "secret", "password"]) or ("key" in k_lower and "key_law" not in k_lower):
                    sanitized[k] = "[REDACTED_SECURITY]"
                else:
                    sanitized[k] = self._sanitize_data(v)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(x) for x in data]
        elif isinstance(data, str):
            # Thay thế email và số điện thoại bằng biểu thức chính quy
            email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
            phone_pattern = r'\b(0[1-9]{1}[0-9]{8,9})\b'
            tmp = re.sub(email_pattern, "[EMAIL_REDACTED]", data)
            tmp = re.sub(phone_pattern, "[PHONE_REDACTED]", tmp)
            # Truncate nếu văn bản quá dài (> 12000 ký tự) để tránh quá tải token
            if len(tmp) > 12000:
                tmp = tmp[:12000] + "\n... [TRUNCATED FOR LENGTH] ..."
            return tmp
        else:
            return data

    def evaluate_scenario(self, scenario: Dict[str, Any], observed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gửi kịch bản kiểm thử và dữ liệu quan sát được lên OpenAI API để chấm điểm.
        Tự động xử lý lỗi parse JSON và thử lại một lần nếu cần.
        """
        sanitized_observed = self._sanitize_data(observed)
        
        user_content = (
            f"--- BẮT ĐẦU KỊCH BẢN KIỂM THỬ ---\n"
            f"ID: {scenario.get('id', 'unknown')}\n"
            f"Tiêu đề: {scenario.get('title', 'Untitled')}\n"
            f"Persona: {scenario.get('persona', 'general')}\n"
            f"Đầu vào người dùng: {scenario.get('input', '')}\n"
            f"Route: {scenario.get('route', '')}\n"
            f"Yêu cầu khẳng định (Required Assertions): {scenario.get('required_assertions', [])}\n"
            f"\n"
            f"--- DỮ LIỆU QUAN SÁT THỰC TẾ (OBSERVED DATA) ---\n"
            f"{json.dumps(sanitized_observed, ensure_ascii=False, indent=2)}\n"
            f"--- KẾT THÚC DỮ LIỆU QUAN SÁT ---\n\n"
            f"Hãy tiến hành đánh giá, chấm điểm chi tiết và trả về cấu trúc JSON đúng như được yêu cầu."
        )

        retries = 1
        for attempt in range(retries + 1):
            try:
                # Sử dụng JSON Mode của OpenAI để đảm bảo đầu ra là JSON
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                
                raw_response = response.choices[0].message.content or ""
                result = json.loads(raw_response.strip())
                return result

            except Exception as e:
                logger.warning(
                    "Attempt %d failed to evaluate scenario %s with OpenAI: %s",
                    attempt + 1,
                    scenario.get("id"),
                    e
                )
                if attempt == retries:
                    # Nếu hết lượt thử lại, tạo một JSON lỗi giả định để runner không bị sập
                    return {
                        "scenario_id": scenario.get("id"),
                        "status": "fail",
                        "scores": {
                            "ux_clarity": 0,
                            "legal_relevance": 0,
                            "evidence_citation_usefulness": 0,
                            "recommendation_quality": 0,
                            "personalization": 0,
                            "context_retention": 0,
                            "error_resilience": 0,
                            "mvp_completeness": 0
                        },
                        "what_worked": [],
                        "what_failed": ["OpenAI Evaluator API call failed"],
                        "issues": [
                            {
                                "severity": "blocker",
                                "module": "OpenAIQAEvaluator",
                                "title": "API Evaluation failed",
                                "step": "AI Evaluation Call",
                                "expected": "Successful response from OpenAI",
                                "actual": str(e),
                                "suggested_fix": "Kiểm tra kết nối mạng và tính hợp lệ của OPENAI_API_KEY."
                            }
                        ],
                        "judgement": f"Không thể lấy kết quả đánh giá tự động từ OpenAI: {str(e)}"
                    }
