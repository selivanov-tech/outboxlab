"""Prefix released identity + campaign tables with their bounded-context name.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-31
"""

from __future__ import annotations

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels = None
depends_on = None

# Foreign keys (mailbox__mailboxes etc. -> workspaces) and the workspace_isolation
# RLS policy on campaigns travel with the table OID, so a rename repoints them
# automatically — only the table name changes here.
_RENAMES = (
    ("workspaces", "identity__workspaces"),
    ("campaigns", "campaign__campaigns"),
)


def upgrade() -> None:
    for old, new in _RENAMES:
        op.rename_table(old, new)


def downgrade() -> None:
    for old, new in reversed(_RENAMES):
        op.rename_table(new, old)
