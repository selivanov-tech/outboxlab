from app.contexts.messaging.domain.intent import Intent


def test_intent_has_exactly_five_labels() -> None:
    assert {i.value for i in Intent} == {
        "positive",
        "negative",
        "ooo",
        "unsubscribe",
        "unclear",
    }


def test_intent_is_a_str_enum() -> None:
    assert Intent.POSITIVE == "positive"
    assert isinstance(Intent.POSITIVE, str)
