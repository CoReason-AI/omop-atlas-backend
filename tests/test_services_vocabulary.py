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

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from omop_atlas_backend.models.vocabulary import Base, Concept, ConceptClass, Domain, Vocabulary
from omop_atlas_backend.schemas.concept import ConceptSearch
from omop_atlas_backend.services.exceptions import ConceptNotFound
from omop_atlas_backend.services.vocabulary import VocabularyService


@pytest_asyncio.fixture
async def db_session():
    # Use SQLite in-memory for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture
async def vocabulary_service(db_session):
    return VocabularyService(db_session, redis=None)


@pytest_asyncio.fixture
async def seed_data(db_session):
    # 1. Create dependencies
    vocab = Vocabulary(vocabulary_id="SNOMED", vocabulary_name="SNOMED", vocabulary_concept_id=0)
    domain = Domain(domain_id="Condition", domain_name="Condition", domain_concept_id=0)
    c_class = ConceptClass(
        concept_class_id="Clinical Finding", concept_class_name="Clinical Finding", concept_class_concept_id=0
    )

    db_session.add_all([vocab, domain, c_class])
    await db_session.commit()

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
    db_session.add(concept)
    await db_session.commit()
    return concept


@pytest.mark.asyncio
async def test_get_concept_by_id_success(vocabulary_service, seed_data):
    # Execute
    result = await vocabulary_service.get_concept_by_id(1)

    # Assert
    assert result.concept_id == 1
    assert result.concept_name == "Test Concept"
    assert result.domain_id == "Condition"


@pytest.mark.asyncio
async def test_get_concept_by_id_not_found(vocabulary_service):
    # Execute & Assert
    with pytest.raises(ConceptNotFound):
        await vocabulary_service.get_concept_by_id(999)


@pytest.mark.asyncio
async def test_search_concepts(vocabulary_service, seed_data):
    search = ConceptSearch(QUERY="Test")
    results = await vocabulary_service.search_concepts(search)
    assert len(results) == 1
    assert results[0].concept_id == 1


@pytest.mark.asyncio
async def test_search_concepts_by_filters(vocabulary_service, seed_data):
    # Test all filters
    search = ConceptSearch(
        QUERY="Test",
        VOCABULARY_ID=["SNOMED"],
        DOMAIN_ID=["Condition"],
        CONCEPT_CLASS_ID=["Clinical Finding"],
        STANDARD_CONCEPT="S",
    )
    results = await vocabulary_service.search_concepts(search)
    assert len(results) == 1

    # Test filter mismatch
    search_mismatch = ConceptSearch(QUERY="Test", VOCABULARY_ID=["ICD10"])
    results_empty = await vocabulary_service.search_concepts(search_mismatch)
    assert len(results_empty) == 0


@pytest.mark.asyncio
async def test_search_concepts_standard_concept_n(vocabulary_service, db_session, seed_data):
    # Create non-standard concept
    # seed_data already creates the dependent tables (Vocabulary, Domain, ConceptClass)
    # but we are using db_session directly here, so we need to ensure dependencies exist.
    # seed_data fixture runs before this test so they should exist.

    c_non_standard = Concept(
        concept_id=2,
        concept_name="Non Standard",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept=None,  # Non-standard
        concept_code="456",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )
    db_session.add(c_non_standard)
    await db_session.commit()

    search = ConceptSearch(STANDARD_CONCEPT="N")
    results = await vocabulary_service.search_concepts(search)
    assert len(results) >= 1
    found = any(c.concept_id == 2 for c in results)
    assert found


@pytest.mark.asyncio
async def test_search_concepts_invalid_reason_v(vocabulary_service, seed_data):
    search = ConceptSearch(INVALID_REASON="V")
    results = await vocabulary_service.search_concepts(search)
    assert len(results) >= 1

    # Check invalid
    search_invalid = ConceptSearch(INVALID_REASON="D")
    results_inv = await vocabulary_service.search_concepts(search_invalid)
    assert len(results_inv) == 0


@pytest.mark.asyncio
async def test_redis_caching(vocabulary_service, seed_data):
    # Mock redis
    from unittest.mock import AsyncMock, MagicMock

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock()

    vocabulary_service.redis = mock_redis

    # First call - cache miss
    await vocabulary_service.get_concept_by_id(1)
    mock_redis.get.assert_called_with("concept:1")
    mock_redis.set.assert_called()

    # Second call - cache hit
    mock_redis.get = AsyncMock(return_value=None)
    # To properly simulate cache hit we need to return valid json
    # but we can just verify the flow for now or use a real redis mock if needed
    # Let's verify that if redis returns something, we use it

    # Setup mock to return json
    concept_json = (
        '{"conceptId": 1, "conceptName": "Test Concept", "domainId": "Condition", '
        '"vocabularyId": "SNOMED", "conceptClassId": "Clinical Finding", "standardConcept": "S", '
        '"conceptCode": "123", "validStartDate": "2020-01-01", "validEndDate": "2099-12-31", "invalidReason": null}'
    )
    mock_redis.get = AsyncMock(return_value=concept_json)

    result = await vocabulary_service.get_concept_by_id(1)
    assert result.concept_id == 1
    assert result.concept_name == "Test Concept"

    # Verify set was not called (or called previously) - actually we don't call set if we found it in cache?
    # Checking logic: if cached: return ...
    # So set is NOT called if found in cache.
    mock_redis.set.reset_mock()
    await vocabulary_service.get_concept_by_id(1)
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_redis_error_handling(vocabulary_service, seed_data):
    # Mock redis raising exception
    from unittest.mock import AsyncMock, MagicMock

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=Exception("Redis down"))
    mock_redis.set = AsyncMock(side_effect=Exception("Redis down"))

    vocabulary_service.redis = mock_redis

    # Should not raise exception
    result = await vocabulary_service.get_concept_by_id(1)
    assert result.concept_id == 1
