import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db.base import Base


class OutboundMessage(Base):
    __tablename__ = "messaging__outbound_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity__workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    mailbox_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mailbox__mailboxes.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_email: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    rfc822_message_id: Mapped[str] = mapped_column(
        String(998), nullable=False, unique=True
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_thread_id: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class InboundMessage(Base):
    __tablename__ = "messaging__inbound_messages"
    __table_args__ = (
        UniqueConstraint(
            "mailbox_id", "provider_message_id", name="uq_inbound_mailbox_provider_msg"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity__workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    mailbox_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mailbox__mailboxes.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_message_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_thread_id: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )
    from_email: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    in_reply_to_header: Mapped[str | None] = mapped_column(Text, nullable=True)
    references_header: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_outbound_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messaging__outbound_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    intent: Mapped[str | None] = mapped_column(String(16), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class OutboxEvent(Base):
    __tablename__ = "messaging__outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity__workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )


__all__ = ["OutboundMessage", "InboundMessage", "OutboxEvent"]
