from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.session import RefreshSession


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        user_agent: str = "",
        ip_address: str = "",
    ) -> RefreshSession:
        session = RefreshSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(session)
        self.db.flush()
        return session

    def get_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        stmt = select(RefreshSession).where(RefreshSession.token_hash == token_hash)
        return self.db.scalar(stmt)

    def revoke(self, session: RefreshSession) -> None:
        session.revoked_at = utcnow()
        self.db.add(session)
        self.db.flush()
