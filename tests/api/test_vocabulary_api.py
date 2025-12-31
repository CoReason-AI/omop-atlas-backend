# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from __future__ import annotations

from datetime import date
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.dependencies import get_db, get_redis
from omop_atlas_backend.main import app
from omop_atlas_backend.models.vocabulary import Concept


# Override dependencies for testing
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    mock_session = AsyncMock(spec=AsyncSession)
    # We will configure the mock per test
    yield mock_session


async def override_get_redis() -> AsyncGenerator["Redis[str]", None]:
    mock_redis = AsyncMock()
    yield mock_redis


# Set dependency overrides
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_redis] = override_get_redis


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_redis() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def test_app(mock_session: AsyncMock, mock_redis: AsyncMock) -> FastAPI:
    # Update overrides with specific mocks
    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        yield mock_session

    async def _get_redis() -> AsyncGenerator["Redis[str]", None]:
        yield mock_redis

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_redis] = _get_redis
    return app  # type: ignore[no-any-return]


@pytest.mark.asyncio
async def test_search_concepts_endpoint(test_app: FastAPI, mock_session: AsyncMock) -> None:
    """Test POST /vocabulary/search"""
    mock_result = MagicMock()
    mock_concept = Concept(
        concept_id=1,
        concept_name="Aspirin",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Ingredient",
        standard_concept="S",
        concept_code="111",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )
    mock_result.scalars.return_value.all.return_value = [mock_concept]
    mock_session.execute.return_value = mock_result

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        payload = {"QUERY": "aspirin"}
        response = await ac.post("/vocabulary/search", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["conceptId"] == 1
    assert data[0]["conceptName"] == "Aspirin"


@pytest.mark.asyncio
async def test_get_concept_endpoint(test_app: FastAPI, mock_session: AsyncMock, mock_redis: AsyncMock) -> None:
    """Test GET /vocabulary/concept/{id} with cache miss"""
    mock_redis.get.return_value = None

    mock_concept = Concept(
        concept_id=100,
        concept_name="Test",
        domain_id="Type",
        vocabulary_id="Vocab",
        concept_class_id="Class",
        standard_concept="S",
        concept_code="C100",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_concept
    mock_session.execute.return_value = mock_result

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        response = await ac.get("/vocabulary/concept/100")

    assert response.status_code == 200
    assert response.json()["conceptId"] == 100
    assert mock_redis.set.called


@pytest.mark.asyncio
async def test_get_concept_not_found(test_app: FastAPI, mock_session: AsyncMock, mock_redis: AsyncMock) -> None:
    """Test GET /vocabulary/concept/{id} 404"""
    mock_redis.get.return_value = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        response = await ac.get("/vocabulary/concept/999")

    assert response.status_code == 404
