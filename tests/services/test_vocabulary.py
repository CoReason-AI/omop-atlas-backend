# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import Concept
from omop_atlas_backend.schemas.concept import ConceptSearch
from omop_atlas_backend.services.vocabulary import VocabularyService


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    return redis


@pytest.mark.asyncio
async def test_get_concept_found_db(async_session: AsyncSession, mock_redis: AsyncMock) -> None:
    """Test retrieving a concept from DB when cache is empty."""
    # Setup data
    concept = Concept(
        concept_id=1,
        concept_name="Test Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="C1",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add(concept)
    await async_session.commit()

    service = VocabularyService(async_session, mock_redis)
    result = await service.get_concept(1)

    assert result is not None
    assert result.concept_id == 1
    assert result.concept_name == "Test Concept"

    # Verify Redis interaction
    mock_redis.get.assert_awaited_once_with("concept:1")
    # Verify set called once
    assert mock_redis.set.call_count == 1


@pytest.mark.asyncio
async def test_get_concept_found_cache(async_session: AsyncSession, mock_redis: AsyncMock) -> None:
    """Test retrieving a concept from Redis cache."""
    # Setup cache return
    cached_data = {
        "concept_id": 2,
        "concept_name": "Cached Concept",
        "domain_id": "Drug",
        "vocabulary_id": "RxNorm",
        "concept_class_id": "Ingredient",
        "standard_concept": "S",
        "concept_code": "C2",
        "valid_start_date": "2020-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    service = VocabularyService(async_session, mock_redis)
    result = await service.get_concept(2)

    assert result is not None
    assert result.concept_id == 2
    assert result.concept_name == "Cached Concept"

    # Verify DB was NOT queried (implied by no data setup in DB)
    mock_redis.get.assert_awaited_once_with("concept:2")


@pytest.mark.asyncio
async def test_get_concept_not_found(async_session: AsyncSession, mock_redis: AsyncMock) -> None:
    """Test retrieving a non-existent concept."""
    service = VocabularyService(async_session, mock_redis)
    result = await service.get_concept(999)

    assert result is None
    mock_redis.get.assert_awaited_once_with("concept:999")
    mock_redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_concepts_by_name(async_session: AsyncSession) -> None:
    """Test searching concepts by name."""
    c1 = Concept(
        concept_id=10,
        concept_name="Aspirin 100mg",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Clinical Drug",
        standard_concept="S",
        concept_code="D1",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    c2 = Concept(
        concept_id=11,
        concept_name="Tylenol",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Branded Drug",
        standard_concept="S",
        concept_code="D2",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add_all([c1, c2])
    await async_session.commit()

    service = VocabularyService(async_session)
    search = ConceptSearch(QUERY="Aspirin")
    results = await service.search_concepts(search)

    assert len(results) == 1
    assert results[0].concept_id == 10
    assert results[0].concept_name == "Aspirin 100mg"


@pytest.mark.asyncio
async def test_search_concepts_filters(async_session: AsyncSession) -> None:
    """Test searching with multiple filters."""
    c1 = Concept(
        concept_id=20,
        concept_name="Heart Failure",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="C20",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    c2 = Concept(
        concept_id=21,
        concept_name="Heart Transplant",
        domain_id="Procedure",
        vocabulary_id="SNOMED",
        concept_class_id="Procedure",
        standard_concept="S",
        concept_code="C21",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    c3 = Concept(
        concept_id=22,
        concept_name="Invalid Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="C22",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason="D",
    )
    async_session.add_all([c1, c2, c3])
    await async_session.commit()

    service = VocabularyService(async_session)

    # Filter by Domain
    search = ConceptSearch(QUERY="Heart", DOMAIN_ID=["Condition"])
    results = await service.search_concepts(search)
    assert len(results) == 1
    assert results[0].domain_id == "Condition"

    # Filter by Vocabulary
    search = ConceptSearch(QUERY="Heart", VOCABULARY_ID=["SNOMED"])
    results = await service.search_concepts(search)
    assert len(results) == 2

    # Filter by Concept Class
    search = ConceptSearch(CONCEPT_CLASS_ID=["Procedure"])
    results = await service.search_concepts(search)
    assert len(results) == 1
    assert results[0].concept_id == 21

    # Filter by Standard Concept
    search = ConceptSearch(STANDARD_CONCEPT="S")
    results = await service.search_concepts(search)
    assert len(results) == 3

    # Filter by Invalid Reason
    search = ConceptSearch(INVALID_REASON="D")
    results = await service.search_concepts(search)
    assert len(results) == 1
    assert results[0].concept_id == 22


@pytest.mark.asyncio
async def test_search_concepts_pagination(async_session: AsyncSession) -> None:
    """Test result limiting."""
    concepts = [
        Concept(
            concept_id=i,
            concept_name=f"Concept {i}",
            domain_id="Meas",
            vocabulary_id="Test",
            concept_class_id="Class",
            standard_concept="S",
            concept_code=f"C{i}",
            valid_start_date=date(2020, 1, 1),
            valid_end_date=date(2099, 12, 31),
        )
        for i in range(100, 110)
    ]
    async_session.add_all(concepts)
    await async_session.commit()

    service = VocabularyService(async_session)
    search = ConceptSearch(QUERY="Concept")

    # Limit to 5
    results = await service.search_concepts(search, limit=5)
    assert len(results) == 5
