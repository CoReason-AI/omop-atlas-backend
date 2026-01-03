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

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.dependencies import get_db, get_redis
from omop_atlas_backend.main import app
from omop_atlas_backend.models.security import User
from omop_atlas_backend.models.vocabulary import Concept, ConceptClass, Domain, Vocabulary


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


@pytest_asyncio.fixture
async def seed_data(async_session: AsyncSession) -> None:
    # 1. Create dependencies
    vocab = Vocabulary(
        vocabulary_id="RxNorm", vocabulary_name="RxNorm", vocabulary_concept_id=1
    )
    domain = Domain(domain_id="Drug", domain_name="Drug", domain_concept_id=1)
    c_class = ConceptClass(
        concept_class_id="Ingredient",
        concept_class_name="Ingredient",
        concept_class_concept_id=1,
    )

    async_session.add_all([vocab, domain, c_class])
    await async_session.flush()

    # 2. Create Concept
    concept = Concept(
        concept_id=1001,
        concept_name="Aspirin",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Ingredient",
        standard_concept="S",
        concept_code="1001",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )
    async_session.add(concept)

    # 3. Create User
    user = User(username="testuser", email="test@example.com", password_hash="hash", id=1)
    async_session.add(user)

    await async_session.commit()


@pytest.mark.asyncio
async def test_create_concept_set(client: AsyncClient, seed_data: None) -> None:
    payload = {
        "name": "Test Set",
        "items": [
            {
                "conceptId": 1001,
                "isExcluded": False,
                "includeDescendants": True,
                "includeMapped": False,
            }
        ],
    }
    response = await client.post("/conceptset/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Set"
    assert len(data["items"]) == 1
    assert data["items"][0]["conceptId"] == 1001
    assert data["items"][0]["concept"]["conceptName"] == "Aspirin"


@pytest.mark.asyncio
async def test_create_concept_set_invalid_concept(
    client: AsyncClient, seed_data: None
) -> None:
    payload = {
        "name": "Invalid Set",
        "items": [{"conceptId": 9999}],
    }
    response = await client.post("/conceptset/", json=payload)
    assert response.status_code == 400
    assert "Concept not found: 9999" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_concept_set(client: AsyncClient, seed_data: None) -> None:
    # Create first
    payload = {"name": "To Get", "items": [{"conceptId": 1001}]}
    create_res = await client.post("/conceptset/", json=payload)
    cs_id = create_res.json()["id"]

    # Get
    response = await client.get(f"/conceptset/{cs_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cs_id
    assert data["name"] == "To Get"


@pytest.mark.asyncio
async def test_get_concept_set_not_found(client: AsyncClient) -> None:
    response = await client.get("/conceptset/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_concept_set(client: AsyncClient, seed_data: None) -> None:
    # Create
    payload = {"name": "Original", "items": [{"conceptId": 1001}]}
    create_res = await client.post("/conceptset/", json=payload)
    cs_id = create_res.json()["id"]

    # Update
    update_payload = {"name": "Updated", "items": []}
    response = await client.put(f"/conceptset/{cs_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_update_concept_set_invalid_concept(
    client: AsyncClient, seed_data: None
) -> None:
    # Create
    payload = {"name": "Original", "items": [{"conceptId": 1001}]}
    create_res = await client.post("/conceptset/", json=payload)
    cs_id = create_res.json()["id"]

    # Update with invalid concept
    update_payload = {"items": [{"conceptId": 9999}]}
    response = await client.put(f"/conceptset/{cs_id}", json=update_payload)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_concept_set_not_found(client: AsyncClient) -> None:
    response = await client.put("/conceptset/9999", json={"name": "New"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_concept_set(client: AsyncClient, seed_data: None) -> None:
    # Create
    payload = {"name": "To Delete", "items": []}
    create_res = await client.post("/conceptset/", json=payload)
    cs_id = create_res.json()["id"]

    # Delete
    response = await client.delete(f"/conceptset/{cs_id}")
    assert response.status_code == 204

    # Verify deleted
    response = await client.get(f"/conceptset/{cs_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_concept_set_not_found(client: AsyncClient) -> None:
    response = await client.delete("/conceptset/9999")
    assert response.status_code == 404
