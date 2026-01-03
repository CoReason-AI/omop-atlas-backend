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
from typing import List

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import Concept, ConceptClass, Domain, Vocabulary
from omop_atlas_backend.schemas.concept_set import (
    ConceptSetCreate,
    ConceptSetItemCreate,
    ConceptSetUpdate,
)
from omop_atlas_backend.services.concept_set import ConceptSetNotFound, ConceptSetService
from omop_atlas_backend.services.exceptions import ConceptNotFound
from omop_atlas_backend.services.vocabulary import VocabularyService


@pytest_asyncio.fixture
async def vocabulary_service(async_session: AsyncSession) -> VocabularyService:
    return VocabularyService(async_session)


@pytest_asyncio.fixture
async def concept_set_service(
    async_session: AsyncSession, vocabulary_service: VocabularyService
) -> ConceptSetService:
    return ConceptSetService(async_session, vocabulary_service)


@pytest_asyncio.fixture
async def seed_concepts(async_session: AsyncSession) -> List[int]:
    vocab = Vocabulary(
        vocabulary_id="RxNorm", vocabulary_name="RxNorm", vocabulary_concept_id=1
    )
    domain = Domain(domain_id="Drug", domain_name="Drug", domain_concept_id=1)
    c_class = ConceptClass(
        concept_class_id="Ingredient",
        concept_class_name="Ingredient",
        concept_class_concept_id=1,
    )

    async_session.add_all([vocab, domain, c_class])
    await async_session.flush()

    c1 = Concept(
        concept_id=1001,
        concept_name="Aspirin",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Ingredient",
        concept_code="1001",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    c2 = Concept(
        concept_id=1002,
        concept_name="Tylenol",
        domain_id="Drug",
        vocabulary_id="RxNorm",
        concept_class_id="Ingredient",
        concept_code="1002",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add_all([c1, c2])
    await async_session.commit()
    return [1001, 1002]


@pytest.mark.asyncio
async def test_validate_concepts(
    vocabulary_service: VocabularyService, seed_concepts: List[int]
) -> None:
    await vocabulary_service.validate_concepts([1001, 1002])

    with pytest.raises(ConceptNotFound) as exc:
        await vocabulary_service.validate_concepts([1001, 9999])
    assert exc.value.concept_id == 9999


@pytest.mark.asyncio
async def test_create_concept_set(
    concept_set_service: ConceptSetService, seed_concepts: List[int]
) -> None:
    data = ConceptSetCreate(
        concept_set_name="Test Set",  # type: ignore
        items=[
            ConceptSetItemCreate(concept_id=1001, isExcluded=True),  # type: ignore
            ConceptSetItemCreate(concept_id=1002),  # type: ignore
        ],
    )

    from omop_atlas_backend.models.security import User

    user = User(username="testuser", email="test@example.com", password_hash="hash")
    concept_set_service.db.add(user)
    await concept_set_service.db.commit()
    user_id = user.id

    cs = await concept_set_service.create_concept_set(data, user_id)

    assert cs.concept_set_id is not None
    assert cs.concept_set_name == "Test Set"
    assert len(cs.items) == 2
    assert cs.items[0].concept_id == 1001
    assert cs.items[0].is_excluded is True
    assert cs.items[0].concept is not None
    assert cs.items[0].concept.concept_name == "Aspirin"


@pytest.mark.asyncio
async def test_create_concept_set_invalid_concept(
    concept_set_service: ConceptSetService, seed_concepts: List[int]
) -> None:
    from omop_atlas_backend.models.security import User

    user = User(username="testuser2", email="test2@example.com", password_hash="hash")
    concept_set_service.db.add(user)
    await concept_set_service.db.commit()

    data = ConceptSetCreate(
        concept_set_name="Invalid Set",  # type: ignore
        items=[ConceptSetItemCreate(concept_id=9999)],  # type: ignore
    )

    with pytest.raises(ConceptNotFound):
        await concept_set_service.create_concept_set(data, user.id)


@pytest.mark.asyncio
async def test_update_concept_set(
    concept_set_service: ConceptSetService, seed_concepts: List[int]
) -> None:
    from omop_atlas_backend.models.security import User

    user = User(username="testuser3", email="test3@example.com", password_hash="hash")
    concept_set_service.db.add(user)
    await concept_set_service.db.commit()

    create_data = ConceptSetCreate(
        concept_set_name="Original Name",  # type: ignore
        items=[ConceptSetItemCreate(concept_id=1001)],  # type: ignore
    )
    cs = await concept_set_service.create_concept_set(create_data, user.id)

    update_data = ConceptSetUpdate(
        concept_set_name="Updated Name",  # type: ignore
        items=[ConceptSetItemCreate(concept_id=1002)],  # type: ignore
    )
    updated_cs = await concept_set_service.update_concept_set(
        cs.concept_set_id, update_data
    )

    assert updated_cs.concept_set_name == "Updated Name"
    assert len(updated_cs.items) == 1
    assert updated_cs.items[0].concept_id == 1002


@pytest.mark.asyncio
async def test_delete_concept_set(
    concept_set_service: ConceptSetService, seed_concepts: List[int]
) -> None:
    from omop_atlas_backend.models.security import User

    user = User(username="testuser4", email="test4@example.com", password_hash="hash")
    concept_set_service.db.add(user)
    await concept_set_service.db.commit()

    create_data = ConceptSetCreate(concept_set_name="To Delete", items=[])  # type: ignore
    cs = await concept_set_service.create_concept_set(create_data, user.id)

    await concept_set_service.delete_concept_set(cs.concept_set_id)

    with pytest.raises(ConceptSetNotFound):
        await concept_set_service.get_concept_set(cs.concept_set_id)


@pytest.mark.asyncio
async def test_update_non_existent_concept_set(
    concept_set_service: ConceptSetService,
) -> None:
    update_data = ConceptSetUpdate(concept_set_name="New Name")  # type: ignore
    with pytest.raises(ConceptSetNotFound):
        await concept_set_service.update_concept_set(9999, update_data)


@pytest.mark.asyncio
async def test_delete_non_existent_concept_set(
    concept_set_service: ConceptSetService,
) -> None:
    with pytest.raises(ConceptSetNotFound):
        await concept_set_service.delete_concept_set(9999)
