# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

import os
from typing import AsyncGenerator, Optional

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Default to in-memory for dev/test if not specified, or use a proper env var.
# AGENTS.md mentions: Expect Postgres credentials in PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE.
# For now I will construct a URL or just use a placeholder string that assumes env vars are set.
# But for the app to actually run or for my tests to mock it, I need structure.

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_redis() -> AsyncGenerator[Optional[Redis], None]:
    # Return None if REDIS_URL is not set or valid, or just return the client.
    # The service handles Optional[Redis].
    client: Optional[Redis] = None
    try:
        client = Redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        # If redis is not available, yield None
        yield None
        return

    # If client creation succeeded, yield it and ensure cleanup
    try:
        yield client
    finally:
        await client.aclose()
