from collections.abc import Iterable

from prometheus_client import Counter, Histogram

EMAILS_SENT = Counter("emails_sent", "Campaign emails accepted by the mail provider")
REPLY_CLASSIFIED = Counter(
    "reply_classified", "Matched replies by classified intent", ["intent"]
)
SEND_FAILURES = Counter(
    "send_failures", "Send jobs that did not send, by reason", ["reason"]
)
LEAD_PAUSED = Counter(
    "lead_paused", "Leads paused by a reply, by stop reason", ["reason"]
)
SEND_JOB_LATENCY = Histogram(
    "send_job_latency_seconds",
    "Time from a send job's scheduled time to the provider accepting the email",
    buckets=(1, 5, 15, 30, 60, 120, 300, 900, 1800, 3600),
)


def record_email_sent(latency_seconds: float) -> None:
    EMAILS_SENT.inc()
    SEND_JOB_LATENCY.observe(max(latency_seconds, 0.0))


def record_send_failure(reason: str) -> None:
    SEND_FAILURES.labels(reason=reason).inc()


def record_replies_classified(intents: Iterable[str]) -> None:
    for intent in intents:
        REPLY_CLASSIFIED.labels(intent=intent).inc()


def record_lead_paused(reason: str) -> None:
    LEAD_PAUSED.labels(reason=reason).inc()
