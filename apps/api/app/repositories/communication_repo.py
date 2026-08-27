from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.communication import Attachment, Conversation, InternalNote, Message, MessageDirection


class CommunicationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_conversation(
        self,
        *,
        workspace_id: str,
        ticket_id: str,
        created_by_user_id: str,
        channel,
        subject: str,
        external_thread_ref: str | None,
    ) -> Conversation:
        item = Conversation(
            workspace_id=workspace_id,
            ticket_id=ticket_id,
            created_by_user_id=created_by_user_id,
            channel=channel,
            subject=subject,
            external_thread_ref=external_thread_ref,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_conversation(
        self, *, workspace_id: str, ticket_id: str, conversation_id: str
    ) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
            Conversation.ticket_id == ticket_id,
        )
        return self.db.scalar(stmt)

    def list_conversations(self, *, workspace_id: str, ticket_id: str) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.workspace_id == workspace_id, Conversation.ticket_id == ticket_id)
            .order_by(Conversation.created_at)
        )
        return list(self.db.scalars(stmt))

    def create_message(
        self,
        *,
        workspace_id: str,
        conversation_id: str,
        author_user_id: str | None,
        direction: MessageDirection,
        body: str,
        external_message_ref: str | None = None,
    ) -> Message:
        item = Message(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            author_user_id=author_user_id,
            direction=direction,
            body=body,
            external_message_ref=external_message_ref,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_message(
        self, *, workspace_id: str, conversation_id: str, message_id: str
    ) -> Message | None:
        stmt = select(Message).where(
            Message.id == message_id,
            Message.workspace_id == workspace_id,
            Message.conversation_id == conversation_id,
        )
        return self.db.scalar(stmt)

    def list_messages(self, *, workspace_id: str, conversation_id: str) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.workspace_id == workspace_id, Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return list(self.db.scalars(stmt))

    def create_note(
        self, *, workspace_id: str, ticket_id: str, author_user_id: str, body: str
    ) -> InternalNote:
        item = InternalNote(
            workspace_id=workspace_id,
            ticket_id=ticket_id,
            author_user_id=author_user_id,
            body=body,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_note(self, *, workspace_id: str, ticket_id: str, note_id: str) -> InternalNote | None:
        stmt = select(InternalNote).where(
            InternalNote.id == note_id,
            InternalNote.workspace_id == workspace_id,
            InternalNote.ticket_id == ticket_id,
        )
        return self.db.scalar(stmt)

    def list_notes(self, *, workspace_id: str, ticket_id: str) -> list[InternalNote]:
        stmt = (
            select(InternalNote)
            .where(InternalNote.workspace_id == workspace_id, InternalNote.ticket_id == ticket_id)
            .order_by(InternalNote.created_at)
        )
        return list(self.db.scalars(stmt))

    def create_attachment(
        self,
        *,
        workspace_id: str,
        filename: str,
        content_type: str,
        content: bytes,
        sha256: str,
        message_id: str | None = None,
        internal_note_id: str | None = None,
    ) -> Attachment:
        item = Attachment(
            workspace_id=workspace_id,
            filename=filename,
            content_type=content_type,
            content=content,
            size_bytes=len(content),
            sha256=sha256,
            message_id=message_id,
            internal_note_id=internal_note_id,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_attachment(self, *, workspace_id: str, attachment_id: str) -> Attachment | None:
        stmt = select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.workspace_id == workspace_id,
        )
        return self.db.scalar(stmt)
