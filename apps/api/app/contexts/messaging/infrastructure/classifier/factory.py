import httpx

from app.config import Settings
from app.contexts.messaging.application.ports.intent_classifier import (
    IntentClassifierPort,
)
from app.contexts.messaging.infrastructure.classifier.deterministic import (
    DeterministicIntentClassifier,
)
from app.contexts.messaging.infrastructure.classifier.llm import LlmIntentClassifier
from app.contexts.messaging.infrastructure.llm.anthropic import AnthropicChatClient
from app.contexts.messaging.infrastructure.llm.openai import OpenAIChatClient


def build_intent_classifier(
    settings: Settings, client: httpx.AsyncClient
) -> IntentClassifierPort:
    if not settings.llm_enabled:
        return DeterministicIntentClassifier()
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return LlmIntentClassifier(
            AnthropicChatClient(client, api_key=settings.anthropic_api_key)
        )
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return LlmIntentClassifier(
            OpenAIChatClient(client, api_key=settings.openai_api_key)
        )
    return DeterministicIntentClassifier()
