import os
import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_relayai.db")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

from app.db.database import Base, get_db
from app.main import app


@pytest.fixture()
def session_factory() -> Iterator[async_sessionmaker]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def setup_database():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(setup_database())
    yield TestSessionLocal
    asyncio.run(engine.dispose())


@pytest.fixture()
def client(session_factory: async_sessionmaker) -> Iterator[TestClient]:
    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
