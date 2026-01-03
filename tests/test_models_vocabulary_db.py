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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import (
    Concept,
    ConceptAncestor,
    ConceptClass,
    ConceptRelationship,
    Domain,
    Relationship,
    Vocabulary,
)


@pytest.fixture
def relationship_data() -> Relationship:
    return Relationship(
        relationship_id="Is a",
        relationship_name="Is a",
        is_hierarchical="1",
        defines_ancestry="1",
        reverse_relationship_id="Subsumes",
        relationship_concept_id=0,
    )


@pytest.mark.asyncio
async def test_relationship_creation(async_session: AsyncSession, relationship_data: Relationship) -> None:
    async_session.add(relationship_data)
    await async_session.commit()

    assert relationship_data.relationship_id == "Is a"


@pytest.mark.asyncio
async def test_concept_relationship_lifecycle(async_session: AsyncSession, relationship_data: Relationship) -> None:
    # Setup
    vocab = Vocabulary(vocabulary_id="SNOMED", vocabulary_name="SNOMED", vocabulary_concept_id=0)
    domain = Domain(domain_id="Condition", domain_name="Condition", domain_concept_id=0)
    c_class = ConceptClass(
        concept_class_id="Clinical Finding", concept_class_name="Clinical Finding", concept_class_concept_id=0
    )
    async_session.add_all([vocab, domain, c_class, relationship_data])
    await async_session.commit()

    c1 = Concept(
        concept_id=10,
        concept_name="C1",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="C1",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    c2 = Concept(
        concept_id=20,
        concept_name="C2",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="C2",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add_all([c1, c2])
    await async_session.commit()

    # Create Relationship
    cr = ConceptRelationship(
        concept_id_1=10,
        concept_id_2=20,
        relationship_id="Is a",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add(cr)
    await async_session.commit()

    # Verify
    assert cr.concept_1 == c1
    assert cr.concept_2 == c2
    assert cr.relationship_rel == relationship_data


@pytest.mark.asyncio
async def test_concept_ancestor_lifecycle(async_session: AsyncSession) -> None:
    # Setup
    vocab = Vocabulary(vocabulary_id="SNOMED", vocabulary_name="SNOMED", vocabulary_concept_id=0)
    domain = Domain(domain_id="Condition", domain_name="Condition", domain_concept_id=0)
    c_class = ConceptClass(
        concept_class_id="Clinical Finding", concept_class_name="Clinical Finding", concept_class_concept_id=0
    )
    async_session.add_all([vocab, domain, c_class])
    await async_session.commit()

    c1 = Concept(
        concept_id=100,
        concept_name="Ancestor",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="A",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    c2 = Concept(
        concept_id=200,
        concept_name="Descendant",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="D",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add_all([c1, c2])
    await async_session.commit()

    # Create Ancestor
    ca = ConceptAncestor(
        ancestor_concept_id=100,
        descendant_concept_id=200,
        min_levels_of_separation=1,
        max_levels_of_separation=5,
    )
    async_session.add(ca)
    await async_session.commit()

    # Verify
    assert ca.ancestor_concept == c1
    assert ca.descendant_concept == c2


@pytest.mark.asyncio
async def test_fk_constraint_concept_relationship(async_session: AsyncSession, relationship_data: Relationship) -> None:
    # Add relationship metadata
    async_session.add(relationship_data)
    await async_session.commit()

    # Try to add concept relationship with non-existent concepts
    cr = ConceptRelationship(
        concept_id_1=9999,
        concept_id_2=8888,
        relationship_id="Is a",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add(cr)

    with pytest.raises(IntegrityError):
        await async_session.commit()


@pytest.mark.asyncio
async def test_fk_constraint_concept_ancestor(async_session: AsyncSession) -> None:
    # Try to add concept ancestor with non-existent concepts
    ca = ConceptAncestor(
        ancestor_concept_id=9999,
        descendant_concept_id=8888,
        min_levels_of_separation=1,
        max_levels_of_separation=1,
    )
    async_session.add(ca)

    with pytest.raises(IntegrityError):
        await async_session.commit()


@pytest.mark.asyncio
async def test_duplicate_pk_concept_relationship(async_session: AsyncSession, relationship_data: Relationship) -> None:
    # Setup
    vocab = Vocabulary(vocabulary_id="SNOMED", vocabulary_name="SNOMED", vocabulary_concept_id=0)
    domain = Domain(domain_id="Condition", domain_name="Condition", domain_concept_id=0)
    c_class = ConceptClass(
        concept_class_id="Clinical Finding", concept_class_name="Clinical Finding", concept_class_concept_id=0
    )
    async_session.add_all([vocab, domain, c_class, relationship_data])
    await async_session.commit()

    c1 = Concept(
        concept_id=10,
        concept_name="C1",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="C1",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    c2 = Concept(
        concept_id=20,
        concept_name="C2",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="C2",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add_all([c1, c2])
    await async_session.commit()

    # Add first
    cr1 = ConceptRelationship(
        concept_id_1=10,
        concept_id_2=20,
        relationship_id="Is a",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add(cr1)
    await async_session.commit()

    # Add second (duplicate)
    cr2 = ConceptRelationship(
        concept_id_1=10,
        concept_id_2=20,
        relationship_id="Is a",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )
    async_session.add(cr2)

    with pytest.raises(IntegrityError):
        await async_session.commit()
