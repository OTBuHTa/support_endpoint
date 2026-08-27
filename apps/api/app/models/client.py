from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class ClientOrganization(TimestampMixin, Base):
    """A company/business account a workspace does business with.
    Optional parent of one or more Client records (see ADR-004 for
    why Client/ClientOrganization/ClientContact are split this way).
    """

    __tablename__ = "client_organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    clients: Mapped[list["Client"]] = relationship(back_populates="organization")


class Client(TimestampMixin, Base):
    """The primary CRM record a Ticket (Phase 4) attaches to — an
    individual person, optionally affiliated with a ClientOrganization.
    """

    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("client_organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_email: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    primary_phone: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization: Mapped["ClientOrganization | None"] = relationship(back_populates="clients")
    contacts: Mapped[list["ClientContact"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )


class ClientContact(TimestampMixin, Base):
    """An additional named contact channel for a Client — e.g. a
    secondary email, phone, or role-labeled contact point. Kept
    separate from Client's own primary_email/primary_phone so a
    Client can have several without schema changes.
    """

    __tablename__ = "client_contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False, default="email")
    value: Mapped[str] = mapped_column(String(255), nullable=False)

    client: Mapped["Client"] = relationship(back_populates="contacts")
