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
from omop_atlas_backend.schemas.concept import ConceptRelationship
from omop_atlas_backend.schemas.concept import RelatedConcept as RelatedConceptSchema
from omop_atlas_backend.services.vocabulary import VocabularyService


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    # Mocking db.bind.dialect.name for search_concepts if needed, though this test focuses on get_related_concepts
    session.bind = MagicMock()
    session.bind.dialect.name = "postgresql"
    return session


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    return redis


@pytest.fixture
def vocabulary_service_with_redis(mock_db_session: AsyncMock, mock_redis: AsyncMock) -> VocabularyService:
    return VocabularyService(mock_db_session, redis=mock_redis)


@pytest.mark.asyncio
async def test_get_related_concepts_cache_hit(
    vocabulary_service_with_redis: VocabularyService, mock_redis: AsyncMock, mock_db_session: AsyncMock
) -> None:
    """Test retrieving related concepts from Redis cache."""
    # Setup cache data
    # Use snake_case for python constructor to satisfy mypy
    cached_concept = RelatedConceptSchema(
        concept_id=1,
        concept_name="Cached Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="100",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
        relationships=[
            ConceptRelationship(relationship_name="Mapped from", relationship_distance=0, relationship_id="Mapped from")
        ],
    )
    # Serialize to JSON array string
    cached_json = "[" + cached_concept.model_dump_json(by_alias=True) + "]"
    mock_redis.get.return_value = cached_json

    # Execute
    result = await vocabulary_service_with_redis.get_related_concepts(1)

    # Assert
    assert len(result) == 1
    assert result[0].concept_id == 1
    assert result[0].concept_name == "Cached Concept"
    # Verify DB was NOT queried
    mock_db_session.execute.assert_not_called()
    # Verify Redis get was called
    mock_redis.get.assert_called_once_with("concept_related:1")


@pytest.mark.asyncio
async def test_get_related_concepts_cache_miss_and_set(
    vocabulary_service_with_redis: VocabularyService, mock_redis: AsyncMock, mock_db_session: AsyncMock
) -> None:
    """Test cache miss falls back to DB and sets cache."""
    # Setup Redis to return None (cache miss)
    mock_redis.get.return_value = None

    # Setup DB mock return values
    # We need to mock the 3 execute calls in get_related_concepts
    # 1. Direct relationships
    # 2. Ancestors
    # 3. Descendants

    # Create dummy models
    c1 = ConceptModel(
        concept_id=2,
        concept_name="Related",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="200",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )

    # Prepare query results
    # Each execute returns a Result object which we iterate over
    # row format: (concept, rel_name, rel_dist)

    # Result 1: One direct relationship
    res1 = MagicMock()
    res1.all.return_value = [(c1, "Mapped from", 0)]

    # Result 2: No ancestors
    res2 = MagicMock()
    res2.all.return_value = []

    # Result 3: No descendants
    res3 = MagicMock()
    res3.all.return_value = []

    mock_db_session.execute.side_effect = [res1, res2, res3]

    # Execute
    result = await vocabulary_service_with_redis.get_related_concepts(1)

    # Assert
    assert len(result) == 1
    assert result[0].concept_id == 2
    assert result[0].relationships[0].relationship_name == "Mapped from"

    # Verify Redis set was called
    assert mock_redis.set.called
    args, kwargs = mock_redis.set.call_args
    assert args[0] == "concept_related:1"
    assert "Mapped from" in args[1]  # Check content loosely
    assert kwargs.get("ex") == 3600


@pytest.mark.asyncio
async def test_get_related_concepts_redis_error_on_get(
    vocabulary_service_with_redis: VocabularyService, mock_redis: AsyncMock, mock_db_session: AsyncMock
) -> None:
    """Test Redis error on get is ignored and falls back to DB."""
    # Setup Redis to raise exception
    mock_redis.get.side_effect = Exception("Redis connection failed")

    # Setup DB mock (same as above)
    c1 = ConceptModel(
        concept_id=2,
        concept_name="Related",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="200",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )
    res1 = MagicMock()
    res1.all.return_value = [(c1, "Mapped from", 0)]
    mock_db_session.execute.side_effect = [res1, MagicMock(all=lambda: []), MagicMock(all=lambda: [])]

    # Execute
    result = await vocabulary_service_with_redis.get_related_concepts(1)

    # Assert
    assert len(result) == 1
    # Should succeed despite Redis error


@pytest.mark.asyncio
async def test_get_related_concepts_redis_error_on_set(
    vocabulary_service_with_redis: VocabularyService, mock_redis: AsyncMock, mock_db_session: AsyncMock
) -> None:
    """Test Redis error on set is ignored."""
    mock_redis.get.return_value = None
    mock_redis.set.side_effect = Exception("Redis write failed")

    # Setup DB
    c1 = ConceptModel(
        concept_id=2,
        concept_name="Related",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="200",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )
    res1 = MagicMock()
    res1.all.return_value = [(c1, "Mapped from", 0)]
    mock_db_session.execute.side_effect = [res1, MagicMock(all=lambda: []), MagicMock(all=lambda: [])]

    # Execute
    result = await vocabulary_service_with_redis.get_related_concepts(1)

    # Assert
    assert len(result) == 1
    # Should succeed despite Redis error
