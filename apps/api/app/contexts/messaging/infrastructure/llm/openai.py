import httpx

_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
_DEFAULT_MODEL = "gpt-4o-mini"
_MAX_TOKENS = 16


class OpenAIChatClient:
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
            _COMPLETIONS_URL,
            headers={
                "authorization": f"Bearer {self._api_key}",
                "content-type": "application/json",
            },
            json={
                "model": self._model,
                "max_tokens": _MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
