from enum import StrEnum

from sqlalchemy import BigInteger, Enum, ForeignKey, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class ConversationChannel(StrEnum):
    WEB = "web"
    EMAIL = "email"
    CHAT = "chat"
    PHONE = "phone"
    API = "api"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    channel: Mapped[ConversationChannel] = mapped_column(
        Enum(ConversationChannel, native_enum=False, length=16), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    external_thread_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(TimestampMixin, Base):
    """Customer-visible conversation message.

    Internal operator-only content deliberately lives in InternalNote,
    rather than a visibility flag on this table. This makes accidental
    client exposure substantially harder.
    """

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection, native_enum=False, length=16), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    external_message_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class InternalNote(TimestampMixin, Base):
    """Operator-only note. Never returned by customer-facing message APIs."""

    __tablename__ = "internal_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="internal_note", cascade="all, delete-orphan"
    )


class Attachment(TimestampMixin, Base):
    """Small attachment stored in Postgres for Phase 5.

    The service layer enforces a strict size cap. A later production
    hardening phase may move blobs to object storage without changing
    the authorization model or public attachment identifiers.
    """

    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True, index=True
    )
    internal_note_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("internal_notes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False, default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    message: Mapped[Message | None] = relationship(back_populates="attachments")
    internal_note: Mapped[InternalNote | None] = relationship(back_populates="attachments")
