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
from typing import Any, AsyncGenerator, cast

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from omop_atlas_backend.models.base import Base
from omop_atlas_backend.models.vocabulary import Concept, ConceptClass, Domain, Vocabulary
from omop_atlas_backend.schemas.concept import ConceptSearch
from omop_atlas_backend.services.exceptions import ConceptNotFound
from omop_atlas_backend.services.vocabulary import VocabularyService


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # Use SQLite in-memory for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture
async def vocabulary_service(db_session: AsyncSession) -> VocabularyService:
    return VocabularyService(db_session, redis=None)


@pytest_asyncio.fixture
async def seed_data(db_session: AsyncSession) -> Concept:
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
async def test_get_concept_by_id_success(vocabulary_service: VocabularyService, seed_data: Concept) -> None:
    # Execute
    result = await vocabulary_service.get_concept_by_id(1)

    # Assert
    assert result.concept_id == 1
    assert result.concept_name == "Test Concept"
    assert result.domain_id == "Condition"


@pytest.mark.asyncio
async def test_get_concept_by_id_not_found(vocabulary_service: VocabularyService) -> None:
    # Execute & Assert
    with pytest.raises(ConceptNotFound):
        await vocabulary_service.get_concept_by_id(999)


@pytest.mark.asyncio
async def test_search_concepts(vocabulary_service: VocabularyService, seed_data: Concept) -> None:
    search = ConceptSearch(QUERY="Test")
    results = await vocabulary_service.search_concepts(search)
    assert len(results) == 1
    assert results[0].concept_id == 1


@pytest.mark.asyncio
async def test_search_concepts_by_filters(vocabulary_service: VocabularyService, seed_data: Concept) -> None:
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
async def test_search_concepts_standard_concept_n(
    vocabulary_service: VocabularyService, db_session: AsyncSession, seed_data: Concept
) -> None:
    # Create non-standard concept
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
async def test_search_concepts_invalid_reason_v(vocabulary_service: VocabularyService, seed_data: Concept) -> None:
    search = ConceptSearch(INVALID_REASON="V")
    results = await vocabulary_service.search_concepts(search)
    assert len(results) >= 1

    # Check invalid
    search_invalid = ConceptSearch(INVALID_REASON="D")
    results_inv = await vocabulary_service.search_concepts(search_invalid)
    assert len(results_inv) == 0


@pytest.mark.asyncio
async def test_search_concepts_postgres_fts_path(vocabulary_service: VocabularyService, seed_data: Concept) -> None:
    """Test the Postgres FTS code path by mocking the dialect name."""
    from unittest.mock import MagicMock

    # Create a wrapper or mock for the session
    real_session = vocabulary_service.db

    # Create a proxy that returns "postgresql" for bind.dialect.name
    class SessionProxy:
        bind = MagicMock()
        bind.dialect.name = "postgresql"

        async def execute(self, stmt: Any) -> Any:
            return await real_session.execute(stmt)

    # Swap the session
    vocabulary_service.db = cast(AsyncSession, SessionProxy())

    search = ConceptSearch(QUERY="Test")

    # This should fail because SQLite doesn't support to_tsvector
    from sqlalchemy.exc import OperationalError

    with pytest.raises(OperationalError) as excinfo:
        await vocabulary_service.search_concepts(search)

    # SQLite might complain about '@' token (unrecognized) or 'to_tsvector' function
    error_msg = str(excinfo.value)
    assert "no such function: to_tsvector" in error_msg or 'unrecognized token: "@"' in error_msg

    # Restore session
    vocabulary_service.db = real_session


@pytest.mark.asyncio
async def test_redis_caching(vocabulary_service: VocabularyService, seed_data: Concept) -> None:
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
    mock_redis.set.reset_mock()
    await vocabulary_service.get_concept_by_id(1)
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_redis_error_handling(vocabulary_service: VocabularyService, seed_data: Concept) -> None:
    # Mock redis raising exception
    from unittest.mock import AsyncMock, MagicMock

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=Exception("Redis down"))
    mock_redis.set = AsyncMock(side_effect=Exception("Redis down"))

    vocabulary_service.redis = mock_redis

    # Should not raise exception
    result = await vocabulary_service.get_concept_by_id(1)
    assert result.concept_id == 1


@pytest.mark.asyncio
async def test_search_concepts_special_characters(vocabulary_service: VocabularyService, seed_data: Concept) -> None:
    """Test searching with special characters like quotes or percent signs."""
    # Test valid SQL special chars (should be handled by ILIKE)
    search = ConceptSearch(QUERY="%Test%")
    results = await vocabulary_service.search_concepts(search)
    assert len(results) >= 1  # Should match "Test Concept"

    # Test characters that might cause issues if not escaped properly
    # Note: SQLite ILIKE might behave differently than Postgres with some chars,
    # but basic SQL safety is handled by SQLAlchemy bind parameters.
    search_quote = ConceptSearch(QUERY="Test's Concept")
    results_quote = await vocabulary_service.search_concepts(search_quote)
    assert len(results_quote) == 0  # Should be safe, returns nothing


