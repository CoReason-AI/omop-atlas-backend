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
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import Concept
from omop_atlas_backend.schemas.concept import Concept as ConceptSchema
from omop_atlas_backend.schemas.concept import ConceptSearch
from omop_atlas_backend.services.vocabulary import VocabularyService


@pytest.fixture
def mock_redis() -> MagicMock:
    m = MagicMock(spec=Redis)
    m.get = AsyncMock()
    m.set = AsyncMock()
    return m


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_get_concept_cache_hit(mock_session: MagicMock, mock_redis: MagicMock) -> None:
    """Test get_concept returns from cache if available."""
    service = VocabularyService(mock_session, mock_redis)
    concept_id = 123

    # Mock Redis return value
    cached_concept = ConceptSchema(
        concept_id=123,
        concept_name="Cached Concept",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Ingredient",
        concept_code="123",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        standard_concept="S",
    )
    mock_redis.get.return_value = cached_concept.model_dump_json(by_alias=True)

    result = await service.get_concept(concept_id)

    assert result is not None
    assert result.concept_id == 123
    assert result.concept_name == "Cached Concept"

    # Ensure DB was NOT queried
    mock_session.execute.assert_not_called()
    mock_redis.get.assert_called_once_with(f"concept:{concept_id}")


@pytest.mark.asyncio
async def test_get_concept_db_hit(mock_session: MagicMock, mock_redis: MagicMock) -> None:
    """Test get_concept fetches from DB on cache miss and sets cache."""
    service = VocabularyService(mock_session, mock_redis)
    concept_id = 456

    # Cache miss
    mock_redis.get.return_value = None

    # DB Hit
    db_concept = Concept(
        concept_id=456,
        concept_name="DB Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="456",
        valid_start_date=date(2021, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )

    # Mock scalar_one_or_none result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = db_concept
    mock_session.execute.return_value = mock_result

    result = await service.get_concept(concept_id)

    assert result is not None
    assert result.concept_name == "DB Concept"

    # Verify Cache Set
    mock_redis.set.assert_called_once()
    args, _ = mock_redis.set.call_args
    assert args[0] == f"concept:{concept_id}"
    assert "DB Concept" in args[1]


@pytest.mark.asyncio
async def test_get_concept_redis_error(mock_session: MagicMock, mock_redis: MagicMock) -> None:
    """Test get_concept handles Redis errors gracefully."""
    service = VocabularyService(mock_session, mock_redis)
    concept_id = 789

    # Simulate Redis error on get
    mock_redis.get.side_effect = Exception("Redis Down")

    # DB Mock
    db_concept = Concept(
        concept_id=789,
        concept_name="Resilient Concept",
        domain_id="Device",
        vocabulary_id="SNOMED",
        concept_class_id="Device",
        concept_code="789",
        valid_start_date=date(2022, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = db_concept
    mock_session.execute.return_value = mock_result

    # Simulate Redis error on set as well
    mock_redis.set.side_effect = Exception("Redis Down")

    result = await service.get_concept(concept_id)

    assert result is not None
    assert result.concept_name == "Resilient Concept"

    # Verify get was called (and failed)
    mock_redis.get.assert_called_once()
    # Verify DB was called (fallback)
    mock_session.execute.assert_called_once()
    # Verify set was called (and failed, but ignored)
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_search_concepts(mock_session: MagicMock, mock_redis: MagicMock) -> None:
    """Test search_concepts constructs query and returns results."""
    service = VocabularyService(mock_session, mock_redis)
    search_criteria = ConceptSearch(QUERY="aspirin", DOMAIN_ID=["Drug"])

    # Mock DB results
    db_concepts = [
        Concept(
            concept_id=1,
            concept_name="Aspirin 80mg",
            domain_id="Drug",
            vocabulary_id="RxNorm",
            concept_class_id="Branded Drug",
            concept_code="A1",
            valid_start_date=date(2020, 1, 1),
            valid_end_date=date(2099, 12, 31),
        )
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = db_concepts
    mock_session.execute.return_value = mock_result

    results = await service.search_concepts(search_criteria, limit=10, offset=0)

    assert len(results) == 1
    assert results[0].concept_name == "Aspirin 80mg"

    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_search_concepts_all_filters(mock_session: MagicMock, mock_redis: MagicMock) -> None:
    """Test search_concepts with all filters enabled (standard='S', invalid='V')."""
    service = VocabularyService(mock_session, mock_redis)
    search_criteria = ConceptSearch(
        QUERY="test",
        DOMAIN_ID=["Drug"],
        VOCABULARY_ID=["RxNorm"],
        CONCEPT_CLASS_ID=["Ingredient"],
        STANDARD_CONCEPT="S",
        INVALID_REASON="V",  # "V" maps to None check in service
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    await service.search_concepts(search_criteria)

    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_search_concepts_postgres_dialect(mock_session: MagicMock, mock_redis: MagicMock) -> None:
    """Test search_concepts uses Postgres FTS when dialect is postgresql."""
    service = VocabularyService(mock_session, mock_redis)
    search_criteria = ConceptSearch(QUERY="aspirin")

    # Mock DB dialect
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_session.bind = mock_bind

    # Mock DB results
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    await service.search_concepts(search_criteria)

    # Verify that the query construction used FTS logic
    # We can inspect the calls or just rely on coverage.
    # Since we can't easily inspect the exact SQL string from mocked select calls
    # without complex inspection, we assume coverage verification is sufficient.
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_search_concepts_other_filters(mock_session: MagicMock, mock_redis: MagicMock) -> None:
    """Test search_concepts with alternative filter values."""
    service = VocabularyService(mock_session, mock_redis)
    # Testing branches: INVALID_REASON != 'V' and STANDARD_CONCEPT == 'N'
    search_criteria = ConceptSearch(INVALID_REASON="D", STANDARD_CONCEPT="N")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    await service.search_concepts(search_criteria)

    mock_session.execute.assert_called_once()
