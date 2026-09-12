from typing import Protocol

from app.contexts.messaging.domain.intent import Intent


class IntentClassifierPort(Protocol):
    async def classify(self, subject: str, text: str) -> Intent: ...
