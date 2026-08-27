from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.client import Client
from app.models.communication import Conversation, ConversationChannel, Message, MessageDirection
from app.models.portal import ClientUserLink
from app.models.ticket import Ticket
from app.models.ticket_enums import TicketPriority
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.audit_repo import AuditRepository
from app.repositories.user_repo import UserRepository


class PortalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditRepository(db)

    def link_client_user(
        self,
        *,
        workspace_id: str,
        client_id: str,
        user_email: str,
        actor_user_id: str,
    ) -> ClientUserLink:
        client = self.db.scalar(
            select(Client).where(Client.id == client_id, Client.workspace_id == workspace_id)
        )
        if client is None:
            raise NotFoundError("Client not found")
        user = UserRepository(self.db).get_by_email(user_email)
        if user is None or not user.is_active:
            raise ValidationAppError("Active user account not found for this email")
        existing = self.db.scalar(
            select(ClientUserLink).where(
                ClientUserLink.workspace_id == workspace_id,
                (ClientUserLink.user_id == user.id) | (ClientUserLink.client_id == client_id),
            )
        )
        if existing is not None:
            if existing.user_id == user.id and existing.client_id == client_id:
                return existing
            raise ValidationAppError("User or client is already linked in this workspace")
        link = ClientUserLink(
            workspace_id=workspace_id,
            client_id=client_id,
            user_id=user.id,
            linked_by_user_id=actor_user_id,
        )
        self.db.add(link)
        self.db.flush()
        self.audit.record(
            action="portal.client_user_link.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="client_user_link",
            resource_id=link.id,
            metadata={"client_id": client_id, "user_id": user.id},
        )
        self.db.commit()
        return link

    def accounts(self, *, user_id: str) -> list[dict]:
        rows = self.db.execute(
            select(ClientUserLink, Client, Workspace)
            .join(Client, Client.id == ClientUserLink.client_id)
            .join(Workspace, Workspace.id == ClientUserLink.workspace_id)
            .where(ClientUserLink.user_id == user_id, Client.is_active.is_(True))
            .order_by(Workspace.name, Client.full_name)
        ).all()
        return [
            {
                "link_id": link.id,
                "workspace_id": link.workspace_id,
                "workspace_name": workspace.name,
                "client_id": client.id,
                "client_name": client.full_name,
            }
            for link, client, workspace in rows
        ]

    def _link(self, *, user_id: str, link_id: str) -> ClientUserLink:
        link = self.db.scalar(
            select(ClientUserLink).where(
                ClientUserLink.id == link_id,
                ClientUserLink.user_id == user_id,
            )
        )
        if link is None:
            raise NotFoundError("Portal account not found")
        return link

    def _ticket(self, *, link: ClientUserLink, ticket_id: str) -> Ticket:
        ticket = self.db.scalar(
            select(Ticket).where(
                Ticket.id == ticket_id,
                Ticket.workspace_id == link.workspace_id,
                Ticket.client_id == link.client_id,
            )
        )
        if ticket is None:
            raise NotFoundError("Ticket not found")
        return ticket

    def list_tickets(self, *, user_id: str, link_id: str) -> list[Ticket]:
        link = self._link(user_id=user_id, link_id=link_id)
        return list(
            self.db.scalars(
                select(Ticket)
                .where(
                    Ticket.workspace_id == link.workspace_id,
                    Ticket.client_id == link.client_id,
                )
                .order_by(Ticket.created_at.desc())
            )
        )

    def create_ticket(
        self,
        *,
        user_id: str,
        link_id: str,
        subject: str,
        description: str,
        priority: TicketPriority,
    ) -> Ticket:
        link = self._link(user_id=user_id, link_id=link_id)
        ticket = Ticket(
            workspace_id=link.workspace_id,
            client_id=link.client_id,
            creator_user_id=user_id,
            subject=subject,
            description=description,
            priority=priority,
        )
        self.db.add(ticket)
        self.db.flush()
        self.audit.record(
            action="portal.ticket.created",
            workspace_id=link.workspace_id,
            actor_user_id=user_id,
            resource_type="ticket",
            resource_id=ticket.id,
            metadata={"client_id": link.client_id},
        )
        self.db.commit()
        return ticket

    def get_ticket(self, *, user_id: str, link_id: str, ticket_id: str) -> Ticket:
        link = self._link(user_id=user_id, link_id=link_id)
        return self._ticket(link=link, ticket_id=ticket_id)

    def list_messages(self, *, user_id: str, link_id: str, ticket_id: str) -> list[Message]:
        link = self._link(user_id=user_id, link_id=link_id)
        self._ticket(link=link, ticket_id=ticket_id)
        stmt = (
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.workspace_id == link.workspace_id,
                Conversation.ticket_id == ticket_id,
                Message.workspace_id == link.workspace_id,
            )
            .order_by(Message.created_at.asc())
        )
        return list(self.db.scalars(stmt))

    def add_message(
        self, *, user_id: str, link_id: str, ticket_id: str, body: str
    ) -> Message:
        link = self._link(user_id=user_id, link_id=link_id)
        ticket = self._ticket(link=link, ticket_id=ticket_id)
        conversation = self.db.scalar(
            select(Conversation)
            .where(
                Conversation.workspace_id == link.workspace_id,
                Conversation.ticket_id == ticket.id,
                Conversation.channel == ConversationChannel.WEB,
            )
            .order_by(Conversation.created_at.asc())
            .limit(1)
        )
        if conversation is None:
            conversation = Conversation(
                workspace_id=link.workspace_id,
                ticket_id=ticket.id,
                created_by_user_id=user_id,
                channel=ConversationChannel.WEB,
                subject=ticket.subject,
            )
            self.db.add(conversation)
            self.db.flush()
        message = Message(
            workspace_id=link.workspace_id,
            conversation_id=conversation.id,
            author_user_id=user_id,
            direction=MessageDirection.INBOUND,
            body=body,
        )
        self.db.add(message)
        self.db.flush()
        self.audit.record(
            action="portal.message.created",
            workspace_id=link.workspace_id,
            actor_user_id=user_id,
            resource_type="message",
            resource_id=message.id,
            metadata={"ticket_id": ticket.id},
        )
        self.db.commit()
        return message
