import contextlib
import contextvars
import logging
import os
import time

from openai import OpenAI

logger = logging.getLogger(__name__)


class ModelClient:
    """
    Bridge client for LLM model providers.
    Currently supports OpenAI.
    """

    def __init__(self, api_key: str | None = None, default_model: str | None = None):
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY is required for ModelClient")

        self.client = OpenAI(api_key=self.api_key)
        self.default_model = default_model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        logger.info(f"ModelClient initialized with model: {self.default_model}")
        self._usage_context: contextvars.ContextVar[list[dict[str, int | str | None]] | None] = (
            contextvars.ContextVar("llm_usage_context", default=None)
        )

    @contextlib.contextmanager
    def capture_usage(self):
        current = self._usage_context.get()
        if current is not None:
            yield current
            return
        usage: list[dict[str, int | str | None]] = []
        token = self._usage_context.set(usage)
        try:
            yield usage
        finally:
            self._usage_context.reset(token)

    def generate_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        messages: list[dict[str, str]] | None = None,
        **kwargs,
    ) -> str:
        """
        Generate a completion using the underlying LLM.
        """
        target_model = model or self.default_model

        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        start_mono = time.monotonic()
        try:
            response = self.client.chat.completions.create(
                model=target_model, messages=messages, **kwargs
            )
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            record = {
                "model": getattr(response, "model", target_model),
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
                "latency_ms": int((time.monotonic() - start_mono) * 1000),
            }
            collector = self._usage_context.get()
            if collector is not None:
                collector.append(record)
            return content
        except Exception as e:
            logger.error(f"Error in ModelClient.generate_completion: {e}")
            raise
