"""Step 3: processed-events set for the first outbox consumer.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaign__processed_events",
        sa.Column("event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity__workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("ALTER TABLE campaign__processed_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE campaign__processed_events FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY workspace_isolation ON campaign__processed_events "
        "USING (workspace_id = "
        "NULLIF(current_setting('app.workspace_id', true), '')::uuid)"
    )
    op.create_index(
        "ix_outbox_events_event_type_created_at",
        "messaging__outbox_events",
        ["event_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_outbox_events_event_type_created_at",
        table_name="messaging__outbox_events",
    )
    op.drop_table("campaign__processed_events")
