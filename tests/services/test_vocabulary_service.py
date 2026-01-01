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
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import Concept as ConceptModel
from omop_atlas_backend.schemas.concept import Concept as ConceptSchema
from omop_atlas_backend.schemas.concept import ConceptSearch
from omop_atlas_backend.services.exceptions import ConceptNotFound
from omop_atlas_backend.services.vocabulary import VocabularyService


@pytest.fixture
def mock_db() -> AsyncMock:
    m = AsyncMock(spec=AsyncSession)
    # Ensure bind.dialect.name can be accessed
    m.bind = MagicMock()
    m.bind.dialect.name = "postgresql"
    return m


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    return redis


@pytest.fixture
def service(mock_db: AsyncMock, mock_redis: AsyncMock) -> VocabularyService:
    return VocabularyService(db=mock_db, redis=mock_redis)


@pytest.mark.asyncio
async def test_get_concept_by_id_cache_hit(service: VocabularyService, mock_redis: AsyncMock) -> None:
    """
    Test retrieving a concept that exists in the Redis cache.
    """
    schema_obj = ConceptSchema(
        concept_id=1,
        concept_name="Test Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="12345",
        valid_start_date=date(1970, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )

    mock_redis.get.return_value = schema_obj.model_dump_json()

    result = await service.get_concept_by_id(1)

    assert result.concept_id == 1
    assert result.concept_name == "Test Concept"
    mock_redis.get.assert_called_once_with("concept:1")
    service.db.execute.assert_not_called()  # type: ignore


@pytest.mark.asyncio
async def test_get_concept_by_id_cache_miss_db_hit(
    service: VocabularyService, mock_db: AsyncMock, mock_redis: AsyncMock
) -> None:
    """
    Test retrieving a concept that is not in cache but exists in DB.
    """
    mock_redis.get.return_value = None

    mock_concept_model = ConceptModel(
        concept_id=2,
        concept_name="DB Concept",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Ingredient",
        standard_concept="S",
        concept_code="54321",
        valid_start_date=date(1980, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )

    # Mocking the DB execution result
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_concept_model
    mock_db.execute.return_value = mock_result

    result = await service.get_concept_by_id(2)

    assert result.concept_id == 2
    assert result.concept_name == "DB Concept"
    mock_redis.get.assert_called_once_with("concept:2")
    mock_db.execute.assert_called_once()
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_get_concept_by_id_not_found(service: VocabularyService, mock_db: AsyncMock, mock_redis: AsyncMock) -> None:
    """
    Test retrieving a concept that exists nowhere.
    """
    mock_redis.get.return_value = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(ConceptNotFound) as exc:
        await service.get_concept_by_id(999)

    assert "Concept with ID 999 not found" in str(exc.value)
    mock_redis.get.assert_called_once_with("concept:999")
    mock_db.execute.assert_called_once()
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_get_concept_by_id_redis_failure_fallback(
    service: VocabularyService, mock_db: AsyncMock, mock_redis: AsyncMock
) -> None:
    """
    Test that if Redis fails, the service falls back to DB transparently.
    """
    mock_redis.get.side_effect = Exception("Redis is down")

    mock_concept_model = ConceptModel(
        concept_id=3,
        concept_name="Fallback Concept",
        domain_id="Meas",
        vocabulary_id="LOINC",
        concept_class_id="Lab Test",
        standard_concept="S",
        concept_code="98765",
        valid_start_date=date(2000, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_concept_model
    mock_db.execute.return_value = mock_result

    result = await service.get_concept_by_id(3)

    assert result.concept_id == 3
    # Should have tried Redis
    mock_redis.get.assert_called_once()
    # Should have executed DB query despite Redis error
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_search_concepts_fts_query_generation(service: VocabularyService, mock_db: AsyncMock) -> None:
    """
    Test that search_concepts generates the correct FTS query structure.
    """
    search = ConceptSearch(QUERY="aspirin")

    mock_result = MagicMock()
    # Return a model so it can be validated into a schema
    mock_concept = ConceptModel(
        concept_id=10,
        concept_name="Aspirin",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Ingredient",
        standard_concept="S",
        concept_code="111",
        valid_start_date=date(1970, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    mock_result.scalars.return_value.all.return_value = [mock_concept]
    mock_db.execute.return_value = mock_result

    results = await service.search_concepts(search)

    # Verify we got a schema back
    assert len(results) == 1
    assert isinstance(results[0], ConceptSchema)

    # Verify execute was called
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args
    stmt = call_args[0][0]

    # Verify FTS logic (to_tsvector) and Concept Code logic (ilike) are present
    assert "to_tsvector" in str(stmt)
    # The default str() of stmt might not show the values, but structure should be there
    # or_ is usually represented, let's just check the key parts
    assert "concept_code" in str(stmt)


@pytest.mark.asyncio
async def test_search_concepts_filters_logic(service: VocabularyService, mock_db: AsyncMock) -> None:
    """
    Test that filters are applied correctly, specifically the OMOP mapping logic.
    """
    # Test 1: Invalid Reason 'V' -> NULL
    search = ConceptSearch(QUERY="", INVALID_REASON="V")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    await service.search_concepts(search)

    call_args = mock_db.execute.call_args
    stmt = call_args[0][0]

    # Check for IS NULL on invalid_reason
    # In string representation, it usually shows as "invalid_reason IS NULL"
    assert "invalid_reason IS NULL" in str(stmt)

    # Test 2: Standard Concept 'N' -> NULL
    search = ConceptSearch(QUERY="", STANDARD_CONCEPT="N")
    await service.search_concepts(search)
    call_args = mock_db.execute.call_args
    stmt = call_args[0][0]
    assert "standard_concept IS NULL" in str(stmt)
