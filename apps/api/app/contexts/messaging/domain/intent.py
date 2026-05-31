from enum import StrEnum


class Intent(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    OOO = "ooo"
    UNSUBSCRIBE = "unsubscribe"
    UNCLEAR = "unclear"
