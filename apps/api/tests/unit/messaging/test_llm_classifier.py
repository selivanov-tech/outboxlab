import httpx

from app.contexts.messaging.domain.intent import Intent
from app.contexts.messaging.infrastructure.classifier.llm import LlmIntentClassifier
from app.contexts.messaging.infrastructure.llm.anthropic import AnthropicChatClient
from app.contexts.messaging.infrastructure.llm.openai import OpenAIChatClient


def _anthropic_response(text: str) -> httpx.Response:
    return httpx.Response(200, json={"content": [{"type": "text", "text": text}]})


def _openai_response(content: str) -> httpx.Response:
    return httpx.Response(
        200, json={"choices": [{"message": {"role": "assistant", "content": content}}]}
    )


async def test_anthropic_client_label_is_used() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _anthropic_response("negative")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        classifier = LlmIntentClassifier(AnthropicChatClient(client, api_key="k"))
        result = await classifier.classify("Re: offer", "this sounds good, interested")

    assert result is Intent.NEGATIVE


async def test_openai_client_label_is_used() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer k"
        return _openai_response("unsubscribe")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        classifier = LlmIntentClassifier(OpenAIChatClient(client, api_key="k"))
        result = await classifier.classify("Re: offer", "stop emailing me")

    assert result is Intent.UNSUBSCRIBE


async def test_falls_back_to_deterministic_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        classifier = LlmIntentClassifier(OpenAIChatClient(client, api_key="k"))
        result = await classifier.classify("Re: offer", "please unsubscribe me")

    assert result is Intent.UNSUBSCRIBE


async def test_falls_back_when_llm_returns_unknown_label() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _anthropic_response("maybe")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        classifier = LlmIntentClassifier(AnthropicChatClient(client, api_key="k"))
        result = await classifier.classify("Re: offer", "we are not interested")

    assert result is Intent.NEGATIVE


async def test_falls_back_when_openai_content_is_null() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": None}}]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        classifier = LlmIntentClassifier(OpenAIChatClient(client, api_key="k"))
        result = await classifier.classify("Re: offer", "not interested, thanks")

    assert result is Intent.NEGATIVE
