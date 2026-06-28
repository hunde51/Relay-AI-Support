import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.background.celery_app import celery_app
from app.db.database import SessionLocal
from app.db.models import AIRunORM, KnowledgeDocumentORM, KnowledgeIngestionJobORM, KnowledgeSourceORM
from app.services.ai_service import process_ai_run
from app.services import rag_service


async def _process_ai_run_async(ai_run_id: str) -> dict:
    async with SessionLocal() as db:
        run = await db.execute(select(AIRunORM).where(AIRunORM.id == ai_run_id))
        ai_run = run.scalar_one_or_none()
        if ai_run and ai_run.status == "failed":
            ai_run.status = "running"
            ai_run.error = None
            ai_run.completed_at = None
            ai_run.started_at = datetime.now(UTC).replace(tzinfo=None)
            await db.commit()
        return await process_ai_run(db, ai_run_id)


async def _process_document_ingestion_async(job_id: str) -> dict:
    async with SessionLocal() as db:
        job_result = await db.execute(select(KnowledgeIngestionJobORM).where(KnowledgeIngestionJobORM.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            return {"error": "Ingestion job not found"}

        doc_result = await db.execute(select(KnowledgeDocumentORM).where(KnowledgeDocumentORM.id == job.document_id))
        doc = doc_result.scalar_one_or_none()
        if not doc:
            job.status = "failed"
            job.error = "Document not found"
            job.started_at = datetime.now(UTC).replace(tzinfo=None)
            job.completed_at = datetime.now(UTC).replace(tzinfo=None)
            await db.commit()
            return {"error": "Document not found"}

        source_name = ""
        if doc.source_id:
            src_result = await db.execute(select(KnowledgeSourceORM).where(KnowledgeSourceORM.id == doc.source_id))
            source = src_result.scalar_one_or_none()
            source_name = source.name if source else ""

        now = datetime.now(UTC).replace(tzinfo=None)
        try:
            job.status = "running"
            job.started_at = now
            doc.status = "ingesting"
            await db.commit()

            result = await rag_service.ingest_document_file(
                db,
                doc.storage_path,
                doc.title,
                doc.id,
                doc.organization_id,
                source_name,
            )

            doc.status = "ingested"
            job.status = "completed"
            job.completed_at = datetime.now(UTC).replace(tzinfo=None)
            job.chunks_created = result.get("ingested", 0)
            job.metadata_json = result
            await db.commit()
            return {"status": "completed", "job_id": job.id, "result": result}
        except Exception as exc:
            doc.status = "failed"
            job.status = "failed"
            job.error = str(exc)
            job.completed_at = datetime.now(UTC).replace(tzinfo=None)
            await db.commit()
            return {"status": "failed", "job_id": job.id, "error": str(exc)}


@celery_app.task(
    name="app.background.tasks.deliver_webhook_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def deliver_webhook_task(self, delivery_id: str):
    async def _run():
        from app.services.webhook_service import deliver_webhook
        async with SessionLocal() as db:
            return await deliver_webhook(db, delivery_id)
    return asyncio.run(_run())


@celery_app.task(
    name="app.background.tasks.process_ai_run_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def process_ai_run_task(self, ai_run_id: str):
    return asyncio.run(_process_ai_run_async(ai_run_id))


@celery_app.task(
    name="app.background.tasks.process_document_ingestion_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def process_document_ingestion_task(self, job_id: str):
    return asyncio.run(_process_document_ingestion_async(job_id))
