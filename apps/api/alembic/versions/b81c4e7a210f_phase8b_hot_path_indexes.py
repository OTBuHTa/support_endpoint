"""phase8b hot path indexes

Revision ID: b81c4e7a210f
Revises: f7b2c4d8e1a0
Create Date: 2026-08-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b81c4e7a210f"
down_revision: str | None = "f7b2c4d8e1a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_tickets_workspace_created",
        "tickets",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_tickets_workspace_status_created",
        "tickets",
        ["workspace_id", "status", "created_at"],
    )
    op.create_index(
        "ix_tickets_workspace_assignee_created",
        "tickets",
        ["workspace_id", "assignee_user_id", "created_at"],
    )
    op.create_index(
        "ix_tickets_workspace_client_created",
        "tickets",
        ["workspace_id", "client_id", "created_at"],
    )
    op.create_index(
        "ix_support_tasks_workspace_created",
        "support_tasks",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_notifications_workspace_user_created",
        "notifications",
        ["workspace_id", "user_id", "created_at"],
    )
    op.create_index(
        "ix_ticket_slas_workspace_due",
        "ticket_slas",
        ["workspace_id", "resolution_due_at"],
    )
    op.create_index(
        "ix_audit_ticket_status_created",
        "audit_events",
        ["workspace_id", "resource_type", "resource_id", "action", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_ticket_status_created", table_name="audit_events")
    op.drop_index("ix_ticket_slas_workspace_due", table_name="ticket_slas")
    op.drop_index("ix_notifications_workspace_user_created", table_name="notifications")
    op.drop_index("ix_support_tasks_workspace_created", table_name="support_tasks")
    op.drop_index("ix_tickets_workspace_client_created", table_name="tickets")
    op.drop_index("ix_tickets_workspace_assignee_created", table_name="tickets")
    op.drop_index("ix_tickets_workspace_status_created", table_name="tickets")
    op.drop_index("ix_tickets_workspace_created", table_name="tickets")
