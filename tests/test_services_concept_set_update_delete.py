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
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.security import User
from omop_atlas_backend.models.vocabulary import Concept, ConceptClass, Domain, Vocabulary
from omop_atlas_backend.schemas.concept_set import ConceptSetCreate, ConceptSetItemCreate, ConceptSetUpdate
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
    user = User(username="test_user_cs_ud", password_hash="hash")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_concepts(async_session: AsyncSession) -> list[Concept]:
    # Create dependencies
    d1 = Domain(domain_id="Condition", domain_name="Condition", domain_concept_id=0)
    v1 = Vocabulary(vocabulary_id="SNOMED", vocabulary_name="SNOMED", vocabulary_concept_id=0)
    cc1 = ConceptClass(
        concept_class_id="Clinical Finding", concept_class_name="Clinical Finding", concept_class_concept_id=0
    )
    async_session.add_all([d1, v1, cc1])
    await async_session.commit()

    c1 = Concept(
        concept_id=201,
        concept_name="C201",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="C201",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    c2 = Concept(
        concept_id=202,
        concept_name="C202",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="C202",
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
async def test_update_concept_set_name(
    concept_set_service: ConceptSetService, test_user: User, sample_concepts: list[Concept]
) -> None:
    """
    Test 1: Successful update of Name only.
    """
    # Create
    item = ConceptSetItemCreate(concept_id=201, isExcluded=False, includeDescendants=False, includeMapped=False)
    create_data = ConceptSetCreate(name="Original Name", items=[item])
    cs = await concept_set_service.create_concept_set(create_data, test_user.id)

    # Update Name
    update_data = ConceptSetUpdate(name="Updated Name", items=None)
    updated_cs = await concept_set_service.update_concept_set(cs.concept_set_id, update_data)

    assert updated_cs.concept_set_name == "Updated Name"
    # Ensure items are untouched
    assert len(updated_cs.items) == 1
    assert updated_cs.items[0].concept_id == 201


@pytest.mark.asyncio
async def test_update_concept_set_items_replace(
    concept_set_service: ConceptSetService, test_user: User, sample_concepts: list[Concept]
) -> None:
    """
    Test 2/3: Successful update of Items (Replacement)
    """
    # Create with C201
    item1 = ConceptSetItemCreate(concept_id=201, isExcluded=False, includeDescendants=False, includeMapped=False)
    create_data = ConceptSetCreate(name="Item Update Set", items=[item1])
    cs = await concept_set_service.create_concept_set(create_data, test_user.id)

    # Update to C202 (Replace)
    item2 = ConceptSetItemCreate(concept_id=202, isExcluded=True, includeDescendants=True, includeMapped=False)
    update_data = ConceptSetUpdate(name="Item Update Set", items=[item2])

    updated_cs = await concept_set_service.update_concept_set(cs.concept_set_id, update_data)

    assert len(updated_cs.items) == 1
    assert updated_cs.items[0].concept_id == 202
    assert updated_cs.items[0].is_excluded is True


@pytest.mark.asyncio
async def test_update_concept_set_duplicate_name(
    concept_set_service: ConceptSetService, test_user: User, sample_concepts: list[Concept]
) -> None:
    """
    Test 4: Update to a name that already exists.
    """
    # Create two sets
    await concept_set_service.create_concept_set(ConceptSetCreate(name="Set A", items=[]), test_user.id)
    cs2 = await concept_set_service.create_concept_set(ConceptSetCreate(name="Set B", items=[]), test_user.id)

    # Try updating B to A
    update_data = ConceptSetUpdate(name="Set A", items=None)

    with pytest.raises(DuplicateResourceError) as exc:
        await concept_set_service.update_concept_set(cs2.concept_set_id, update_data)

    assert "already exists" in str(exc.value)


@pytest.mark.asyncio
async def test_update_items_non_existent_concept(
    concept_set_service: ConceptSetService, test_user: User, sample_concepts: list[Concept]
) -> None:
    """
    Test 5: Update items with non-existent Concept ID.
    """
    cs = await concept_set_service.create_concept_set(ConceptSetCreate(name="Valid Set", items=[]), test_user.id)

    item_bad = ConceptSetItemCreate(concept_id=999, isExcluded=False, includeDescendants=False, includeMapped=False)
    update_data = ConceptSetUpdate(name="Valid Set", items=[item_bad])

    with pytest.raises(ConceptNotFound) as exc:
        await concept_set_service.update_concept_set(cs.concept_set_id, update_data)

    assert "999" in str(exc.value)


@pytest.mark.asyncio
async def test_update_items_duplicate_concepts(
    concept_set_service: ConceptSetService, test_user: User, sample_concepts: list[Concept]
) -> None:
    """
    Test 6: Update items with duplicate IDs.
    """
    cs = await concept_set_service.create_concept_set(ConceptSetCreate(name="Unique Set", items=[]), test_user.id)

    item = ConceptSetItemCreate(concept_id=201, isExcluded=False, includeDescendants=False, includeMapped=False)
    update_data = ConceptSetUpdate(name="Unique Set", items=[item, item])

    with pytest.raises(ValidationError) as exc:
        await concept_set_service.update_concept_set(cs.concept_set_id, update_data)

    assert "Duplicate concept IDs" in str(exc.value)


@pytest.mark.asyncio
async def test_delete_concept_set(
    concept_set_service: ConceptSetService, test_user: User, sample_concepts: list[Concept]
) -> None:
    """
    Test 8: Successful Delete.
    """
    cs = await concept_set_service.create_concept_set(ConceptSetCreate(name="To Delete", items=[]), test_user.id)
    id_to_delete = cs.concept_set_id

    await concept_set_service.delete_concept_set(id_to_delete)

    # Verify it's gone
    with pytest.raises(ValidationError) as exc:
        await concept_set_service.get_concept_set(id_to_delete)

    assert "not found" in str(exc.value)


@pytest.mark.asyncio
async def test_delete_non_existent_concept_set(concept_set_service: ConceptSetService) -> None:
    """
    Test 9: Delete non-existent ID.
    """
    with pytest.raises(ValidationError) as exc:
        await concept_set_service.delete_concept_set(99999)

    assert "not found" in str(exc.value)


@pytest.mark.asyncio
async def test_update_non_existent_concept_set(concept_set_service: ConceptSetService) -> None:
    """
    Test 7: Update non-existent ID.
    """
    update_data = ConceptSetUpdate(name="Ghost", items=None)
    with pytest.raises(ValidationError) as exc:
        await concept_set_service.update_concept_set(99999, update_data)

    assert "not found" in str(exc.value)
