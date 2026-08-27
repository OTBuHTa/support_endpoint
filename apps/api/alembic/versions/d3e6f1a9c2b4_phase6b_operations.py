"""phase6b deterministic operations

Revision ID: d3e6f1a9c2b4
Revises: a84d21f0b6c7
Create Date: 2026-08-27
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "d3e6f1a9c2b4"
down_revision: str | None = "a84d21f0b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_ROLE_PERMISSIONS = {
    "operator": ("tasks.read", "tasks.write", "sla.read", "notifications.read"),
    "supervisor": (
        "tasks.read",
        "tasks.write",
        "sla.read",
        "sla.manage",
        "notifications.read",
    ),
    "administrator": (
        "tasks.read",
        "tasks.write",
        "sla.read",
        "sla.manage",
        "notifications.read",
    ),
}


def upgrade() -> None:
    op.create_table(
        "support_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("ticket_id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("assignee_user_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_tasks_workspace_id", "support_tasks", ["workspace_id"])
    op.create_index("ix_support_tasks_ticket_id", "support_tasks", ["ticket_id"])
    op.create_index("ix_support_tasks_assignee_user_id", "support_tasks", ["assignee_user_id"])
    op.create_index("ix_support_tasks_status", "support_tasks", ["status"])
    op.create_index("ix_support_tasks_due_at", "support_tasks", ["due_at"])

    op.create_table(
        "sla_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("first_response_minutes", sa.Integer(), nullable=False),
        sa.Column("resolution_minutes", sa.Integer(), nullable=False),
        sa.Column("warning_minutes_before", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "priority", name="uq_sla_policy_workspace_priority"),
    )
    op.create_index("ix_sla_policies_workspace_id", "sla_policies", ["workspace_id"])

    op.create_table(
        "ticket_slas",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("ticket_id", sa.String(length=36), nullable=False),
        sa.Column("policy_id", sa.String(length=36), nullable=False),
        sa.Column("first_response_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_response_warning_sent", sa.Boolean(), nullable=False),
        sa.Column("resolution_warning_sent", sa.Boolean(), nullable=False),
        sa.Column("first_response_breached", sa.Boolean(), nullable=False),
        sa.Column("resolution_breached", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_id"], ["sla_policies.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", name="uq_ticket_sla_ticket"),
    )
    op.create_index("ix_ticket_slas_workspace_id", "ticket_slas", ["workspace_id"])
    op.create_index("ix_ticket_slas_ticket_id", "ticket_slas", ["ticket_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("ticket_id", sa.String(length=36), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_workspace_id", "notifications", ["workspace_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_ticket_id", "notifications", ["ticket_id"])
    op.create_index("ix_notifications_type", "notifications", ["type"])

    _grant_permissions()


def _grant_permissions() -> None:
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
    all_codes = {code for codes in _NEW_ROLE_PERMISSIONS.values() for code in codes}
    for code in all_codes:
        permission_id = bind.execute(
            sa.select(permissions.c.id).where(permissions.c.code == code)
        ).scalar()
        if permission_id is None:
            permission_id = str(uuid.uuid4())
            bind.execute(
                permissions.insert().values(
                    id=permission_id,
                    code=code,
                    description="",
                    created_at=now,
                    updated_at=now,
                )
            )
        permission_ids[code] = str(permission_id)

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
                        id=str(uuid.uuid4()),
                        role_id=role_id,
                        permission_id=permission_id,
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
    codes = {code for values in _NEW_ROLE_PERMISSIONS.values() for code in values}
    ids = list(
        bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_(codes))).scalars()
    )
    if ids:
        bind.execute(role_permissions.delete().where(role_permissions.c.permission_id.in_(ids)))
        bind.execute(permissions.delete().where(permissions.c.id.in_(ids)))

    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_index("ix_notifications_ticket_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_workspace_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_ticket_slas_ticket_id", table_name="ticket_slas")
    op.drop_index("ix_ticket_slas_workspace_id", table_name="ticket_slas")
    op.drop_table("ticket_slas")
    op.drop_index("ix_sla_policies_workspace_id", table_name="sla_policies")
    op.drop_table("sla_policies")
    op.drop_index("ix_support_tasks_due_at", table_name="support_tasks")
    op.drop_index("ix_support_tasks_status", table_name="support_tasks")
    op.drop_index("ix_support_tasks_assignee_user_id", table_name="support_tasks")
    op.drop_index("ix_support_tasks_ticket_id", table_name="support_tasks")
    op.drop_index("ix_support_tasks_workspace_id", table_name="support_tasks")
    op.drop_table("support_tasks")
