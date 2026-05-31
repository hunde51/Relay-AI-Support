from sqlalchemy import Column, String, DateTime
from datetime import UTC, datetime
from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TicketORM(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    status = Column(String, default="open")
    priority = Column(String, default="medium")
    category = Column(String, default="general")
    created_at = Column(DateTime, default=utc_now)
