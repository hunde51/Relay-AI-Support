"""Seed a default organization so the app works without auth."""
import asyncio
from sqlalchemy import select
from app.db.database import SessionLocal
from app.db.models import OrganizationORM, OrganizationSettingsORM, NotificationSettingsORM

DEFAULT_ORG_ID = "ORG-DEFAULT000000"
DEFAULT_ORG_SLUG = "default"


async def seed():
    async with SessionLocal() as db:
        existing = await db.execute(select(OrganizationORM).where(OrganizationORM.id == DEFAULT_ORG_ID))
        if existing.scalar_one_or_none():
            print("Default org already exists — skipping seed.")
            return

        org = OrganizationORM(id=DEFAULT_ORG_ID, name="RelayAI Support", slug=DEFAULT_ORG_SLUG)
        db.add(org)
        await db.flush()  # persist org before FK-dependent rows
        db.add(OrganizationSettingsORM(organization_id=DEFAULT_ORG_ID))
        db.add(NotificationSettingsORM(organization_id=DEFAULT_ORG_ID))
        await db.commit()
        print(f"Seeded default org: {DEFAULT_ORG_ID}")


if __name__ == "__main__":
    asyncio.run(seed())
