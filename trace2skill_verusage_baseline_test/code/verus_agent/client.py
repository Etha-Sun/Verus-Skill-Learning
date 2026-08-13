from __future__ import annotations

from react_agent import LLMClient
from react_agent.models import Message, ModelSettings


class FixedGenerationClient(LLMClient):
    """Apply experiment settings without changing Trace2Skill's ReAct core."""

    def __init__(
        self,
        inner: LLMClient,
        *,
        temperature: float,
        max_output_tokens: int,
    ) -> None:
        self.inner = inner
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

    def _settings(self, incoming: ModelSettings | None) -> ModelSettings:
        return ModelSettings(
            temperature=self.temperature,
            max_tokens=self.max_output_tokens,
            stop=list(incoming.stop) if incoming else [],
            extra_body=dict(incoming.extra_body) if incoming else {},
        )

    def chat(self, messages: list[Message], settings: ModelSettings | None = None) -> str:
        return self.inner.chat(messages, self._settings(settings))

    async def chat_async(
        self, messages: list[Message], settings: ModelSettings | None = None
    ) -> str:
        return await self.inner.chat_async(messages, self._settings(settings))

    async def aclose(self) -> None:
        close = getattr(self.inner, "aclose", None)
        if close is not None:
            await close()
