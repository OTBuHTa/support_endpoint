from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class AuditEvent(TimestampMixin, Base):
    """Immutable-style audit trail for security/business-sensitive
    actions. Kept distinct from ordinary application logs. Rows are
    append-only at the application-service level (no update/delete
    service methods are provided in Foundation).
    """

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
