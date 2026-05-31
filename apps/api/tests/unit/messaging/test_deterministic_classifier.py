import pytest

from app.contexts.messaging.domain.intent import Intent
from app.contexts.messaging.infrastructure.classifier.deterministic import (
    DeterministicIntentClassifier,
)

_CASES = [
    ("Re: offer", "Please unsubscribe me from this list", Intent.UNSUBSCRIBE),
    ("Automatic reply", "I am out of office until Monday", Intent.OOO),
    ("Re: offer", "Thanks, but we're not interested", Intent.NEGATIVE),
    ("Re: offer", "This sounds good, let's talk next week", Intent.POSITIVE),
    ("Re: offer", "Yes, please send more", Intent.POSITIVE),
    ("Re: offer", "Who is this and how did you get my address?", Intent.UNCLEAR),
]


@pytest.mark.parametrize(("subject", "snippet", "expected"), _CASES)
async def test_classify(subject: str, snippet: str, expected: Intent) -> None:
    classifier = DeterministicIntentClassifier()
    assert await classifier.classify(subject, snippet) == expected


async def test_unsubscribe_beats_positive() -> None:
    classifier = DeterministicIntentClassifier()
    result = await classifier.classify(
        "Re: offer", "Sounds good, but please unsubscribe me"
    )
    assert result is Intent.UNSUBSCRIBE


async def test_ooo_beats_negative() -> None:
    classifier = DeterministicIntentClassifier()
    result = await classifier.classify(
        "Out of office", "On vacation; not interested in meetings this week"
    )
    assert result is Intent.OOO


async def test_short_token_is_not_matched_inside_a_word() -> None:
    classifier = DeterministicIntentClassifier()
    result = await classifier.classify("Re: offer", "I will reply yesterday's thread")
    assert result is Intent.UNCLEAR
