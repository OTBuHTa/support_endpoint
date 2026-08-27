from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.client import Client, ClientContact, ClientOrganization


class ClientOrganizationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self, *, workspace_id: str, name: str, domain: str = "", notes: str = ""
    ) -> ClientOrganization:
        org = ClientOrganization(workspace_id=workspace_id, name=name, domain=domain, notes=notes)
        self.db.add(org)
        self.db.flush()
        return org

    def get_in_workspace(self, *, workspace_id: str, org_id: str) -> ClientOrganization | None:
        stmt = select(ClientOrganization).where(
            ClientOrganization.id == org_id, ClientOrganization.workspace_id == workspace_id
        )
        return self.db.scalar(stmt)

    def list_in_workspace(
        self, *, workspace_id: str, q: str = "", limit: int = 20, offset: int = 0
    ) -> tuple[list[ClientOrganization], int]:
        base = select(ClientOrganization).where(ClientOrganization.workspace_id == workspace_id)
        if q:
            like = f"%{q.lower()}%"
            base = base.where(
                or_(
                    func.lower(ClientOrganization.name).like(like),
                    func.lower(ClientOrganization.domain).like(like),
                )
            )
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = list(
            self.db.scalars(base.order_by(ClientOrganization.name).limit(limit).offset(offset))
        )
        return items, total


class ClientRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        workspace_id: str,
        full_name: str,
        primary_email: str = "",
        primary_phone: str = "",
        organization_id: str | None = None,
        notes: str = "",
    ) -> Client:
        client = Client(
            workspace_id=workspace_id,
            full_name=full_name,
            primary_email=primary_email,
            primary_phone=primary_phone,
            organization_id=organization_id,
            notes=notes,
        )
        self.db.add(client)
        self.db.flush()
        return client

    def get_in_workspace(self, *, workspace_id: str, client_id: str) -> Client | None:
        """Object-level guard: a client id from another workspace never
        resolves here, even if the caller is authorized on *this*
        workspace_id — this is the IDOR/BOLA check at the resource
        level, distinct from (and in addition to) the membership check
        already performed by `require_permission` on the path's
        workspace_id.
        """
        stmt = select(Client).where(Client.id == client_id, Client.workspace_id == workspace_id)
        return self.db.scalar(stmt)

    def list_in_workspace(
        self,
        *,
        workspace_id: str,
        q: str = "",
        organization_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Client], int]:
        base = select(Client).where(Client.workspace_id == workspace_id)
        if organization_id:
            base = base.where(Client.organization_id == organization_id)
        if q:
            like = f"%{q.lower()}%"
            base = base.where(
                or_(
                    func.lower(Client.full_name).like(like),
                    func.lower(Client.primary_email).like(like),
                    func.lower(Client.primary_phone).like(like),
                )
            )
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = list(self.db.scalars(base.order_by(Client.full_name).limit(limit).offset(offset)))
        return items, total


class ClientContactRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self, *, workspace_id: str, client_id: str, label: str, channel_type: str, value: str
    ) -> ClientContact:
        contact = ClientContact(
            workspace_id=workspace_id,
            client_id=client_id,
            label=label,
            channel_type=channel_type,
            value=value,
        )
        self.db.add(contact)
        self.db.flush()
        return contact

    def list_for_client(self, *, workspace_id: str, client_id: str) -> list[ClientContact]:
        stmt = select(ClientContact).where(
            ClientContact.workspace_id == workspace_id, ClientContact.client_id == client_id
        )
        return list(self.db.scalars(stmt))

    def get_in_workspace(self, *, workspace_id: str, contact_id: str) -> ClientContact | None:
        stmt = select(ClientContact).where(
            ClientContact.id == contact_id, ClientContact.workspace_id == workspace_id
        )
        return self.db.scalar(stmt)

    def delete(self, contact: ClientContact) -> None:
        self.db.delete(contact)
        self.db.flush()
