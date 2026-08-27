from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid
from app.models.ticket_enums import TicketPriority


class TaskStatus(StrEnum):
    OPEN = "open"
    DONE = "done"
    CANCELLED = "cancelled"


class NotificationType(StrEnum):
    TASK_ASSIGNED = "task_assigned"
    SLA_WARNING = "sla_warning"
    SLA_BREACHED = "sla_breached"
    TICKET_ASSIGNED = "ticket_assigned"


class SupportTask(TimestampMixin, Base):
    __tablename__ = "support_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assignee_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, length=16),
        nullable=False,
        default=TaskStatus.OPEN,
        index=True,
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class SLAPolicy(TimestampMixin, Base):
    __tablename__ = "sla_policies"
    __table_args__ = (
        UniqueConstraint("workspace_id", "priority", name="uq_sla_policy_workspace_priority"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, native_enum=False, length=16), nullable=False
    )
    first_response_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_minutes_before: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TicketSLA(TimestampMixin, Base):
    __tablename__ = "ticket_slas"
    __table_args__ = (UniqueConstraint("ticket_id", name="uq_ticket_sla_ticket"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sla_policies.id", ondelete="RESTRICT"), nullable=False
    )
    first_response_due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolution_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_response_warning_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    resolution_warning_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    first_response_breached: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    resolution_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=True, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False, length=32), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
