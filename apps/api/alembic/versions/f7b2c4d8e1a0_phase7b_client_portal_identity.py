"""phase7b client portal identity

Revision ID: f7b2c4d8e1a0
Revises: d3e6f1a9c2b4
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7b2c4d8e1a0"
down_revision: str | None = "d3e6f1a9c2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "client_user_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("linked_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id", "user_id", name="uq_client_user_link_workspace_user"
        ),
        sa.UniqueConstraint(
            "workspace_id", "client_id", name="uq_client_user_link_workspace_client"
        ),
    )
    op.create_index("ix_client_user_links_workspace_id", "client_user_links", ["workspace_id"])
    op.create_index("ix_client_user_links_client_id", "client_user_links", ["client_id"])
    op.create_index("ix_client_user_links_user_id", "client_user_links", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_client_user_links_user_id", table_name="client_user_links")
    op.drop_index("ix_client_user_links_client_id", table_name="client_user_links")
    op.drop_index("ix_client_user_links_workspace_id", table_name="client_user_links")
    op.drop_table("client_user_links")
