import json

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        action: str,
        workspace_id: str | None = None,
        actor_user_id: str | None = None,
        resource_type: str = "",
        resource_id: str = "",
        correlation_id: str = "",
        result: str = "success",
        metadata: dict | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            action=action,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            correlation_id=correlation_id,
            result=result,
            metadata_json=json.dumps(metadata or {}),
        )
        self.db.add(event)
        self.db.flush()
        return event