@pytest.mark.asyncio
async def test_redis_cache_corruption(vocabulary_service: VocabularyService, seed_data: Concept) -> None:
    """Test that invalid JSON in Redis causes a fallback to DB."""
    from unittest.mock import AsyncMock, MagicMock

    mock_redis = MagicMock()
    # Return garbage that fails JSON parsing/validation
    mock_redis.get = AsyncMock(return_value="{invalid-json")
    mock_redis.set = AsyncMock()

    vocabulary_service.redis = mock_redis

    # Should fall back to DB and succeed
    result = await vocabulary_service.get_concept_by_id(1)
    assert result.concept_id == 1


@pytest.mark.asyncio
async def test_search_concepts_case_sensitivity(
    vocabulary_service: VocabularyService, db_session: AsyncSession, seed_data: Concept
) -> None:
    """Test case sensitivity for standard_concept filters."""
    # Concept(standard_concept="S") exists.
    # Search with "s" (lowercase) should fail if it's strictly case-sensitive exact match.
    search_lower = ConceptSearch(STANDARD_CONCEPT="s")
    results = await vocabulary_service.search_concepts(search_lower)
    assert len(results) == 0

    # Search with "S" (uppercase) should succeed
    search_upper = ConceptSearch(STANDARD_CONCEPT="S")
    results_upper = await vocabulary_service.search_concepts(search_upper)
    assert len(results_upper) == 1


@pytest.mark.asyncio
async def test_search_concepts_lexical(
    vocabulary_service: VocabularyService, db_session: AsyncSession, seed_data: Concept
) -> None:
    # 1. Create dependencies for lexical search
    from omop_atlas_backend.models.vocabulary import ConceptSynonym

    # Add a synonym for the existing concept (concept_id=1, "Test Concept")
    # Synonym: "Trial Idea"
    synonym = ConceptSynonym(
        concept_id=1,
        concept_synonym_name="Trial Idea",
        language_concept_id=4180186,  # English
    )
    db_session.add(synonym)

    # Add another concept to test ranking
    # Concept: "Test Concept Extended" -> Match "Test Concept"
    concept2 = Concept(
        concept_id=2,
        concept_name="Test Concept Extended",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="999",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )
    db_session.add(concept2)
    await db_session.commit()

    # Search for "Test Concept"
    # Should match concept 1 ("Test Concept") - Exact match -> Higher score
    # Should match concept 2 ("Test Concept Extended") - Partial match -> Lower score
    search = ConceptSearch(QUERY="Test Concept", IS_LEXICAL=True)
    results = await vocabulary_service.search_concepts(search)

    assert len(results) >= 2
    # Concept 1 should be first because it's a closer match (shorter length diff)
    assert results[0].concept_id == 1
    assert results[1].concept_id == 2

    # Search by Synonym "Trial"
    search_syn = ConceptSearch(QUERY="Trial", IS_LEXICAL=True)
    results_syn = await vocabulary_service.search_concepts(search_syn)
    assert len(results_syn) >= 1
    assert results_syn[0].concept_id == 1

@pytest.mark.asyncio
async def test_search_concepts_lexical_whitespace_and_non_standard(
    vocabulary_service: VocabularyService, db_session: AsyncSession, seed_data: Concept
) -> None:
    # 1. Test multiple spaces
    # Existing concept name: "Test Concept"
    # Query with multiple spaces: "Test  Concept"
    search = ConceptSearch(QUERY="Test  Concept", IS_LEXICAL=True)
    results = await vocabulary_service.search_concepts(search)
    assert len(results) >= 1
    assert results[0].concept_id == 1

    # 2. Test searching for non-standard concept
    # Create non-standard concept
    c_non_standard = Concept(
        concept_id=3,
        concept_name="Non Standard Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept=None,
        concept_code="NS1",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )
    db_session.add(c_non_standard)
    await db_session.commit()

    # Search explicitly for non-standard
    search_ns = ConceptSearch(QUERY="Non Standard", IS_LEXICAL=True, STANDARD_CONCEPT="N")
    results_ns = await vocabulary_service.search_concepts(search_ns)
    assert len(results_ns) >= 1
    assert results_ns[0].concept_id == 3

    # Ensure regular search doesn't find it if we filter for 'S'
    search_s = ConceptSearch(QUERY="Non Standard", IS_LEXICAL=True, STANDARD_CONCEPT="S")
    results_s = await vocabulary_service.search_concepts(search_s)
    assert len(results_s) == 0
