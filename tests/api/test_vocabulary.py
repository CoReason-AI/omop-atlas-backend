# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

# Phase 2: Vocabulary Engine Tests

from datetime import date
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.dependencies import get_db, get_redis
from omop_atlas_backend.main import app
from omop_atlas_backend.models.vocabulary import Concept


@pytest_asyncio.fixture
async def client(async_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Test client with dependency overrides.
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_session

    async def override_get_redis() -> AsyncGenerator[None, None]:
        # Return None (no Redis) for basic API tests
        yield None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_concept_api_found(client: AsyncClient, async_session: AsyncSession) -> None:
    # Seed DB
    c = Concept(
        concept_id=1,
        concept_name="API Test Concept",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Ingredient",
        concept_code="API1",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add(c)
    await async_session.commit()

    response = await client.get("/vocabulary/concept/1")
    assert response.status_code == 200
    data = response.json()
    assert data["conceptId"] == 1
    assert data["conceptName"] == "API Test Concept"


@pytest.mark.asyncio
async def test_get_concept_api_not_found(client: AsyncClient) -> None:
    response = await client.get("/vocabulary/concept/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_search_concepts_api(client: AsyncClient, async_session: AsyncSession) -> None:
    # Seed DB
    c1 = Concept(
        concept_id=10,
        concept_name="Search Match",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="S1",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    c2 = Concept(
        concept_id=11,
        concept_name="No Match",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="S2",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add_all([c1, c2])
    await async_session.commit()

    # Search Payload (using uppercase keys as per schema)
    payload = {"QUERY": "Search"}
    response = await client.post("/vocabulary/search", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["conceptName"] == "Search Match"


@pytest.mark.asyncio
async def test_search_concepts_pagination_api(client: AsyncClient, async_session: AsyncSession) -> None:
    # Seed DB
    for i in range(5):
        async_session.add(
            Concept(
                concept_id=20 + i,
                concept_name=f"Page {i}",
                domain_id="M",
                vocabulary_id="V",
                concept_class_id="C",
                concept_code=f"P{i}",
                valid_start_date=date(2020, 1, 1),
                valid_end_date=date(2099, 12, 31),
            )
        )
    await async_session.commit()

    payload = {"QUERY": "Page"}
    # Limit 2, Offset 2 => Should get Page 2, Page 3
    response = await client.post("/vocabulary/search?limit=2&offset=2", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["conceptName"] == "Page 2"
    assert data[1]["conceptName"] == "Page 3"
