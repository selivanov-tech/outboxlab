"""Step 2: mailbox + messaging tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels = None
depends_on = None

# mailbox__mailboxes carries a workspace_id FK (tenant data), so — unlike the
# identity registry — it is under RLS too. The worker sets app.workspace_id from
# MAILBOX_WORKSPACE_ID before reading it, so there is no bootstrap cycle.
# FORCE makes the policy apply to the table owner; NULLIF guards the pooled
# empty-string GUC state (see 0001_baseline).
_TENANT_TABLES = (
    "mailbox__mailboxes",
    "messaging__outbound_messages",
    "messaging__inbound_messages",
    "messaging__outbox_events",
)

# The identity table is still named "workspaces" at this revision; 0003 renames
# it to identity__workspaces and Postgres repoints these FKs automatically. Do
# not change the "workspaces.id" targets below to the prefixed name — 0002 runs
# before 0003 and would fail with "relation identity__workspaces does not exist".
_IDENTITY_FK = "workspaces.id"


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY workspace_isolation ON {table} "
        "USING (workspace_id = "
        "NULLIF(current_setting('app.workspace_id', true), '')::uuid)"
    )


def upgrade() -> None:
    op.create_table(
        "mailbox__mailboxes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey(_IDENTITY_FK, ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email_address", sa.String(320), nullable=False),
        sa.Column("last_sync_cursor", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "messaging__outbound_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey(_IDENTITY_FK, ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mailbox_id",
            UUID(as_uuid=True),
            sa.ForeignKey("mailbox__mailboxes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("to_email", sa.String(320), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("rfc822_message_id", sa.String(998), nullable=False, unique=True),
        sa.Column("provider_message_id", sa.String(64), nullable=True),
        sa.Column("provider_thread_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_outbound_messages_provider_thread_id",
        "messaging__outbound_messages",
        ["provider_thread_id"],
    )

    op.create_table(
        "messaging__inbound_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey(_IDENTITY_FK, ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mailbox_id",
            UUID(as_uuid=True),
            sa.ForeignKey("mailbox__mailboxes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_message_id", sa.String(64), nullable=False),
        sa.Column("provider_thread_id", sa.String(64), nullable=False),
        sa.Column("from_email", sa.String(320), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("in_reply_to_header", sa.Text(), nullable=True),
        sa.Column("references_header", sa.Text(), nullable=True),
        sa.Column(
            "matched_outbound_id",
            UUID(as_uuid=True),
            sa.ForeignKey("messaging__outbound_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("intent", sa.String(16), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "mailbox_id", "provider_message_id", name="uq_inbound_mailbox_provider_msg"
        ),
    )
    op.create_index(
        "ix_inbound_messages_provider_thread_id",
        "messaging__inbound_messages",
        ["provider_thread_id"],
    )

    op.create_table(
        "messaging__outbox_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey(_IDENTITY_FK, ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", UUID(as_uuid=True), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_outbox_events_created_at", "messaging__outbox_events", ["created_at"]
    )

    for table in _TENANT_TABLES:
        _enable_rls(table)


def downgrade() -> None:
    op.drop_table("messaging__outbox_events")
    op.drop_table("messaging__inbound_messages")
    op.drop_table("messaging__outbound_messages")
    op.drop_table("mailbox__mailboxes")
