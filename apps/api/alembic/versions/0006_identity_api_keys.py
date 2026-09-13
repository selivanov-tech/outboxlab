"""Step 4: workspace API keys.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity__api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity__workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("secret_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("prefix", name="uq_api_keys_prefix"),
    )


def downgrade() -> None:
    op.drop_table("identity__api_keys")
