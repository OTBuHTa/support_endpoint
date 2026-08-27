import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.communication import (
    Attachment,
    Conversation,
    InternalNote,
    Message,
    MessageDirection,
)
from app.models.workspace import Workspace
from app.repositories.audit_repo import AuditRepository
from app.repositories.communication_repo import CommunicationRepository
from app.repositories.ticket_repo import TicketRepository


class CommunicationService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repo = CommunicationRepository(db)
        self.tickets = TicketRepository(db)
        self.audit = AuditRepository(db)

    def _ticket(self, *, workspace_id: str, ticket_id: str):
        ticket = self.tickets.get_in_workspace(workspace_id=workspace_id, ticket_id=ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found")
        return ticket

    def _conversation(
        self, *, workspace_id: str, ticket_id: str, conversation_id: str
    ) -> Conversation:
        self._ticket(workspace_id=workspace_id, ticket_id=ticket_id)
        item = self.repo.get_conversation(
            workspace_id=workspace_id, ticket_id=ticket_id, conversation_id=conversation_id
        )
        if item is None:
            raise NotFoundError("Conversation not found")
        return item

    def create_conversation(
        self,
        *,
        workspace_id: str,
        ticket_id: str,
        actor_user_id: str,
        channel,
        subject: str,
        external_thread_ref: str | None,
    ) -> Conversation:
        self._ticket(workspace_id=workspace_id, ticket_id=ticket_id)
        item = self.repo.create_conversation(
            workspace_id=workspace_id,
            ticket_id=ticket_id,
            created_by_user_id=actor_user_id,
            channel=channel,
            subject=subject,
            external_thread_ref=external_thread_ref,
        )
        self.audit.record(
            action="communications.conversation.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="conversation",
            resource_id=item.id,
            metadata={"ticket_id": ticket_id, "channel": item.channel.value},
        )
        self.db.commit()
        return item

    def list_conversations(self, *, workspace_id: str, ticket_id: str) -> list[Conversation]:
        self._ticket(workspace_id=workspace_id, ticket_id=ticket_id)
        return self.repo.list_conversations(workspace_id=workspace_id, ticket_id=ticket_id)

    def create_outbound_message(
        self,
        *,
        workspace_id: str,
        ticket_id: str,
        conversation_id: str,
        actor_user_id: str,
        body: str,
    ) -> Message:
        conversation = self._conversation(
            workspace_id=workspace_id, ticket_id=ticket_id, conversation_id=conversation_id
        )
        item = self.repo.create_message(
            workspace_id=workspace_id,
            conversation_id=conversation.id,
            author_user_id=actor_user_id,
            direction=MessageDirection.OUTBOUND,
            body=body,
        )
        self.audit.record(
            action="communications.message.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="message",
            resource_id=item.id,
            metadata={"ticket_id": ticket_id, "direction": "outbound"},
        )
        self.db.commit()
        return item

    def create_inbound_message(
        self,
        *,
        workspace_id: str,
        ticket_id: str,
        conversation_id: str,
        actor_user_id: str,
        body: str,
        external_message_ref: str | None,
    ) -> Message:
        """Record an already-received customer message."""
        conversation = self._conversation(
            workspace_id=workspace_id, ticket_id=ticket_id, conversation_id=conversation_id
        )
        item = self.repo.create_message(
            workspace_id=workspace_id,
            conversation_id=conversation.id,
            author_user_id=None,
            direction=MessageDirection.INBOUND,
            body=body,
            external_message_ref=external_message_ref,
        )
        self.audit.record(
            action="communications.message.received",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="message",
            resource_id=item.id,
            metadata={"ticket_id": ticket_id, "direction": "inbound"},
        )
        self.db.commit()
        return item

    def list_messages(
        self, *, workspace_id: str, ticket_id: str, conversation_id: str
    ) -> list[Message]:
        conversation = self._conversation(
            workspace_id=workspace_id, ticket_id=ticket_id, conversation_id=conversation_id
        )
        return self.repo.list_messages(workspace_id=workspace_id, conversation_id=conversation.id)

    def create_note(
        self, *, workspace_id: str, ticket_id: str, actor_user_id: str, body: str
    ) -> InternalNote:
        self._ticket(workspace_id=workspace_id, ticket_id=ticket_id)
        item = self.repo.create_note(
            workspace_id=workspace_id,
            ticket_id=ticket_id,
            author_user_id=actor_user_id,
            body=body,
        )
        self.audit.record(
            action="communications.internal_note.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="internal_note",
            resource_id=item.id,
            metadata={"ticket_id": ticket_id},
        )
        self.db.commit()
        return item

    def list_notes(self, *, workspace_id: str, ticket_id: str) -> list[InternalNote]:
        self._ticket(workspace_id=workspace_id, ticket_id=ticket_id)
        return self.repo.list_notes(workspace_id=workspace_id, ticket_id=ticket_id)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        normalized = filename.replace("\\", "/").split("/")[-1].strip()
        normalized = "".join(ch for ch in normalized if ch.isprintable() and ch not in "\r\n\x00")
        if not normalized or normalized in {".", ".."} or len(normalized) > 255:
            raise ValidationAppError(
                "attachment filename is required and must be <= 255 printable characters"
            )
        return normalized

    def _validate_attachment(self, *, workspace_id: str, filename: str, content: bytes) -> str:
        safe_filename = self._safe_filename(filename)
        if not content:
            raise ValidationAppError("attachment is empty")
        if len(content) > self.settings.attachment_max_bytes:
            raise ValidationAppError("attachment exceeds the configured per-file size limit")

        workspace = self.db.scalar(
            select(Workspace).where(Workspace.id == workspace_id).with_for_update()
        )
        if workspace is None:
            raise NotFoundError("Workspace not found")
        used = self.repo.attachment_usage_bytes(workspace_id=workspace_id)
        if used + len(content) > self.settings.attachment_workspace_quota_bytes:
            raise ValidationAppError("workspace attachment storage quota exceeded")
        return safe_filename

    def attach_to_message(
        self,
        *,
        workspace_id: str,
        ticket_id: str,
        conversation_id: str,
        message_id: str,
        actor_user_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> Attachment:
        conversation = self._conversation(
            workspace_id=workspace_id, ticket_id=ticket_id, conversation_id=conversation_id
        )
        message = self.repo.get_message(
            workspace_id=workspace_id, conversation_id=conversation.id, message_id=message_id
        )
        if message is None:
            raise NotFoundError("Message not found")
        safe_filename = self._validate_attachment(
            workspace_id=workspace_id, filename=filename, content=content
        )
        item = self.repo.create_attachment(
            workspace_id=workspace_id,
            message_id=message.id,
            filename=safe_filename,
            content_type=content_type or "application/octet-stream",
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
        )
        self.audit.record(
            action="communications.attachment.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="attachment",
            resource_id=item.id,
            metadata={"ticket_id": ticket_id, "message_id": message.id, "size": len(content)},
        )
        self.db.commit()
        return item

    def attach_to_note(
        self,
        *,
        workspace_id: str,
        ticket_id: str,
        note_id: str,
        actor_user_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> Attachment:
        self._ticket(workspace_id=workspace_id, ticket_id=ticket_id)
        note = self.repo.get_note(workspace_id=workspace_id, ticket_id=ticket_id, note_id=note_id)
        if note is None:
            raise NotFoundError("Internal note not found")
        safe_filename = self._validate_attachment(
            workspace_id=workspace_id, filename=filename, content=content
        )
        item = self.repo.create_attachment(
            workspace_id=workspace_id,
            internal_note_id=note.id,
            filename=safe_filename,
            content_type=content_type or "application/octet-stream",
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
        )
        self.audit.record(
            action="communications.internal_attachment.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="attachment",
            resource_id=item.id,
            metadata={"ticket_id": ticket_id, "internal_note_id": note.id, "size": len(content)},
        )
        self.db.commit()
        return item

    def get_attachment_for_ticket(
        self,
        *,
        workspace_id: str,
        ticket_id: str,
        attachment_id: str,
        allow_internal: bool,
    ) -> Attachment:
        self._ticket(workspace_id=workspace_id, ticket_id=ticket_id)
        item = self.repo.get_attachment(workspace_id=workspace_id, attachment_id=attachment_id)
        if item is None:
            raise NotFoundError("Attachment not found")
        if item.message_id is not None:
            message = self.db.get(Message, item.message_id)
            if message is None:
                raise NotFoundError("Attachment not found")
            conversation = self.db.get(Conversation, message.conversation_id)
            if conversation is None or conversation.ticket_id != ticket_id:
                raise NotFoundError("Attachment not found")
            return item
        if item.internal_note_id is not None:
            if not allow_internal:
                raise NotFoundError("Attachment not found")
            note = self.db.get(InternalNote, item.internal_note_id)
            if note is None or note.ticket_id != ticket_id:
                raise NotFoundError("Attachment not found")
            return item
        raise NotFoundError("Attachment not found")
