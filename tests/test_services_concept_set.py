# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.security import User
from omop_atlas_backend.models.vocabulary import Concept
from omop_atlas_backend.schemas.concept_set import ConceptSetCreate, ConceptSetItemCreate
from omop_atlas_backend.services.concept_set import ConceptSetService
from omop_atlas_backend.services.exceptions import (
    ConceptNotFound,
    DuplicateResourceError,
    ValidationError,
)

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest_asyncio.fixture
async def concept_set_service(async_session: AsyncSession) -> ConceptSetService:
    return ConceptSetService(async_session)


@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession) -> User:
    user = User(username="test_user_cs", password_hash="hash")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_concepts(async_session: AsyncSession) -> list[Concept]:
    from datetime import date

    from omop_atlas_backend.models.vocabulary import ConceptClass, Domain, Vocabulary

    # Create required dependencies
    d1 = Domain(domain_id="Condition", domain_name="Condition", domain_concept_id=0)
    d2 = Domain(domain_id="Drug", domain_name="Drug", domain_concept_id=0)

    v1 = Vocabulary(vocabulary_id="SNOMED", vocabulary_name="SNOMED", vocabulary_concept_id=0)
    v2 = Vocabulary(vocabulary_id="RxNorm", vocabulary_name="RxNorm", vocabulary_concept_id=0)

    cc1 = ConceptClass(
        concept_class_id="Clinical Finding", concept_class_name="Clinical Finding", concept_class_concept_id=0
    )
    cc2 = ConceptClass(concept_class_id="Ingredient", concept_class_name="Ingredient", concept_class_concept_id=0)

    async_session.add_all([d1, d2, v1, v2, cc1, cc2])
    await async_session.commit()

    # Create some dummy concepts for testing
    c1 = Concept(
        concept_id=101,
        concept_name="Concept 101",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="C101",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    c2 = Concept(
        concept_id=102,
        concept_name="Concept 102",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Ingredient",
        concept_code="C102",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add_all([c1, c2])
    await async_session.commit()
    return [c1, c2]


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_valid_concept_set(
    concept_set_service: ConceptSetService, test_user: User, sample_concepts: list[Concept]
) -> None:
    """
    Standard Case: Create a valid Concept Set with items.
    """
    item1 = ConceptSetItemCreate(concept_id=101, isExcluded=False, includeDescendants=False, includeMapped=False)
    item2 = ConceptSetItemCreate(concept_id=102, isExcluded=True, includeDescendants=False, includeMapped=False)

    data = ConceptSetCreate(name="My First Concept Set", items=[item1, item2])

    result = await concept_set_service.create_concept_set(data, test_user.id)

    assert result.concept_set_id is not None
    assert result.concept_set_name == "My First Concept Set"
    assert result.created_by_id == test_user.id
    assert len(result.items) == 2

    # Verify items are correct
    ids = {item.concept_id for item in result.items}
    assert 101 in ids
    assert 102 in ids


@pytest.mark.asyncio
async def test_create_concept_set_non_existent_concept(
    concept_set_service: ConceptSetService, test_user: User, sample_concepts: list[Concept]
) -> None:
    """
    Edge Case 1: Concept ID does not exist in Vocabulary.
    Should raise ConceptNotFound.
    """
    # 999 does not exist
    item = ConceptSetItemCreate(concept_id=999, isExcluded=False, includeDescendants=False, includeMapped=False)
    data = ConceptSetCreate(name="Invalid Set", items=[item])

    with pytest.raises(ConceptNotFound) as exc:
        await concept_set_service.create_concept_set(data, test_user.id)

    assert "999" in str(exc.value)


@pytest.mark.asyncio
async def test_create_duplicate_concept_set_name(
    concept_set_service: ConceptSetService, test_user: User, sample_concepts: list[Concept]
) -> None:
    """
    Edge Case 2: Duplicate Concept Set Name.
    Should raise DuplicateResourceError.
    """
    data1 = ConceptSetCreate(name="Unique Name", items=[])
    await concept_set_service.create_concept_set(data1, test_user.id)

    # Try creating same name again
    data2 = ConceptSetCreate(name="Unique Name", items=[])

    with pytest.raises(DuplicateResourceError) as exc:
        await concept_set_service.create_concept_set(data2, test_user.id)

    assert "already exists" in str(exc.value)


@pytest.mark.asyncio
async def test_create_concept_set_duplicate_items(
    concept_set_service: ConceptSetService, test_user: User, sample_concepts: list[Concept]
) -> None:
    """
    Edge Case 3: Duplicate Concept IDs in the input list.
    Should raise ValidationError.
    """
    # Same ID twice
    item1 = ConceptSetItemCreate(concept_id=101, isExcluded=False, includeDescendants=False, includeMapped=False)
    item2 = ConceptSetItemCreate(concept_id=101, isExcluded=True, includeDescendants=False, includeMapped=False)

    data = ConceptSetCreate(name="Duplicate Items Set", items=[item1, item2])

    with pytest.raises(ValidationError) as exc:
        await concept_set_service.create_concept_set(data, test_user.id)

    assert "Duplicate concept IDs" in str(exc.value)


@pytest.mark.asyncio
async def test_create_empty_concept_set(concept_set_service: ConceptSetService, test_user: User) -> None:
    """
    Edge Case 4: Create a Concept Set with 0 items.
    """
    data = ConceptSetCreate(name="Empty Set", items=[])

    result = await concept_set_service.create_concept_set(data, test_user.id)

    assert result.concept_set_id is not None
    assert len(result.items) == 0


@pytest.mark.asyncio
async def test_create_concept_set_unicode_name(concept_set_service: ConceptSetService, test_user: User) -> None:
    """
    Edge Case 5: Special characters in name.
    """
    name = "Complex Name 🐍✨ - 'Test'"
    data = ConceptSetCreate(name=name, items=[])

    result = await concept_set_service.create_concept_set(data, test_user.id)

    assert result.concept_set_name == name


@pytest.mark.asyncio
async def test_get_concept_set(
    concept_set_service: ConceptSetService, test_user: User, sample_concepts: list[Concept]
) -> None:
    """
    Test Retrieval of Concept Set with population.
    """
    item1 = ConceptSetItemCreate(concept_id=101, isExcluded=False, includeDescendants=False, includeMapped=False)
    data = ConceptSetCreate(name="Retrieval Set", items=[item1])
    created = await concept_set_service.create_concept_set(data, test_user.id)

    # Fetch
    fetched = await concept_set_service.get_concept_set(created.concept_set_id)

    assert fetched.concept_set_id == created.concept_set_id
    assert len(fetched.items) == 1
    assert fetched.items[0].concept.concept_name == "Concept 101"


@pytest.mark.asyncio
async def test_get_concept_set_not_found(concept_set_service: ConceptSetService) -> None:
    """
    Test Retrieval of non-existent set.
    """
    with pytest.raises(ValidationError) as exc:
        await concept_set_service.get_concept_set(99999)

    assert "not found" in str(exc.value)
