import re

from app.contexts.messaging.domain.intent import Intent

_RULES: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    (
        Intent.UNSUBSCRIBE,
        (
            "unsubscribe",
            "remove me",
            "opt out",
            "opt-out",
            "take me off",
            "stop emailing",
            "stop contacting",
        ),
    ),
    (
        Intent.OOO,
        (
            "out of office",
            "ooo",
            "on vacation",
            "annual leave",
            "parental leave",
            "maternity leave",
            "currently away",
            "away until",
            "auto-reply",
            "autoreply",
            "automatic reply",
        ),
    ),
    (
        Intent.NEGATIVE,
        (
            "not interested",
            "no thanks",
            "no thank you",
            "not a fit",
            "not the right",
            "we pass",
            "please stop",
            "do not contact",
            "don't contact",
            "no need",
        ),
    ),
    (
        Intent.POSITIVE,
        (
            "interested",
            "sounds good",
            "let's talk",
            "lets talk",
            "let's chat",
            "lets chat",
            "happy to",
            "book a",
            "schedule a",
            "set up a call",
            "tell me more",
            "works for me",
            "yes please",
            "yes",
        ),
    ),
)

_COMPILED: tuple[tuple[Intent, re.Pattern[str]], ...] = tuple(
    (intent, re.compile("|".join(rf"\b{re.escape(k)}\b" for k in keywords)))
    for intent, keywords in _RULES
)


class DeterministicIntentClassifier:
    async def classify(self, subject: str, text: str) -> Intent:
        haystack = f"{subject}\n{text}".lower()
        for intent, pattern in _COMPILED:
            if pattern.search(haystack):
                return intent
        return Intent.UNCLEAR
