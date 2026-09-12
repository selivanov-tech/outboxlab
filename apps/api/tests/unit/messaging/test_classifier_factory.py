from typing import Any

import httpx

from app.config import Settings
from app.contexts.messaging.infrastructure.classifier.deterministic import (
    DeterministicIntentClassifier,
)
from app.contexts.messaging.infrastructure.classifier.factory import (
    build_intent_classifier,
)
from app.contexts.messaging.infrastructure.classifier.llm import LlmIntentClassifier
from app.contexts.messaging.infrastructure.llm.anthropic import AnthropicChatClient
from app.contexts.messaging.infrastructure.llm.openai import OpenAIChatClient


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "database_url": "postgresql+asyncpg://u:p@h/db",
        "api_domain": "api.local",
        "app_env": "local",
    }
    base.update(overrides)
    return Settings(**base)


def test_llm_enabled_defaults_true() -> None:
    assert _settings().llm_enabled is True


def test_llm_provider_defaults_anthropic() -> None:
    assert _settings().llm_provider == "anthropic"


async def test_deterministic_when_flag_off() -> None:
    async with httpx.AsyncClient() as client:
        classifier = build_intent_classifier(
            _settings(llm_enabled=False, anthropic_api_key="sk-x"), client
        )
    assert isinstance(classifier, DeterministicIntentClassifier)


async def test_deterministic_when_no_key() -> None:
    async with httpx.AsyncClient() as client:
        classifier = build_intent_classifier(
            _settings(llm_enabled=True, anthropic_api_key=""), client
        )
    assert isinstance(classifier, DeterministicIntentClassifier)


async def test_anthropic_when_enabled_with_key() -> None:
    async with httpx.AsyncClient() as client:
        classifier = build_intent_classifier(
            _settings(
                llm_enabled=True, llm_provider="anthropic", anthropic_api_key="sk-x"
            ),
            client,
        )
    assert isinstance(classifier, LlmIntentClassifier)
    assert isinstance(classifier._llm, AnthropicChatClient)


async def test_openai_when_enabled_with_key() -> None:
    async with httpx.AsyncClient() as client:
        classifier = build_intent_classifier(
            _settings(llm_enabled=True, llm_provider="openai", openai_api_key="sk-o"),
            client,
        )
    assert isinstance(classifier, LlmIntentClassifier)
    assert isinstance(classifier._llm, OpenAIChatClient)


async def test_deterministic_when_provider_key_missing() -> None:
    async with httpx.AsyncClient() as client:
        classifier = build_intent_classifier(
            _settings(
                llm_enabled=True, llm_provider="openai", anthropic_api_key="sk-x"
            ),
            client,
        )
    assert isinstance(classifier, DeterministicIntentClassifier)


def test_llm_provider_is_lowercased() -> None:
    assert _settings(llm_provider="OpenAI").llm_provider == "openai"
