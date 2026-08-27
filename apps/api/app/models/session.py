from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class RefreshSession(TimestampMixin, Base):
    """An opaque, rotating refresh session. The raw token is never
    stored — only its SHA-256 hash. Revocation sets revoked_at and
    must be checked on every refresh.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    @property
    def is_active(self) -> bool:

        from app.db.base import utcnow

        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            # SQLite (used in tests) does not persist tzinfo on DateTime
            # columns the way Postgres does; treat naive values as UTC.
            expires_at = expires_at.replace(tzinfo=UTC)
        return self.revoked_at is None and expires_at > utcnow()
