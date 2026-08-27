"""phase5 communications

Revision ID: 7c5a0d3e91f2
Revises: 409a43b6879d
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7c5a0d3e91f2"
down_revision: str | None = "409a43b6879d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("ticket_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("external_thread_ref", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_workspace_id", "conversations", ["workspace_id"])
    op.create_index("ix_conversations_ticket_id", "conversations", ["ticket_id"])
    op.create_index("ix_conversations_channel", "conversations", ["channel"])
    op.create_index(
        "ix_conversations_external_thread_ref", "conversations", ["external_thread_ref"]
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("author_user_id", sa.String(length=36), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("external_message_ref", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_workspace_id", "messages", ["workspace_id"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_direction", "messages", ["direction"])
    op.create_index("ix_messages_external_message_ref", "messages", ["external_message_ref"])

    op.create_table(
        "internal_notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("ticket_id", sa.String(length=36), nullable=False),
        sa.Column("author_user_id", sa.String(length=36), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_internal_notes_workspace_id", "internal_notes", ["workspace_id"])
    op.create_index("ix_internal_notes_ticket_id", "internal_notes", ["ticket_id"])

    op.create_table(
        "attachments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=True),
        sa.Column("internal_note_id", sa.String(length=36), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(message_id IS NOT NULL AND internal_note_id IS NULL) OR "
            "(message_id IS NULL AND internal_note_id IS NOT NULL)",
            name="ck_attachment_exactly_one_parent",
        ),
        sa.ForeignKeyConstraint(["internal_note_id"], ["internal_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attachments_workspace_id", "attachments", ["workspace_id"])
    op.create_index("ix_attachments_message_id", "attachments", ["message_id"])
    op.create_index("ix_attachments_internal_note_id", "attachments", ["internal_note_id"])
    op.create_index("ix_attachments_sha256", "attachments", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_attachments_sha256", table_name="attachments")
    op.drop_index("ix_attachments_internal_note_id", table_name="attachments")
    op.drop_index("ix_attachments_message_id", table_name="attachments")
    op.drop_index("ix_attachments_workspace_id", table_name="attachments")
    op.drop_table("attachments")
    op.drop_index("ix_internal_notes_ticket_id", table_name="internal_notes")
    op.drop_index("ix_internal_notes_workspace_id", table_name="internal_notes")
    op.drop_table("internal_notes")
    op.drop_index("ix_messages_external_message_ref", table_name="messages")
    op.drop_index("ix_messages_direction", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_index("ix_messages_workspace_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_external_thread_ref", table_name="conversations")
    op.drop_index("ix_conversations_channel", table_name="conversations")
    op.drop_index("ix_conversations_ticket_id", table_name="conversations")
    op.drop_index("ix_conversations_workspace_id", table_name="conversations")
    op.drop_table("conversations")
