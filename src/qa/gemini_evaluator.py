"""
Gemini QA Evaluator — adapter kết nối với Google Gemini API để đóng vai AI QA Evaluator.
Mirrors the interface of OpenAIQAEvaluator (src/qa/openai_evaluator.py) but uses
google-generativeai SDK instead of the OpenAI client.

Environment variables:
    GEMINI_API_KEY   — required, Google AI Studio API key
    GEMINI_MODEL     — optional, defaults to "gemini-1.5-flash"
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-1.5-flash"


class GeminiQAEvaluator:
    """
    Sends scenario + observed data to Gemini and returns a structured JSON judgement.

    Compatible interface with OpenAIQAEvaluator — callers can swap evaluators
    without changing the runner script.
    """

    def __init__(self, model: Optional[str] = None):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Obtain a key from https://aistudio.google.com/app/apikey "
                "and set it in your .env file."
            )

        self.model_name = model or os.getenv("GEMINI_MODEL", _DEFAULT_MODEL).strip()

        # Lazy import so the package is optional at import time
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=self.api_key)
            self._genai = genai
            self._model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
        except ImportError as exc:
            raise ImportError(
                "google-generativeai is not installed. "
                "Run: pip install google-generativeai"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialise Gemini model '{self.model_name}': {exc}\n"
                "Try setting GEMINI_MODEL to a valid model name, e.g. gemini-1.5-flash"
            ) from exc

        # Load shared evaluator system prompt
        prompt_path = Path(__file__).parent.parent.parent / "qa" / "ai_user_simulation_prompt.md"
        if prompt_path.exists():
            self.system_prompt = prompt_path.read_text(encoding="utf-8")
        else:
            self.system_prompt = (
                "Ban la AI QA Evaluator cho san pham LexAI. "
                "Danh gia chat luong phan hoi phap ly va cham diem MVP theo dinh dang JSON."
            )

    # ------------------------------------------------------------------
    # Sanitization (same logic as OpenAI evaluator for consistency)
    # ------------------------------------------------------------------

    def _sanitize_data(self, data: Any) -> Any:
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
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
            email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
            phone_pattern = r"\b(0[1-9]{1}[0-9]{8,9})\b"
            tmp = re.sub(email_pattern, "[EMAIL_REDACTED]", data)
            tmp = re.sub(phone_pattern, "[PHONE_REDACTED]", tmp)
            if len(tmp) > 12000:
                tmp = tmp[:12000] + "\n... [TRUNCATED FOR LENGTH] ..."
            return tmp
        else:
            return data

    # ------------------------------------------------------------------
    # Core evaluation call
    # ------------------------------------------------------------------

    def evaluate_scenario(self, scenario: Dict[str, Any], observed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send scenario + observed data to Gemini, return structured JSON judgement.
        Retries once on invalid JSON response.
        """
        sanitized_observed = self._sanitize_data(observed)

        prompt = (
            f"{self.system_prompt}\n\n"
            f"--- BAT DAU KICH BAN KIEM THU ---\n"
            f"ID: {scenario.get('id', 'unknown')}\n"
            f"Tieu de: {scenario.get('title', 'Untitled')}\n"
            f"Persona: {scenario.get('persona', 'general')}\n"
            f"Dau vao nguoi dung: {scenario.get('input', '')}\n"
            f"Route: {scenario.get('route', '')}\n"
            f"Yeu cau khang dinh: {scenario.get('required_assertions', [])}\n"
            f"\n"
            f"--- DU LIEU QUAN SAT THUC TE ---\n"
            f"{json.dumps(sanitized_observed, ensure_ascii=False, indent=2)}\n"
            f"--- KET THUC DU LIEU QUAN SAT ---\n\n"
            f"Hay tien hanh danh gia, cham diem chi tiet va tra ve cau truc JSON dung nhu duoc yeu cau."
        )

        for attempt in range(2):
            try:
                response = self._model.generate_content(prompt)
                raw = (response.text or "").strip()
                # Strip markdown code fences if present
                raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
                raw = re.sub(r"\s*```$", "", raw)
                result = json.loads(raw)
                return result
            except json.JSONDecodeError as exc:
                logger.warning(
                    "Gemini attempt %d: invalid JSON for scenario %s (%s)",
                    attempt + 1, scenario.get("id"), exc,
                )
                if attempt == 1:
                    return self._error_result(scenario, f"Invalid JSON from Gemini: {exc}")
            except Exception as exc:
                logger.warning(
                    "Gemini attempt %d failed for scenario %s: %s",
                    attempt + 1, scenario.get("id"), exc,
                )
                if attempt == 1:
                    return self._error_result(scenario, str(exc))

        return self._error_result(scenario, "All retry attempts exhausted")

    def _error_result(self, scenario: Dict[str, Any], reason: str) -> Dict[str, Any]:
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
                "mvp_completeness": 0,
            },
            "what_worked": [],
            "what_failed": ["Gemini Evaluator API call failed"],
            "issues": [
                {
                    "severity": "blocker",
                    "module": "GeminiQAEvaluator",
                    "title": "API evaluation failed",
                    "step": "Gemini evaluation call",
                    "expected": "Structured JSON judgement from Gemini",
                    "actual": reason,
                    "suggested_fix": (
                        "Kiem tra GEMINI_API_KEY va GEMINI_MODEL trong file .env. "
                        f"Hien tai dang dung model: {self.model_name}"
                    ),
                }
            ],
            "judgement": f"Khong the lay ket qua danh gia tu Gemini: {reason}",
        }
