import os
import logging
from typing import Any, Optional


class LLM:
    """Simple LLM wrapper that supports multiple providers and tracks basic usage."""

    def __init__(self, provider="google", model=None):
        self.provider = provider
        self.model = model or self._get_default_model()
        self.usage = {"total_tokens": 0, "total_cost": 0.0}
        self.nested_usage = {}
        self._setup_client()

    def _setup_client(self):
        if self.provider == "google":
            from google import genai
            self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        # elif self.provider == "openai":
        #     import openai
        #     self.client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _get_default_model(self):
        defaults = {
            "google": "gemini-2.0-flash",
            "openai": "gpt-4o",
        }
        return defaults.get(self.provider)

    def generate(self, prompt: str, system_instruction: str = None) -> tuple[str, Any]:
        """Generate content using the configured LLM provider."""
        response_text = ""
        input_tokens = 0
        output_tokens = 0
        token_count = 0
        cost = 0.0

        if self.provider == "google":
            from google.genai import types
            response = self.client.models.generate_content(
                model=self.model,
                config=types.GenerateContentConfig(system_instruction=system_instruction),
                contents=prompt
            )
            response_text = response.text

            input_tokens = self._estimate_tokens(prompt)
            if system_instruction:
                input_tokens += self._estimate_tokens(system_instruction)
            output_tokens = self._estimate_tokens(response_text)

            cost = self._calculate_cost(input_tokens, output_tokens)

        self.usage["total_tokens"] += input_tokens + output_tokens
        self.usage["total_cost"] += cost

        for key in self.nested_usage:
            self.nested_usage[key]["input_tokens"] += input_tokens
            self.nested_usage[key]["output_tokens"] += output_tokens
            self.nested_usage[key]["cost"] += cost

        tokens = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost
        }

        return response_text, tokens

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for a string."""
        # (4 chars ≈ 1 token)
        return len(text) // 4

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on separate input and output token counts."""
        rates = {
            "gemini-2.0-flash": {"input": 0.15, "output": 0.60},
        }

        model_rates = rates.get(self.model, {"input": 0.0005, "output": 0.0015})

        input_cost = (input_tokens / 1000000) * model_rates["input"]
        output_cost = (output_tokens / 1000000) * model_rates["output"]

        return input_cost + output_cost

    def get_usage(self) -> dict[str, Any]:
        """Get usage statistics."""
        return self.usage

    def track_nested_usage(self, key: str):
        """Track usage for nested operations."""
        if key not in self.nested_usage:
            self.nested_usage[key] = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
        return self.nested_usage[key]

    def pop_nested_usage(self, key: str) -> dict[str, Any]:
        """Get usage statistics for a specific key and remove it from tracking."""
        if key not in self.nested_usage:
            return {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}

        return self.nested_usage.pop(key)