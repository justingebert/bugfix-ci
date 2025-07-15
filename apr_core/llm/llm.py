import logging
import os
import time
from typing import Any

class LLM:
    """Simple LLM wrapper that supports multiple providers and tracks basic usage."""

    def __init__(self, provider="google", model=None):
        self.provider = provider
        self.model = model or self._get_default_model()
        self.usage = {"total_tokens": 0, "input_tokens":0, "output_tokens":0, "total_cost": 0.0}
        self.nested_usage = {}
        self._setup_client()

    def _setup_client(self):
        if self.provider == "google":
            from google import genai
            if not os.getenv("LLM_API_KEY"):
                raise ValueError("LLM_API_KEY environment variable is not set.")
            self.client = genai.Client(api_key=os.getenv("LLM_API_KEY"))
        elif self.provider == "openai":
            import openai
            if not os.getenv("LLM_API_KEY"):
                raise ValueError("LLM_API_KEY environment variable is not set.")
            self.client = openai.Client(api_key=os.getenv("LLM_API_KEY"))
        elif self.provider == "anthropic":
            from anthropic import Anthropic
            if not os.getenv("LLM_API_KEY"):
                raise ValueError("LLM_API_KEY environment variable is not set.")
            self.client = Anthropic(api_key=os.getenv("LLM_API_KEY"))
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _get_default_model(self):
        defaults = {
            "google": "gemini-2.0-flash",
            "openai": "gpt-4o",
            "anthropic": "claude-3-7-sonnet",
        }
        return defaults.get(self.provider)

    def generate(self, prompt: str, system_instruction: str = None) -> tuple[str, Any]:
        """Generate content using the configured LLM provider."""

        max_attempts = 3
        backoff_time = 2  # seconds

        response_text = ""
        input_tokens = 0
        output_tokens = 0

        for attempt in range(max_attempts):
            try:
                if self.provider == "google":
                    from google.genai import types
                    response = self.client.models.generate_content(
                        model=self.model,
                        config=types.GenerateContentConfig(system_instruction=system_instruction),
                        contents=prompt
                    )
                    response_text = response.text

                    input_tokens = response.usage_metadata.get("prompt_token_count", 0)
                    #if system_instruction:
                        #input_tokens += self._estimate_tokens(system_instruction)
                    output_tokens = response.usage_metadata.get("candidates_token_count", 0)

                elif self.provider == "openai":
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "system", "content": system_instruction},
                                {"role": "user", "content": prompt}],
                        max_tokens=1500
                    )

                    response_text = response.choices[0].message.content

                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens

                elif self.provider == "anthropic":
                    response = self.client.messages.create(
                        model=self.model,
                        system=system_instruction,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=1500
                    )

                    response_text = response.content[0].text
                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens

            except Exception as e:
                logging.error(f"Error during LLM generation: {e}")
                if attempt < max_attempts - 1:
                    logging.info(f"Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    backoff_time *= 2
                else:
                    raise RuntimeError(f"Failed to generate content after {max_attempts} attempts") from e

        cost = self._calculate_cost(input_tokens, output_tokens)

        self.usage["input_tokens"] += input_tokens
        self.usage["output_tokens"] += output_tokens
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


    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on separate input and output token counts. per 1M tokens"""
        rates = {
            "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30},
            "gemini-2.0-flash": {"input": 0.15, "output": 0.60},
            "gemini-2.5-flash-lite-preview-06-17": {"input": 0.10, "output": 0.40},
            "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
            "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
            "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
            "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
            "gpt-4.1": {"input": 2.00, "output": 8.00},
            "o4-mini": {"input": 1.10, "output": 4.40},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
            "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
            "claude-3-7-sonnet": {"input": 3.00, "output": 15.00},
            "claude-sonnet-4-0": {"input": 3.00, "output": 15.00},
        }

        model_rates = rates.get(self.model, None)
        if not model_rates:
            logging.warning(f"Cost tracking not supported for this model")
            return 0

        input_cost = (input_tokens / 1000000) * model_rates["input"]
        output_cost = (output_tokens / 1000000) * model_rates["output"]

        return input_cost + output_cost

    def get_usage(self) -> dict[str, Any]:
        return self.usage

    def track_nested_usage(self, key: str):
        """Track usage for nested operations."""
        if key not in self.nested_usage:
            self.nested_usage[key] = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}

    def peek_nested_usage(self, key: str) -> dict[str, Any]:
        """Get usage statistics for a specific key without removing it from tracking."""
        if key not in self.nested_usage:
            raise KeyError(f"No nested usage found for key: {key}")

        return self.nested_usage[key]

    def pop_nested_usage(self, key: str) -> dict[str, Any]:
        """Get usage statistics for a specific key and remove it from tracking."""
        if key not in self.nested_usage:
            raise KeyError(f"No nested usage found for key: {key}")

        return self.nested_usage.pop(key)