import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.background.celery_app import celery_app
from app.db.database import SessionLocal
from app.db.models import AIRunORM, EmailIntegrationORM, KnowledgeDocumentORM, KnowledgeIngestionJobORM, KnowledgeSourceORM, UsageRecordORM, UsageEventORM
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


async def _poll_all_gmail_async() -> dict:
    async with SessionLocal() as db:
        result = await db.execute(
            select(EmailIntegrationORM).where(
                EmailIntegrationORM.provider == "gmail",
                EmailIntegrationORM.is_active == True,
            )
        )
        integrations = result.scalars().all()
        from app.services.email_service import poll_gmail
        total = 0
        for integration in integrations:
            try:
                cnt = await poll_gmail(db, integration)
                total += cnt
            except Exception as exc:
                integration.last_error = str(exc)
                await db.commit()
        return {"polled": len(integrations), "new_messages": total}


async def _poll_all_outlook_async() -> dict:
    async with SessionLocal() as db:
        result = await db.execute(
            select(EmailIntegrationORM).where(
                EmailIntegrationORM.provider == "outlook",
                EmailIntegrationORM.is_active == True,
            )
        )
        integrations = result.scalars().all()
        from app.services.email_service import poll_outlook
        total = 0
        for integration in integrations:
            try:
                cnt = await poll_outlook(db, integration)
                total += cnt
            except Exception as exc:
                integration.last_error = str(exc)
                await db.commit()
        return {"polled": len(integrations), "new_messages": total}


@celery_app.task(
    name="app.background.tasks.poll_gmail",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=2,
)
def poll_gmail_task(self):
    return asyncio.run(_poll_all_gmail_async())


@celery_app.task(
    name="app.background.tasks.poll_outlook",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=2,
)
def poll_outlook_task(self):
    return asyncio.run(_poll_all_outlook_async())


@celery_app.task(
    name="app.background.tasks.archive_old_usage_records",
)
def archive_old_usage_records():
    """Delete usage records and events older than 24 months to control DB size."""
    import asyncio
    from datetime import timedelta
    from sqlalchemy import delete

    async def _run():
        async with SessionLocal() as db:
            cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=730)
            cutoff_period = f"{cutoff.year}-{cutoff.month:02d}"

            result = await db.execute(
                delete(UsageRecordORM).where(UsageRecordORM.period < cutoff_period)
            )
            deleted_records = result.rowcount

            result2 = await db.execute(
                delete(UsageEventORM).where(UsageEventORM.created_at < cutoff)
            )
            deleted_events = result2.rowcount

            await db.commit()
            return {"archived_records": deleted_records, "archived_events": deleted_events}

    return asyncio.run(_run())
