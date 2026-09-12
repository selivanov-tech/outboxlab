import httpx

_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_DEFAULT_MODEL = "claude-3-5-haiku-latest"
_MAX_TOKENS = 16


class AnthropicChatClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def complete(self, prompt: str) -> str:
        response = await self._client.post(
            _MESSAGES_URL,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": self._model,
                "max_tokens": _MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]
