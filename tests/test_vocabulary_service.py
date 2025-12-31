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
from unittest.mock import AsyncMock

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import Concept
from omop_atlas_backend.schemas.concept import ConceptSearch
from omop_atlas_backend.services.vocabulary import VocabularyService


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock(spec=Redis)
    # mock get and set methods
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=None)
    return redis


@pytest.fixture
def service(async_session: AsyncSession, mock_redis: AsyncMock) -> VocabularyService:
    # We cast mock_redis to Optional["Redis[str]"] effectively by passing it,
    # but mypy might complain if strict.
    # Ideally VocabularyService accepts an object that satisfies the Redis interface.
    return VocabularyService(async_session, mock_redis)


@pytest.mark.asyncio
async def test_get_concept_not_found(service: VocabularyService) -> None:
    concept = await service.get_concept(999)
    assert concept is None


@pytest.mark.asyncio
async def test_get_concept_found_db(service: VocabularyService, async_session: AsyncSession) -> None:
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
    assert service.redis is not None
    # We need to cast or ignore type for 'set' on the mock object
    service.redis.set.assert_called_once()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_get_concept_found_cache(service: VocabularyService) -> None:
    # Setup cache hit - JSON structure matches Pydantic alias input (camelCase)
    cached_concept_json = (
        '{"conceptId": 2, "conceptName": "Cached Concept", "conceptCode": "54321", '
        '"domainId": "Drug", "vocabularyId": "RxNorm", "conceptClassId": "Ingredient", '
        '"validStartDate": "2020-01-01", "validEndDate": "2099-12-31"}'
    )

    assert service.redis is not None
    service.redis.get = AsyncMock(return_value=cached_concept_json)  # type: ignore[method-assign]

    concept = await service.get_concept(2)
    assert concept is not None
    assert concept.concept_id == 2
    assert concept.concept_name == "Cached Concept"

    # Verify DB was NOT queried (implicit since we didn't seed DB and mocked Redis hit)


@pytest.mark.asyncio
async def test_get_concept_redis_error_get(service: VocabularyService, async_session: AsyncSession) -> None:
    """Test resilience when Redis get fails."""
    assert service.redis is not None
    service.redis.get.side_effect = Exception("Redis connection failed")  # type: ignore[attr-defined]

    # Seed DB so it can fall back
    db_concept = Concept(
        concept_id=3,
        concept_name="Fallback Concept",
        domain_id="Device",
        vocabulary_id="SNOMED",
        concept_class_id="Device",
        concept_code="D123",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add(db_concept)
    await async_session.commit()

    concept = await service.get_concept(3)
    assert concept is not None
    assert concept.concept_id == 3
    # Should still try to set cache if get failed but set works (unlikely in real life but possible in mocks)
    service.redis.set.assert_called_once()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_get_concept_redis_error_set(service: VocabularyService, async_session: AsyncSession) -> None:
    """Test resilience when Redis set fails."""
    assert service.redis is not None
    service.redis.get.return_value = None  # type: ignore[attr-defined]
    service.redis.set.side_effect = Exception("Redis write failed")  # type: ignore[attr-defined]

    # Seed DB
    db_concept = Concept(
        concept_id=4,
        concept_name="Write Fail Concept",
        domain_id="Device",
        vocabulary_id="SNOMED",
        concept_class_id="Device",
        concept_code="D456",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add(db_concept)
    await async_session.commit()

    # Should not raise exception
    concept = await service.get_concept(4)
    assert concept is not None
    assert concept.concept_id == 4


@pytest.mark.asyncio
async def test_search_concepts_pagination(service: VocabularyService, async_session: AsyncSession) -> None:
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
async def test_search_concepts_filters_comprehensive(service: VocabularyService, async_session: AsyncSession) -> None:
    # Seed DB with various concepts
    c1 = Concept(
        concept_id=200,
        concept_name="Aspirin",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Ingredient",
        concept_code="A1",
        standard_concept="S",
        invalid_reason=None,
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
        standard_concept=None,  # 'N' effectively
        invalid_reason="D",
        valid_start_date=date.today(),
        valid_end_date=date.today(),
    )
    c3 = Concept(
        concept_id=202,
        concept_name="Old Drug",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Brand Name",
        concept_code="OD1",
        standard_concept=None,
        invalid_reason="U",
        valid_start_date=date.today(),
        valid_end_date=date.today(),
    )
    async_session.add_all([c1, c2, c3])
    await async_session.commit()

    # 1. Concept Class ID
    search = ConceptSearch(QUERY="", CONCEPT_CLASS_ID=["Ingredient"])
    results = await service.search_concepts(search)
    assert len(results) == 1
    assert results[0].concept_id == 200

    # 2. Invalid Reason = 'V' (valid, i.e., NULL in DB)
    search = ConceptSearch(QUERY="", INVALID_REASON="V")
    results = await service.search_concepts(search)
    # c1 has invalid_reason=None -> Valid
    # c2 has invalid_reason="D"
    # c3 has invalid_reason="U"
    assert len(results) == 1
    assert results[0].concept_id == 200

    # 3. Invalid Reason = 'D' (specific value)
    search = ConceptSearch(QUERY="", INVALID_REASON="D")
    results = await service.search_concepts(search)
    assert len(results) == 1
    assert results[0].concept_id == 201

    # 4. Standard Concept = 'N' (non-standard, i.e., NULL in DB)
    search = ConceptSearch(QUERY="", STANDARD_CONCEPT="N")
    results = await service.search_concepts(search)
    # c1 is 'S'
    # c2 is None -> 'N'
    # c3 is None -> 'N'
    assert len(results) == 2
    ids = {c.concept_id for c in results}
    assert 201 in ids
    assert 202 in ids

    # 5. Standard Concept = 'S' (specific value)
    search = ConceptSearch(QUERY="", STANDARD_CONCEPT="S")
    results = await service.search_concepts(search)
    assert len(results) == 1
    assert results[0].concept_id == 200

    # 6. Domain ID
    search = ConceptSearch(QUERY="", DOMAIN_ID=["Condition"])
    results = await service.search_concepts(search)
    assert len(results) == 1
    assert results[0].concept_id == 201

    # 7. Vocabulary ID
    search = ConceptSearch(QUERY="", VOCABULARY_ID=["RxNorm"])
    results = await service.search_concepts(search)
    assert len(results) == 2
    ids = {c.concept_id for c in results}
    assert 200 in ids
    assert 202 in ids
