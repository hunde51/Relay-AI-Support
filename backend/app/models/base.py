from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, MappedColumn, mapped_column


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12].upper()}"


class TimestampMixin:
    created_at: MappedColumn[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: MappedColumn[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )
