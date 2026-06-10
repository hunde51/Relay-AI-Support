from sqlalchemy import ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, make_id


class CustomerORM(TimestampMixin, Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("CUS"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String)
    company: Mapped[str | None] = mapped_column(String)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)

    organization: Mapped["OrganizationORM"] = relationship(back_populates="customers")
    tickets: Mapped[list["TicketORM"]] = relationship(back_populates="customer")

    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_customers_organization_email"),
        Index("ix_customers_organization_id", "organization_id"),
    )


from app.models.org import OrganizationORM  # noqa: E402
from app.models.ticket import TicketORM  # noqa: E402
