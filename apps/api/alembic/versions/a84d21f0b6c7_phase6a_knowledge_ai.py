"""phase6a knowledge and advisory AI

Revision ID: a84d21f0b6c7
Revises: 7c5a0d3e91f2
Create Date: 2026-08-27
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "a84d21f0b6c7"
down_revision: str | None = "7c5a0d3e91f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_ROLE_PERMISSIONS = {
    "operator": ("knowledge.read", "ai.assist"),
    "supervisor": ("knowledge.read", "knowledge.write", "ai.assist"),
    "administrator": ("knowledge.read", "knowledge.write", "ai.assist"),
}


def upgrade() -> None:
    op.create_table(
        "knowledge_articles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("author_user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_articles_workspace_id", "knowledge_articles", ["workspace_id"])
    op.create_index("ix_knowledge_articles_status", "knowledge_articles", ["status"])

    op.create_table(
        "ai_suggestions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("ticket_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_suggestions_workspace_id", "ai_suggestions", ["workspace_id"])
    op.create_index("ix_ai_suggestions_ticket_id", "ai_suggestions", ["ticket_id"])
    op.create_index("ix_ai_suggestions_kind", "ai_suggestions", ["kind"])

    bind = op.get_bind()
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("description", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    roles = sa.table("roles", sa.column("id", sa.String), sa.column("name", sa.String))
    role_permissions = sa.table(
        "role_permissions",
        sa.column("id", sa.String),
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
    )
    now = datetime.now(UTC)
    permission_ids: dict[str, str] = {}
    for code in {c for codes in _NEW_ROLE_PERMISSIONS.values() for c in codes}:
        existing = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
        if existing is None:
            existing = str(uuid.uuid4())
            bind.execute(
                permissions.insert().values(
                    id=existing,
                    code=code,
                    description="",
                    created_at=now,
                    updated_at=now,
                )
            )
        permission_ids[code] = str(existing)

    for role_name, codes in _NEW_ROLE_PERMISSIONS.items():
        role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == role_name)).scalar()
        if role_id is None:
            continue
        for code in codes:
            permission_id = permission_ids[code]
            exists = bind.execute(
                sa.select(role_permissions.c.id).where(
                    role_permissions.c.role_id == role_id,
                    role_permissions.c.permission_id == permission_id,
                )
            ).scalar()
            if exists is None:
                bind.execute(
                    role_permissions.insert().values(
                        id=str(uuid.uuid4()), role_id=role_id, permission_id=permission_id
                    )
                )


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table(
        "permissions", sa.column("id", sa.String), sa.column("code", sa.String)
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
    )
    codes = {c for values in _NEW_ROLE_PERMISSIONS.values() for c in values}
    ids = list(
        bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_(codes))).scalars()
    )
    if ids:
        bind.execute(role_permissions.delete().where(role_permissions.c.permission_id.in_(ids)))
        bind.execute(permissions.delete().where(permissions.c.id.in_(ids)))

    op.drop_index("ix_ai_suggestions_kind", table_name="ai_suggestions")
    op.drop_index("ix_ai_suggestions_ticket_id", table_name="ai_suggestions")
    op.drop_index("ix_ai_suggestions_workspace_id", table_name="ai_suggestions")
    op.drop_table("ai_suggestions")
    op.drop_index("ix_knowledge_articles_status", table_name="knowledge_articles")
    op.drop_index("ix_knowledge_articles_workspace_id", table_name="knowledge_articles")
    op.drop_table("knowledge_articles")
