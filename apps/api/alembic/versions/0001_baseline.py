"""Baseline schema.

Revision ID: 0001
Revises:
Create Date: 2026-05-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default=sa.text("'draft'")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # NULLIF guards against the pooled-connection empty-string state: a
    # session that previously ran `SET LOCAL app.workspace_id = '<uuid>'`
    # returns to the pool with the GUC = '' (not NULL), and an unscoped
    # tenant query would otherwise crash with `invalid input syntax for
    # type uuid: ""`.
    # FORCE is required for the policy to apply to the table owner.
    # `workspaces` is intentionally not under RLS — it is the tenant
    # registry and must be readable to resolve the GUC for child tables.
    op.execute("ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE campaigns FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY workspace_isolation ON campaigns "
        "USING (workspace_id = "
        "NULLIF(current_setting('app.workspace_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("campaigns")
    op.drop_table("workspaces")
