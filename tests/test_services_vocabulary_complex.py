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
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from omop_atlas_backend.models.base import Base
from omop_atlas_backend.models.vocabulary import Concept, ConceptClass, Domain, Vocabulary
from omop_atlas_backend.schemas.concept import ConceptSearch
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
async def complex_seed_data(db_session: AsyncSession) -> None:
    # 1. Create dependencies
    vocab = Vocabulary(vocabulary_id="SNOMED", vocabulary_name="SNOMED", vocabulary_concept_id=0)
    vocab2 = Vocabulary(vocabulary_id="ICD10", vocabulary_name="ICD10", vocabulary_concept_id=0)
    domain = Domain(domain_id="Condition", domain_name="Condition", domain_concept_id=0)
    domain2 = Domain(domain_id="Drug", domain_name="Drug", domain_concept_id=0)
    c_class = ConceptClass(
        concept_class_id="Clinical Finding", concept_class_name="Clinical Finding", concept_class_concept_id=0
    )
    c_class2 = ConceptClass(concept_class_id="Ingredient", concept_class_name="Ingredient", concept_class_concept_id=0)

    db_session.add_all([vocab, vocab2, domain, domain2, c_class, c_class2])
    await db_session.commit()

    # 2. Create Concepts
    concepts = [
        Concept(
            concept_id=1,
            concept_name="Aspirin",
            domain_id="Drug",
            vocabulary_id="SNOMED",
            concept_class_id="Ingredient",
            standard_concept="S",
            concept_code="111",
            valid_start_date=date(2020, 1, 1),
            valid_end_date=date(2099, 12, 31),
        ),
        Concept(
            concept_id=2,
            concept_name="Headache",
            domain_id="Condition",
            vocabulary_id="SNOMED",
            concept_class_id="Clinical Finding",
            standard_concept="S",
            concept_code="222",
            valid_start_date=date(2020, 1, 1),
            valid_end_date=date(2099, 12, 31),
        ),
        Concept(
            concept_id=3,
            concept_name="Legacy Drug",
            domain_id="Drug",
            vocabulary_id="SNOMED",
            concept_class_id="Ingredient",
            standard_concept=None,  # Non-standard
            concept_code="333",
            valid_start_date=date(2020, 1, 1),
            valid_end_date=date(2099, 12, 31),
        ),
        Concept(
            concept_id=4,
            concept_name="Invalid Concept",
            domain_id="Condition",
            vocabulary_id="ICD10",
            concept_class_id="Clinical Finding",
            standard_concept="S",
            concept_code="444",
            valid_start_date=date(2020, 1, 1),
            valid_end_date=date(2020, 1, 2),
            invalid_reason="D",  # Deleted
        ),
    ]
    db_session.add_all(concepts)
    await db_session.commit()


@pytest.mark.asyncio
async def test_complex_filter_combination(vocabulary_service: VocabularyService, complex_seed_data: None) -> None:
    # Match specific standard drug
    search = ConceptSearch(
        QUERY="Aspirin",
        DOMAIN_ID=["Drug"],
        VOCABULARY_ID=["SNOMED"],
        STANDARD_CONCEPT="S",
    )
    results = await vocabulary_service.search_concepts(search)
    assert len(results) == 1
    assert results[0].concept_id == 1


@pytest.mark.asyncio
async def test_pagination_logic(vocabulary_service: VocabularyService, complex_seed_data: None) -> None:
    # Match "a" in name (Aspirin, Headache, Legacy Drug, Invalid Concept)
    # Aspirin(1), Headache(2), Legacy Drug(3), Invalid Concept(4)
    # Note: Search without query matches everything?
    # Our search implementation: if query is empty, it skips name filter unless explicitly required.
    # The default impl `if search.query:` means empty query returns everything subject to other filters.

    search = ConceptSearch()
    # Order isn't guaranteed without explicit order_by in service, but usually insertion order in SQLite.
    # Let's assume stability or just check counts.

    # Page 1, limit 2
    results_p1 = await vocabulary_service.search_concepts(search, limit=2, offset=0)
    assert len(results_p1) == 2

    # Page 2, limit 2
    results_p2 = await vocabulary_service.search_concepts(search, limit=2, offset=2)
    assert len(results_p2) == 2

    # Verify distinctness (set of IDs)
    ids_p1 = {c.concept_id for c in results_p1}
    ids_p2 = {c.concept_id for c in results_p2}
    assert ids_p1.isdisjoint(ids_p2)


@pytest.mark.asyncio
async def test_conflicting_filters_return_empty(vocabulary_service: VocabularyService, complex_seed_data: None) -> None:
    # Domain Condition but Class Ingredient (Mismatch in our data)
    search = ConceptSearch(
        DOMAIN_ID=["Condition"],
        CONCEPT_CLASS_ID=["Ingredient"],
    )
    results = await vocabulary_service.search_concepts(search)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_invalid_reason_filter_logic(vocabulary_service: VocabularyService, complex_seed_data: None) -> None:
    # 1. Valid only (invalid_reason is NULL)
    # Our service logic: if invalid_reason == "V", it filters for NULL.
    search_valid = ConceptSearch(INVALID_REASON="V")
    results = await vocabulary_service.search_concepts(search_valid)
    # Should get 1, 2, 3. 4 is 'D'.
    assert len(results) == 3
    assert all(c.concept_id != 4 for c in results)

    # 2. Deleted only
    search_deleted = ConceptSearch(INVALID_REASON="D")
    results_deleted = await vocabulary_service.search_concepts(search_deleted)
    assert len(results_deleted) == 1
    assert results_deleted[0].concept_id == 4
