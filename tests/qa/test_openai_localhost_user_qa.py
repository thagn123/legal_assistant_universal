from __future__ import annotations

import json
import os
import pytest
from unittest.mock import MagicMock, patch
from src.qa.openai_evaluator import OpenAIQAEvaluator


def test_evaluator_initialization_missing_key():
    """Kiểm tra xem evaluator có quăng lỗi ValueError khi thiếu OPENAI_API_KEY không."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        with pytest.raises(ValueError) as excinfo:
            OpenAIQAEvaluator()
        assert "OPENAI_API_KEY" in str(excinfo.value)


def test_evaluator_sanitize_data():
    """Kiểm tra tính năng làm sạch dữ liệu nhạy cảm (Sanitization) của evaluator."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-mock-key"}):
        evaluator = OpenAIQAEvaluator()
        
        raw_data = {
            "api_key": "sk-1234567890abcdef",
            "user_token": "bearer-token-here",
            "email": "nguyen.van@gmail.com",
            "phone": "0912345678",
            "message": "Số điện thoại của An là 0912345678 và email của anh ấy là nguyen.van@gmail.com."
        }
        
        sanitized = evaluator._sanitize_data(raw_data)
        
        # Bắt buộc phải che giấu các key bảo mật
        assert sanitized["api_key"] == "[REDACTED_SECURITY]"
        assert sanitized["user_token"] == "[REDACTED_SECURITY]"
        
        # Bắt buộc phải che giấu email và sđt
        assert sanitized["email"] == "[EMAIL_REDACTED]"
        assert sanitized["phone"] == "[PHONE_REDACTED]"
        
        # Kiểm tra nội dung văn bản bên trong
        assert "0912345678" not in sanitized["message"]
        assert "nguyen.van@gmail.com" not in sanitized["message"]
        assert "[PHONE_REDACTED]" in sanitized["message"]
        assert "[EMAIL_REDACTED]" in sanitized["message"]


@patch("src.qa.openai_evaluator.OpenAI")
def test_evaluate_scenario_success(mock_openai_class):
    """Kiểm tra cuộc gọi chấm điểm thành công và nhận diện dữ liệu JSON trả về."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({
            "scenario_id": "test_scenario",
            "status": "pass",
            "scores": {
                "ux_clarity": 9,
                "legal_relevance": 9,
                "evidence_citation_usefulness": 8,
                "recommendation_quality": 8,
                "personalization": 7,
                "context_retention": 9,
                "error_resilience": 10,
                "mvp_completeness": 9
            },
            "what_worked": ["Everything works great"],
            "what_failed": [],
            "issues": [],
            "judgement": "Excellent legal recommendation engine."
        })))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-mock-key"}):
        evaluator = OpenAIQAEvaluator()
        scenario = {"id": "test_scenario", "input": "Hello", "route": "/analyze"}
        observed = {"response": "Hi there"}
        
        result = evaluator.evaluate_scenario(scenario, observed)
        
        assert result["scenario_id"] == "test_scenario"
        assert result["status"] == "pass"
        assert result["scores"]["ux_clarity"] == 9
        assert result["scores"]["error_resilience"] == 10

