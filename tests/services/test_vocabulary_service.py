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
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import Concept
from omop_atlas_backend.schemas.concept import Concept as ConceptSchema
from omop_atlas_backend.schemas.concept import ConceptSearch
from omop_atlas_backend.services.vocabulary import VocabularyService


@pytest.fixture
def mock_db():
    mock = AsyncMock(spec=AsyncSession)
    # configure bind.dialect.name
    mock.bind = MagicMock()
    mock.bind.dialect.name = "sqlite"  # default
    return mock


@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    # Need to mock the generic Redis type behavior if inspected
    return mock


@pytest.fixture
def service(mock_db, mock_redis):
    return VocabularyService(db=mock_db, redis=mock_redis)


@pytest.fixture
def sample_concept():
    return Concept(
        concept_id=1,
        concept_name="Test Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="12345",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )


@pytest.mark.asyncio
async def test_get_concept_redis_hit(service, mock_redis, sample_concept):
    """Test get_concept returns cached data from Redis."""
    schema = ConceptSchema.model_validate(sample_concept)
    mock_redis.get.return_value = schema.model_dump_json()

    result = await service.get_concept(1)

    assert result == schema
    mock_redis.get.assert_awaited_once_with("concept:1")
    service.db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_concept_redis_miss_db_hit(service, mock_redis, mock_db, sample_concept):
    """Test get_concept fetches from DB on Redis miss and caches result."""
    mock_redis.get.return_value = None

    # Mock DB result
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = sample_concept
    mock_db.execute.return_value = mock_result

    result = await service.get_concept(1)

    assert result.concept_id == 1
    mock_redis.get.assert_awaited_once_with("concept:1")
    mock_db.execute.assert_awaited_once()
    mock_redis.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_concept_db_miss(service, mock_redis, mock_db):
    """Test get_concept returns None if not in DB."""
    mock_redis.get.return_value = None

    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    result = await service.get_concept(999)

    assert result is None
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_get_concept_redis_failure(service, mock_redis, mock_db, sample_concept):
    """Test get_concept falls back to DB if Redis raises exception."""
    mock_redis.get.side_effect = Exception("Redis down")

    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = sample_concept
    mock_db.execute.return_value = mock_result

    result = await service.get_concept(1)

    assert result.concept_id == 1
    # Should attempt to cache but handle exception if set fails too
    mock_redis.set.side_effect = Exception("Redis down")
    await service.get_concept(1)  # Should not raise


@pytest.mark.asyncio
async def test_search_concepts_basic(service, mock_db, sample_concept):
    """Test basic search functionality."""
    mock_result = MagicMock(spec=Result)
    mock_result.scalars.return_value.all.return_value = [sample_concept]
    mock_db.execute.return_value = mock_result

    # Mock dialect to not be postgres
    mock_db.bind.dialect.name = "sqlite"

    search = ConceptSearch(QUERY="Test")
    results = await service.search_concepts(search)

    assert len(results) == 1
    assert results[0].concept_id == 1
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_concepts_postgres_fts(service, mock_db, sample_concept):
    """Test search uses Postgres FTS optimizations."""
    mock_result = MagicMock(spec=Result)
    mock_result.scalars.return_value.all.return_value = [sample_concept]
    mock_db.execute.return_value = mock_result

    # Mock dialect to be postgres
    mock_db.bind.dialect.name = "postgresql"

    search = ConceptSearch(QUERY="Test")
    await service.search_concepts(search)

    # Verify db.execute was called
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_concepts_filters(service, mock_db, sample_concept):
    """Test search with various filters."""
    mock_result = MagicMock(spec=Result)
    mock_result.scalars.return_value.all.return_value = [sample_concept]
    mock_db.execute.return_value = mock_result
    mock_db.bind = None  # Simulate no bind or non-postgres

    search = ConceptSearch(
        QUERY="Test",
        DOMAIN_ID=["Condition"],
        VOCABULARY_ID=["SNOMED"],
        CONCEPT_CLASS_ID=["Clinical Finding"],
        INVALID_REASON="V",
        STANDARD_CONCEPT="S",
    )

    await service.search_concepts(search)
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_concepts_filters_negative(service, mock_db, sample_concept):
    """Test search with negative filters (N, V logic)."""
    mock_result = MagicMock(spec=Result)
    mock_result.scalars.return_value.all.return_value = [sample_concept]
    mock_db.execute.return_value = mock_result
    mock_db.bind = None

    search = ConceptSearch(
        QUERY="Test",
        INVALID_REASON="D",  # Valid invalid reason
        STANDARD_CONCEPT="N",  # Non-standard
    )

    await service.search_concepts(search)
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_concepts_bind_error(sample_concept):
    """Test search handles exception when checking dialect."""

    # Use a custom class to avoid polluting global AsyncMock
    class SafeMockSession(AsyncMock):
        pass

    mock_db = SafeMockSession(spec=AsyncSession)

    mock_result = MagicMock(spec=Result)
    mock_result.scalars.return_value.all.return_value = [sample_concept]
    mock_db.execute.return_value = mock_result

    # Mock db.bind access to raise exception on this specific class
    p = PropertyMock(side_effect=Exception("DB Error"))
    type(mock_db).bind = p

    service = VocabularyService(db=mock_db, redis=None)
    search = ConceptSearch(QUERY="Test")

    await service.search_concepts(search)

    mock_db.execute.assert_awaited_once()
