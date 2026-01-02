# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from datetime import date
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.dependencies import get_db, get_redis, get_vocabulary_service
from omop_atlas_backend.main import app
from omop_atlas_backend.models.vocabulary import Concept, ConceptClass, Domain, Vocabulary
from omop_atlas_backend.services.exceptions import ConceptNotFound
from omop_atlas_backend.services.vocabulary import VocabularyService


@pytest_asyncio.fixture
async def seed_data(async_session: AsyncSession) -> Concept:
    # 1. Create dependencies
    vocab = Vocabulary(vocabulary_id="SNOMED", vocabulary_name="SNOMED", vocabulary_concept_id=0)
    domain = Domain(domain_id="Condition", domain_name="Condition", domain_concept_id=0)
    c_class = ConceptClass(
        concept_class_id="Clinical Finding", concept_class_name="Clinical Finding", concept_class_concept_id=0
    )

    async_session.add_all([vocab, domain, c_class])
    await async_session.commit()

    # 2. Create Concept
    concept = Concept(
        concept_id=1,
        concept_name="Test Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="123",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )
    async_session.add(concept)
    await async_session.commit()
    return concept


@pytest_asyncio.fixture
async def client(async_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    # Override get_db dependency
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_session

    # Override get_redis to return None (no redis in tests)
    async def override_get_redis() -> AsyncGenerator[None, None]:
        yield None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_concept_by_id(client: AsyncClient, seed_data: Concept) -> None:
    response = await client.get("/vocabulary/concept/1")
    assert response.status_code == 200
    data = response.json()
    assert data["conceptId"] == 1
    assert data["conceptName"] == "Test Concept"


@pytest.mark.asyncio
async def test_get_concept_by_id_not_found(client: AsyncClient) -> None:
    # Use explicit mock to ensure we hit the exception path and coverage detects it
    mock_service = AsyncMock(spec=VocabularyService)
    mock_service.get_concept_by_id.side_effect = ConceptNotFound(999)

    app.dependency_overrides[get_vocabulary_service] = lambda: mock_service

    try:
        response = await client.get("/vocabulary/concept/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Concept with ID 999 not found."
    finally:
        # Cleanup override
        del app.dependency_overrides[get_vocabulary_service]


@pytest.mark.asyncio
async def test_search_concepts_post(client: AsyncClient, seed_data: Concept) -> None:
    # Search using POST (existing endpoint)
    payload = {"QUERY": "Test", "DOMAIN_ID": ["Condition"], "VOCABULARY_ID": ["SNOMED"]}
    response = await client.post("/vocabulary/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["conceptId"] == 1


@pytest.mark.asyncio
async def test_search_concepts_get(client: AsyncClient, seed_data: Concept) -> None:
    # Search using GET
    params = {
        "QUERY": "Test",
        "DOMAIN_ID": "Condition",
    }
    response = await client.get("/vocabulary/search", params=params)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["conceptId"] == 1
