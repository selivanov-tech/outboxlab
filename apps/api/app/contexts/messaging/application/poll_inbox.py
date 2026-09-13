from app.contexts.messaging.application.matching import match_reply
from app.contexts.messaging.application.ports.email_receiver import EmailReceiverPort
from app.contexts.messaging.application.ports.inbound_repository import (
    InboundMessageRepositoryPort,
)
from app.contexts.messaging.application.ports.intent_classifier import (
    IntentClassifierPort,
)
from app.contexts.messaging.application.ports.mailbox_gateway import (
    MailboxGatewayPort,
    MailboxView,
)
from app.contexts.messaging.application.ports.outbound_repository import (
    OutboundMessageRepositoryPort,
)
from app.contexts.messaging.application.ports.outbox_writer import OutboxEventWriterPort
from app.contexts.messaging.application.ports.suppression_repository import (
    SuppressionRepositoryPort,
)
from app.contexts.messaging.domain.inbound_message import InboundMessage
from app.contexts.messaging.domain.intent import Intent
from app.contexts.messaging.domain.suppression import Suppression, SuppressionReason

_INBOUND_RECEIVED = "InboundReceived"
_REPLY_MATCHED = "ReplyMatched"
_REPLY_CLASSIFIED = "ReplyClassified"
REPLY_CLASSIFIED_VERSION = 2

_SUPPRESSION_REASONS = {
    Intent.UNSUBSCRIBE: SuppressionReason.UNSUBSCRIBE,
    Intent.BOUNCE: SuppressionReason.HARD_BOUNCE,
}


class PollInboxHandler:
    def __init__(
        self,
        mailbox_gateway: MailboxGatewayPort,
        outbound_repo: OutboundMessageRepositoryPort,
        inbound_repo: InboundMessageRepositoryPort,
        outbox: OutboxEventWriterPort,
        suppressions: SuppressionRepositoryPort,
        receiver: EmailReceiverPort,
        classifier: IntentClassifierPort,
    ) -> None:
        self._mailbox_gateway = mailbox_gateway
        self._outbound_repo = outbound_repo
        self._inbound_repo = inbound_repo
        self._outbox = outbox
        self._suppressions = suppressions
        self._receiver = receiver
        self._classifier = classifier

    async def run_once(self, mailbox: MailboxView) -> int:
        result = await self._receiver.fetch_new(
            mailbox_email=mailbox.email_address,
            since_cursor=mailbox.last_sync_cursor,
        )
        candidates = await self._outbound_repo.list_unanswered(mailbox.id)

        processed = 0
        for fetched in result.messages:
            if await self._inbound_repo.exists(mailbox.id, fetched.provider_message_id):
                continue

            inbound = InboundMessage.new(
                workspace_id=mailbox.workspace_id,
                mailbox_id=mailbox.id,
                provider_message_id=fetched.provider_message_id,
                provider_thread_id=fetched.provider_thread_id,
                from_email=fetched.from_email,
                subject=fetched.subject,
                snippet=fetched.snippet,
                in_reply_to_header=fetched.in_reply_to_header,
                references_header=fetched.references_header,
                received_at=fetched.received_at,
            )
            await self._inbound_repo.add(inbound)
            await self._outbox.record(
                _INBOUND_RECEIVED,
                mailbox.workspace_id,
                inbound.id,
                {
                    "workspace_id": mailbox.workspace_id,
                    "mailbox_id": mailbox.id,
                    "inbound_id": inbound.id,
                    "provider_message_id": inbound.provider_message_id,
                    "provider_thread_id": inbound.provider_thread_id,
                    "from_email": inbound.from_email,
                    "subject": inbound.subject,
                    "received_at": inbound.received_at,
                },
            )

            matched = match_reply(fetched, candidates)
            if matched is not None:
                candidates = [c for c in candidates if c.id != matched.id]
                inbound = inbound.matched_to(matched.id)
                await self._outbox.record(
                    _REPLY_MATCHED,
                    mailbox.workspace_id,
                    inbound.id,
                    {
                        "workspace_id": mailbox.workspace_id,
                        "inbound_id": inbound.id,
                        "matched_outbound_id": matched.id,
                        "provider_thread_id": inbound.provider_thread_id,
                    },
                )

                intent = (
                    Intent.BOUNCE
                    if fetched.is_bounce
                    else await self._classifier.classify(
                        fetched.subject, fetched.body_text or fetched.snippet
                    )
                )
                inbound = inbound.classified_as(intent)
                await self._inbound_repo.update(inbound)
                suppression_reason = _SUPPRESSION_REASONS.get(intent)
                if suppression_reason is not None:
                    await self._suppressions.add(
                        Suppression.new(
                            workspace_id=mailbox.workspace_id,
                            email=matched.to_email,
                            reason=suppression_reason,
                            source_inbound_id=inbound.id,
                        )
                    )
                await self._outbox.record(
                    _REPLY_CLASSIFIED,
                    mailbox.workspace_id,
                    inbound.id,
                    {
                        "event_version": REPLY_CLASSIFIED_VERSION,
                        "workspace_id": mailbox.workspace_id,
                        "inbound_id": inbound.id,
                        "matched_outbound_id": matched.id,
                        "intent": intent.value,
                    },
                )

            processed += 1

        await self._mailbox_gateway.advance_cursor(
            mailbox.workspace_id, result.new_cursor
        )
        return processed
