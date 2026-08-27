from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.client import Client, ClientContact, ClientOrganization
from app.repositories.audit_repo import AuditRepository
from app.repositories.client_repo import (
    ClientContactRepository,
    ClientOrganizationRepository,
    ClientRepository,
)


class ClientOrganizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.orgs = ClientOrganizationRepository(db)
        self.audit = AuditRepository(db)

    def create(
        self, *, workspace_id: str, actor_user_id: str, name: str, domain: str = "", notes: str = ""
    ) -> ClientOrganization:
        org = self.orgs.create(workspace_id=workspace_id, name=name, domain=domain, notes=notes)
        self.audit.record(
            action="crm.organization.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="client_organization",
            resource_id=org.id,
        )
        self.db.commit()
        return org

    def get(self, *, workspace_id: str, org_id: str) -> ClientOrganization:
        org = self.orgs.get_in_workspace(workspace_id=workspace_id, org_id=org_id)
        if org is None:
            raise NotFoundError("Organization not found")
        return org

    def list_organizations(
        self, *, workspace_id: str, q: str = "", limit: int = 20, offset: int = 0
    ) -> tuple[list[ClientOrganization], int]:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        return self.orgs.list_in_workspace(
            workspace_id=workspace_id, q=q, limit=limit, offset=offset
        )

    def update(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        org_id: str,
        name: str | None = None,
        domain: str | None = None,
        notes: str | None = None,
        is_active: bool | None = None,
    ) -> ClientOrganization:
        org = self.get(workspace_id=workspace_id, org_id=org_id)
        if name is not None:
            org.name = name
        if domain is not None:
            org.domain = domain
        if notes is not None:
            org.notes = notes
        if is_active is not None:
            org.is_active = is_active
        self.db.add(org)
        self.audit.record(
            action="crm.organization.updated",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="client_organization",
            resource_id=org.id,
        )
        self.db.commit()
        return org


class ClientService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.clients = ClientRepository(db)
        self.orgs = ClientOrganizationRepository(db)
        self.contacts = ClientContactRepository(db)
        self.audit = AuditRepository(db)

    def _validate_organization(self, *, workspace_id: str, organization_id: str | None) -> None:
        if organization_id is None:
            return
        if self.orgs.get_in_workspace(workspace_id=workspace_id, org_id=organization_id) is None:
            raise ValidationAppError(
                "organization_id does not refer to an organization in this workspace"
            )

    def create(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        full_name: str,
        primary_email: str = "",
        primary_phone: str = "",
        organization_id: str | None = None,
        notes: str = "",
    ) -> Client:
        self._validate_organization(workspace_id=workspace_id, organization_id=organization_id)
        client = self.clients.create(
            workspace_id=workspace_id,
            full_name=full_name,
            primary_email=primary_email,
            primary_phone=primary_phone,
            organization_id=organization_id,
            notes=notes,
        )
        self.audit.record(
            action="crm.client.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="client",
            resource_id=client.id,
        )
        self.db.commit()
        return client

    def get(self, *, workspace_id: str, client_id: str) -> Client:
        client = self.clients.get_in_workspace(workspace_id=workspace_id, client_id=client_id)
        if client is None:
            raise NotFoundError("Client not found")
        return client

    def list_clients(
        self,
        *,
        workspace_id: str,
        q: str = "",
        organization_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Client], int]:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        return self.clients.list_in_workspace(
            workspace_id=workspace_id,
            q=q,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
        )

    def update(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        client_id: str,
        full_name: str | None = None,
        primary_email: str | None = None,
        primary_phone: str | None = None,
        organization_id: str | None = None,
        notes: str | None = None,
        is_active: bool | None = None,
    ) -> Client:
        client = self.get(workspace_id=workspace_id, client_id=client_id)
        if organization_id is not None:
            self._validate_organization(workspace_id=workspace_id, organization_id=organization_id)
            client.organization_id = organization_id
        if full_name is not None:
            client.full_name = full_name
        if primary_email is not None:
            client.primary_email = primary_email
        if primary_phone is not None:
            client.primary_phone = primary_phone
        if notes is not None:
            client.notes = notes
        if is_active is not None:
            client.is_active = is_active
        self.db.add(client)
        self.audit.record(
            action="crm.client.updated",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="client",
            resource_id=client.id,
        )
        self.db.commit()
        return client

    def add_contact(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        client_id: str,
        label: str,
        channel_type: str,
        value: str,
    ) -> ClientContact:
        self.get(workspace_id=workspace_id, client_id=client_id)  # 404s if not in this workspace
        contact = self.contacts.create(
            workspace_id=workspace_id,
            client_id=client_id,
            label=label,
            channel_type=channel_type,
            value=value,
        )
        self.audit.record(
            action="crm.client_contact.created",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="client_contact",
            resource_id=contact.id,
        )
        self.db.commit()
        return contact

    def list_contacts(self, *, workspace_id: str, client_id: str) -> list[ClientContact]:
        self.get(workspace_id=workspace_id, client_id=client_id)
        return self.contacts.list_for_client(workspace_id=workspace_id, client_id=client_id)

    def delete_contact(
        self, *, workspace_id: str, actor_user_id: str, client_id: str, contact_id: str
    ) -> None:
        contact = self.contacts.get_in_workspace(workspace_id=workspace_id, contact_id=contact_id)
        if contact is None or contact.client_id != client_id:
            raise NotFoundError("Contact not found")
        self.contacts.delete(contact)
        self.audit.record(
            action="crm.client_contact.deleted",
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type="client_contact",
            resource_id=contact_id,
        )
        self.db.commit()
