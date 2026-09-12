import httpx

from app.contexts.messaging.domain.intent import Intent
from app.contexts.messaging.infrastructure.classifier.deterministic import (
    DeterministicIntentClassifier,
)
from app.contexts.messaging.infrastructure.llm.client import LlmClient

_PROMPT = (
    "Classify the intent of this email reply. Reply with exactly one word from: "
    "positive, negative, ooo, unsubscribe, unclear.\n\n"
    "Subject: {subject}\n\nBody: {text}"
)


class LlmIntentClassifier:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm
        self._fallback = DeterministicIntentClassifier()

    async def classify(self, subject: str, text: str) -> Intent:
        try:
            answer = await self._llm.complete(
                _PROMPT.format(subject=subject, text=text)
            )
            return Intent(answer.strip().lower())
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            AttributeError,
        ):
            return await self._fallback.classify(subject, text)
