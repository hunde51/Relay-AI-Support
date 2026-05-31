from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import hashlib

from app.db.database import get_db
from app.db.models import (
    KnowledgeSourceORM, KnowledgeDocumentORM,
    KnowledgeChunkORM, KnowledgeIngestionJobORM,
)
from app.db.seed import DEFAULT_ORG_ID
from app.services import rag_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 4


# ── Sources ──────────────────────────────────────────────────────────────────

@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(KnowledgeSourceORM)
        .where(KnowledgeSourceORM.organization_id == DEFAULT_ORG_ID)
        .order_by(KnowledgeSourceORM.created_at.desc())
    )
    sources = result.scalars().all()
    return [
        {
            "id": s.id, "name": s.name, "source_type": s.source_type,
            "status": s.status, "created_at": s.created_at,
        }
        for s in sources
    ]


@router.post("/sources", status_code=201)
async def create_source(
    name: str, source_type: str = "manual_upload",
    db: AsyncSession = Depends(get_db),
):
    s = KnowledgeSourceORM(
        organization_id=DEFAULT_ORG_ID, name=name, source_type=source_type
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return {"id": s.id, "name": s.name, "source_type": s.source_type, "status": s.status}


# ── Documents ─────────────────────────────────────────────────────────────────

@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(KnowledgeDocumentORM)
        .where(KnowledgeDocumentORM.organization_id == DEFAULT_ORG_ID)
        .order_by(KnowledgeDocumentORM.created_at.desc())
    )
    docs = result.scalars().all()
    return [_fmt_doc(d) for d in docs]


@router.post("/documents/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    source_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    checksum = hashlib.sha256(content).hexdigest()

    # Reuse existing source or create a default one
    if not source_id:
        src = KnowledgeSourceORM(
            organization_id=DEFAULT_ORG_ID,
            name="Uploads",
            source_type="manual_upload",
        )
        db.add(src)
        await db.flush()
        source_id = src.id

    doc = KnowledgeDocumentORM(
        organization_id=DEFAULT_ORG_ID,
        source_id=source_id,
        title=file.filename or "Untitled",
        content_type=file.content_type or "text/plain",
        checksum=checksum,
        status="pending",
    )
    db.add(doc)
    await db.flush()

    # Store raw text for ingestion
    doc.storage_path = f"uploads/{doc.id}.txt"
    import os
    os.makedirs("uploads", exist_ok=True)
    with open(doc.storage_path, "wb") as f:
        f.write(content)

    await db.commit()
    await db.refresh(doc)
    return _fmt_doc(doc)


@router.get("/documents/{document_id}")
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    doc = await _get_doc_or_404(db, document_id)
    return _fmt_doc(doc)


@router.post("/documents/{document_id}/ingest")
async def ingest_document(document_id: str, db: AsyncSession = Depends(get_db)):
    doc = await _get_doc_or_404(db, document_id)

    job = KnowledgeIngestionJobORM(
        organization_id=DEFAULT_ORG_ID,
        document_id=document_id,
        status="running",
    )
    db.add(job)
    doc.status = "ingesting"
    await db.flush()

    try:
        result = await rag_service.ingest_document_file(doc.storage_path, doc.title, doc.id)
        doc.status = "ingested"
        job.status = "completed"
        job.metadata_json = result
    except Exception as e:
        doc.status = "failed"
        job.status = "failed"
        job.error = str(e)

    await db.commit()
    return {"document_id": document_id, "status": doc.status, "job_id": job.id}


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    doc = await _get_doc_or_404(db, document_id)
    await db.delete(doc)
    await db.commit()


# ── Search ────────────────────────────────────────────────────────────────────

@router.post("/search")
async def search_knowledge(body: SearchRequest):
    results = await rag_service.search_knowledge(body.query, body.top_k)
    return {"query": body.query, "results": results}


# ── Legacy ingest (sample docs) ───────────────────────────────────────────────

@router.post("/ingest-docs")
async def ingest_sample_docs():
    return await rag_service.ingest_documents()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_doc_or_404(db: AsyncSession, document_id: str) -> KnowledgeDocumentORM:
    result = await db.execute(
        select(KnowledgeDocumentORM).where(KnowledgeDocumentORM.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _fmt_doc(d: KnowledgeDocumentORM) -> dict:
    return {
        "id": d.id, "title": d.title, "content_type": d.content_type,
        "status": d.status, "checksum": d.checksum,
        "source_id": d.source_id, "organization_id": d.organization_id,
        "created_at": d.created_at, "updated_at": d.updated_at,
    }
