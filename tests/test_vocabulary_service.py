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
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import Concept
from omop_atlas_backend.schemas.concept import ConceptSearch
from omop_atlas_backend.services.vocabulary import VocabularyService


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=None)
    return redis


@pytest.fixture
def service(async_session: AsyncSession, mock_redis):
    return VocabularyService(async_session, mock_redis)


@pytest.mark.asyncio
async def test_get_concept_not_found(service: VocabularyService):
    concept = await service.get_concept(999)
    assert concept is None


@pytest.mark.asyncio
async def test_get_concept_found_db(service: VocabularyService, async_session: AsyncSession):
    # Seed DB
    db_concept = Concept(
        concept_id=1,
        concept_name="Test Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="12345",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        standard_concept="S",
        invalid_reason=None,
    )
    async_session.add(db_concept)
    await async_session.commit()

    concept = await service.get_concept(1)
    assert concept is not None
    assert concept.concept_id == 1
    assert concept.concept_name == "Test Concept"

    # Verify Redis cache set was called
    service.redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_get_concept_found_cache(service: VocabularyService):
    # Setup cache hit - JSON structure matches Pydantic alias input (camelCase)
    cached_concept_json = (
        '{"conceptId": 2, "conceptName": "Cached Concept", "conceptCode": "54321", '
        '"domainId": "Drug", "vocabularyId": "RxNorm", "conceptClassId": "Ingredient", '
        '"validStartDate": "2020-01-01", "validEndDate": "2099-12-31"}'
    )
    service.redis.get = AsyncMock(return_value=cached_concept_json)

    concept = await service.get_concept(2)
    assert concept is not None
    assert concept.concept_id == 2
    assert concept.concept_name == "Cached Concept"

    # Verify DB was NOT queried (implicit since we didn't seed DB and mocked Redis hit)


@pytest.mark.asyncio
async def test_search_concepts_pagination(service: VocabularyService, async_session: AsyncSession):
    # Seed DB with multiple concepts
    for i in range(10):
        async_session.add(
            Concept(
                concept_id=i + 100,
                concept_name=f"Concept {i}",
                domain_id="Measurement",
                vocabulary_id="LOINC",
                concept_class_id="Lab Test",
                concept_code=f"C{i}",
                valid_start_date=date(2020, 1, 1),
                valid_end_date=date(2099, 12, 31),
            )
        )
    await async_session.commit()

    search = ConceptSearch(QUERY="Concept")

    # Test limit
    results = await service.search_concepts(search, limit=5, offset=0)
    assert len(results) == 5
    assert results[0].concept_name == "Concept 0"

    # Test offset
    results = await service.search_concepts(search, limit=5, offset=5)
    assert len(results) == 5
    assert results[0].concept_name == "Concept 5"


@pytest.mark.asyncio
async def test_search_concepts_filters(service: VocabularyService, async_session: AsyncSession):
    # Seed DB
    c1 = Concept(
        concept_id=200,
        concept_name="Aspirin",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Ingredient",
        concept_code="A1",
        valid_start_date=date.today(),
        valid_end_date=date.today(),
    )
    c2 = Concept(
        concept_id=201,
        concept_name="Headache",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="H1",
        valid_start_date=date.today(),
        valid_end_date=date.today(),
    )
    async_session.add_all([c1, c2])
    await async_session.commit()

    # Test Domain Filter
    search = ConceptSearch(DOMAIN_ID=["Drug"])
    results = await service.search_concepts(search)
    assert len(results) == 1
    assert results[0].concept_id == 200

    # Test Vocabulary Filter
    search = ConceptSearch(VOCABULARY_ID=["SNOMED"])
    results = await service.search_concepts(search)
    assert len(results) == 1
    assert results[0].concept_id == 201
