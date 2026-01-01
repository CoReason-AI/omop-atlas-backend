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
async def test_search_concepts_invalid_reason_v(vocabulary_service: VocabularyService, seed_data: Concept) -> None:
    search = ConceptSearch(INVALID_REASON="V")
    results = await vocabulary_service.search_concepts(search)
    assert len(results) >= 1

    # Check invalid
    search_invalid = ConceptSearch(INVALID_REASON="D")
    results_inv = await vocabulary_service.search_concepts(search_invalid)
    assert len(results_inv) == 0


@pytest.mark.asyncio
async def test_search_concepts_standard_concept_mapping(
    vocabulary_service: VocabularyService, db_session: AsyncSession, seed_data: Concept
) -> None:
    """Test that standard_concept 'N' maps to NULL."""
    # Create non-standard concept (NULL standard_concept)
    c_non_standard = Concept(
        concept_id=2,
        concept_name="Non Standard",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept=None,  # This maps to 'N' in search
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
async def test_search_concepts_invalid_reason_mapping(
    vocabulary_service: VocabularyService, db_session: AsyncSession, seed_data: Concept
) -> None:
    """Test that invalid_reason 'V' maps to NULL."""
    # seed_data has invalid_reason=None, which corresponds to 'V' (Valid)
    search = ConceptSearch(INVALID_REASON="V")
    results = await vocabulary_service.search_concepts(search)
    assert len(results) >= 1
    found = any(c.concept_id == 1 for c in results)
    assert found

    # Add an invalid one
    c_invalid = Concept(
        concept_id=3,
        concept_name="Invalid Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="789",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason="D",  # Deleted
    )
    db_session.add(c_invalid)
    await db_session.commit()

    # Search for V should NOT find the invalid one
    search_v = ConceptSearch(INVALID_REASON="V")
    results_v = await vocabulary_service.search_concepts(search_v)
    assert not any(c.concept_id == 3 for c in results_v)

    # Search for D should find it
    search_d = ConceptSearch(INVALID_REASON="D")
    results_d = await vocabulary_service.search_concepts(search_d)
    assert any(c.concept_id == 3 for c in results_d)


@pytest.mark.asyncio
async def test_search_concepts_postgres_fts_path(vocabulary_service: VocabularyService, seed_data: Concept) -> None:
    """Test the Postgres FTS code path by mocking the dialect name."""
    from unittest.mock import MagicMock

    # Mock the dialect name on the session bind
    # Note: accessing db.bind.dialect.name
    # vocabulary_service.db is the session.
    # We need to mock the bind (Engine/Connection) and its dialect.

    # Since we are using an actual AsyncSession with SQLite, mocking the bind is tricky
    # without breaking the session. However, the service code checks:
    # dialect_name = self.db.bind.dialect.name if self.db.bind else "postgresql"

    # We can temporarily mock self.db.bind.dialect.name
    original_bind = vocabulary_service.db.bind

    # Create a mock bind with dialect.name = "postgresql"
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"

    # We cannot easily replace the bind on an active session.
    # But we can subclass/wrap the session or just mock the property if possible.
    # Alternatively, we can instantiate the service with a Mock session that delegates execute to the real one
    # but reports a different dialect.

    # Let's try mocking the attribute access on the bind if it's not None
    if original_bind:
        # This is harder because original_bind is a real object.
        pass

    # Better approach: Mock the db session passed to the service ONLY for checking the dialect
    # But we want the execute() to run against the real SQLite DB to see if it generates SQL.
    # Wait, SQLite won't understand `to_tsvector`. So if we force the Postgres path,
    # the query execution WILL FAIL on SQLite.
    # That is actually a GOOD test that we hit the Postgres path!
    # So we expect an OperationalError from SQLite when it sees to_tsvector.

    # Create a wrapper or mock for the session
    real_session = vocabulary_service.db

    # Create a proxy that returns "postgresql" for bind.dialect.name
    # but delegates execute to real_session.
    class SessionProxy:
        bind = MagicMock()
        bind.dialect.name = "postgresql"

        async def execute(self, stmt: Any) -> Any:
            return await real_session.execute(stmt)

    # Swap the session
    vocabulary_service.db = cast(AsyncSession, SessionProxy())

    search = ConceptSearch(QUERY="Test")

    # This should fail because SQLite doesn't support to_tsvector
    # If it fails with "no such function: to_tsvector", we know we hit the Postgres path.
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
