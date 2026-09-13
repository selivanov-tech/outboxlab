"""Step 3: campaign steps, leads, the send-job queue and sending guards.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels = None
depends_on = None

_NEW_TENANT_TABLES = (
    "campaign__steps",
    "campaign__leads",
    "campaign__send_jobs",
    "messaging__suppressions",
)


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY workspace_isolation ON {table} "
        "USING (workspace_id = "
        "NULLIF(current_setting('app.workspace_id', true), '')::uuid)"
    )


def _workspace_fk() -> sa.Column:
    return sa.Column(
        "workspace_id",
        UUID(as_uuid=True),
        sa.ForeignKey("identity__workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )


def upgrade() -> None:
    op.add_column(
        "campaign__campaigns",
        sa.Column(
            "mailbox_id",
            UUID(as_uuid=True),
            sa.ForeignKey("mailbox__mailboxes.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.alter_column("campaign__campaigns", "status", server_default=None)
    op.alter_column("campaign__campaigns", "created_at", server_default=None)

    op.create_table(
        "campaign__steps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        _workspace_fk(),
        sa.Column(
            "campaign_id",
            UUID(as_uuid=True),
            sa.ForeignKey("campaign__campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("delay_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "campaign_id", "position", name="uq_steps_campaign_position"
        ),
    )

    op.create_table(
        "campaign__leads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        _workspace_fk(),
        sa.Column(
            "campaign_id",
            UUID(as_uuid=True),
            sa.ForeignKey("campaign__campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("steps_sent", sa.Integer(), nullable=False),
        sa.Column("stop_reason", sa.String(32), nullable=True),
        sa.Column("reply_intent", sa.String(16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("campaign_id", "email", name="uq_leads_campaign_email"),
    )

    op.create_table(
        "campaign__send_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        _workspace_fk(),
        sa.Column(
            "mailbox_id",
            UUID(as_uuid=True),
            sa.ForeignKey("mailbox__mailboxes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lead_id",
            UUID(as_uuid=True),
            sa.ForeignKey("campaign__leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "step_id",
            UUID(as_uuid=True),
            sa.ForeignKey("campaign__steps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(128), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("outbound_message_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_send_jobs_pending",
        "campaign__send_jobs",
        ["scheduled_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_send_jobs_running",
        "campaign__send_jobs",
        ["locked_at"],
        postgresql_where=sa.text("status = 'running'"),
    )
    op.create_index(
        "ix_send_jobs_outbound_message_id",
        "campaign__send_jobs",
        ["outbound_message_id"],
    )
    op.create_index("ix_send_jobs_lead_id", "campaign__send_jobs", ["lead_id"])

    op.add_column(
        "mailbox__mailboxes",
        sa.Column(
            "daily_send_cap",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("20"),
        ),
    )
    op.create_index(
        "ix_outbound_messages_mailbox_created_at",
        "messaging__outbound_messages",
        ["mailbox_id", "created_at"],
    )
    op.create_table(
        "messaging__suppressions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        _workspace_fk(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column(
            "source_inbound_id",
            UUID(as_uuid=True),
            sa.ForeignKey("messaging__inbound_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "workspace_id",
            "email",
            "reason",
            name="uq_suppressions_workspace_email_reason",
        ),
    )

    for table in _NEW_TENANT_TABLES:
        _enable_rls(table)


def downgrade() -> None:
    op.drop_table("messaging__suppressions")
    op.drop_index(
        "ix_outbound_messages_mailbox_created_at",
        table_name="messaging__outbound_messages",
    )
    op.drop_column("mailbox__mailboxes", "daily_send_cap")
    op.drop_table("campaign__send_jobs")
    op.drop_table("campaign__leads")
    op.drop_table("campaign__steps")
    op.alter_column("campaign__campaigns", "created_at", server_default=sa.func.now())
    op.alter_column("campaign__campaigns", "status", server_default=sa.text("'draft'"))
    op.drop_column("campaign__campaigns", "mailbox_id")
