from datetime import datetime

from sqlalchemy import ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, make_id


class KnowledgeSourceORM(TimestampMixin, Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("SRC"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)

    documents: Mapped[list["KnowledgeDocumentORM"]] = relationship(back_populates="source")

    __table_args__ = (Index("ix_knowledge_sources_organization_id", "organization_id"),)


class KnowledgeDocumentORM(TimestampMixin, Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("DOC"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sources.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String)
    checksum: Mapped[str | None] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)

    source: Mapped["KnowledgeSourceORM"] = relationship(back_populates="documents")
    chunks: Mapped[list["KnowledgeChunkORM"]] = relationship(back_populates="document")

    __table_args__ = (Index("ix_knowledge_documents_organization_id", "organization_id"),)


class KnowledgeChunkORM(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("CHK"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), nullable=False)
    chunk_index: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    token_count: Mapped[str | None] = mapped_column(String)
    embedding_id: Mapped[str | None] = mapped_column(String)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(String, nullable=False)

    document: Mapped["KnowledgeDocumentORM"] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunks_document_index"),
        Index("ix_knowledge_chunks_organization_id", "organization_id"),
    )


class KnowledgeIngestionJobORM(TimestampMixin, Base):
    __tablename__ = "knowledge_ingestion_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("ING"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="queued", nullable=False)
    error: Mapped[str | None] = mapped_column(String)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
