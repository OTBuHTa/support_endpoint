from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid
from app.models.ticket_enums import TicketPriority, TicketStatus


class Queue(TimestampMixin, Base):
    """A workspace-defined routing group tickets are placed in (e.g.
    "Support", "Billing"). Workspace-customizable, unlike TicketStatus/
    TicketPriority.
    """

    __tablename__ = "queues"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_queue_workspace_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TicketCategory(TimestampMixin, Base):
    """A workspace-defined ticket category (e.g. "Bug", "Billing
    question"). Workspace-customizable.
    """

    __tablename__ = "ticket_categories"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_category_workspace_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Tag(TimestampMixin, Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_tag_workspace_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="")


class Ticket(TimestampMixin, Base):
    """The core Service Desk entity. `assignee_user_id` is a
    denormalized pointer to the *current* assignee for fast filtering;
    the authoritative history of who was assigned when lives in
    `TicketAssignment` (see ADR-005).
    """

    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assignee_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    queue_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("queues.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ticket_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, native_enum=False, length=32),
        nullable=False,
        default=TicketStatus.NEW,
        index=True,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, native_enum=False, length=16),
        nullable=False,
        default=TicketPriority.MEDIUM,
        index=True,
    )

    tags: Mapped[list["TicketTag"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["TicketAssignment"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketAssignment.created_at",
    )


class TicketAssignment(TimestampMixin, Base):
    """One row per assignment *change* — an append-only history log.
    `assignee_user_id` is nullable to represent an "unassigned" event.
    """

    __tablename__ = "ticket_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignee_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="assignments")


class TicketTag(Base):
    __tablename__ = "ticket_tags"
    __table_args__ = (UniqueConstraint("ticket_id", "tag_id", name="uq_ticket_tag"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()
