import os
import asyncio
from typing import AsyncGenerator
import pytest
from httpx import AsyncClient, ASGITransport
import pytest_asyncio
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import get_session
from app.db.models import Base
from app.main import app

DATABASE_URL = os.getenv("TEST_DB_URL", "postgresql+asyncpg://root:root@test_db:5432/test_db")

engine_test = create_async_engine(DATABASE_URL, poolclass=NullPool)
async_session_maker = sessionmaker(bind=engine_test, class_=AsyncSession, expire_on_commit=False)

async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

app.dependency_overrides[get_session] = override_get_async_session

@pytest.fixture(scope="function", autouse=True)
async def prepare_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@pytest_asyncio.fixture(scope="session")
async def ac_public() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost:8000") as ac:
        yield ac

@pytest.fixture(scope="session")
def asyncio_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
