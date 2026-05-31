from typing import Protocol


class LlmClient(Protocol):
    async def complete(self, prompt: str) -> str: ...
