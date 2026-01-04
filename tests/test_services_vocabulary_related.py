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

from omop_atlas_backend.models.vocabulary import (
    Concept,
    ConceptAncestor,
    ConceptClass,
    ConceptRelationship,
    Domain,
    Relationship,
    Vocabulary,
)
from omop_atlas_backend.services.vocabulary import VocabularyService

# Reuse async_session from conftest.py (assumed to be available via pytest plugins/conftest resolution)


@pytest_asyncio.fixture
async def vocabulary_service(async_session: AsyncSession) -> VocabularyService:
    return VocabularyService(async_session, redis=None)


@pytest_asyncio.fixture
async def seed_data(async_session: AsyncSession) -> Concept:
    # 1. Create dependencies
    vocab = Vocabulary(vocabulary_id="SNOMED", vocabulary_name="SNOMED", vocabulary_concept_id=0)
    domain = Domain(domain_id="Condition", domain_name="Condition", domain_concept_id=0)
    c_class = ConceptClass(
        concept_class_id="Clinical Finding", concept_class_name="Clinical Finding", concept_class_concept_id=0
    )

    # Relationships
    rel_mapped = Relationship(
        relationship_id="Mapped from",
        relationship_name="Mapped from",
        is_hierarchical="0",
        defines_ancestry="0",
        reverse_relationship_id="Mapped to",
        relationship_concept_id=0,
    )

    async_session.add_all([vocab, domain, c_class, rel_mapped])
    await async_session.commit()

    # 2. Create Concepts
    # Concept 1 (Target)
    c1 = Concept(
        concept_id=1,
        concept_name="Target Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="100",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )

    # Concept 2 (Directly Related)
    c2 = Concept(
        concept_id=2,
        concept_name="Related Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="200",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )

    # Concept 3 (Ancestor)
    c3 = Concept(
        concept_id=3,
        concept_name="Ancestor Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="300",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )

    # Concept 4 (Descendant)
    c4 = Concept(
        concept_id=4,
        concept_name="Descendant Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="400",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )

    async_session.add_all([c1, c2, c3, c4])
    await async_session.commit()

    # 3. Create Relationships
    # c1 -> c2 (Direct)
    cr = ConceptRelationship(
        concept_id_1=1,
        concept_id_2=2,
        relationship_id="Mapped from",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )

    # c3 -> c1 (Ancestor)
    ca1 = ConceptAncestor(
        ancestor_concept_id=3,
        descendant_concept_id=1,
        min_levels_of_separation=1,
        max_levels_of_separation=1,
    )

    # c1 -> c4 (Descendant: c1 is ancestor of c4)
    ca2 = ConceptAncestor(
        ancestor_concept_id=1,
        descendant_concept_id=4,
        min_levels_of_separation=1,
        max_levels_of_separation=1,
    )

    async_session.add_all([cr, ca1, ca2])
    await async_session.commit()
    return c1


@pytest.mark.asyncio
async def test_get_related_concepts(vocabulary_service: VocabularyService, seed_data: Concept) -> None:
    # Execute
    related = await vocabulary_service.get_related_concepts(1)

    # Assert
    assert len(related) == 3

    # Check for Direct Relationship (c2)
    rel_c2 = next((r for r in related if r.concept_id == 2), None)
    assert rel_c2 is not None
    assert len(rel_c2.relationships) == 1
    assert rel_c2.relationships[0].relationship_name == "Mapped from"
    assert rel_c2.relationships[0].relationship_distance == 0

    # Check for Ancestor (c3)
    rel_c3 = next((r for r in related if r.concept_id == 3), None)
    assert rel_c3 is not None
    assert len(rel_c3.relationships) == 1
    assert rel_c3.relationships[0].relationship_name == "Ancestor"
    assert rel_c3.relationships[0].relationship_distance == 1

    # Check for Descendant (c4)
    rel_c4 = next((r for r in related if r.concept_id == 4), None)
    assert rel_c4 is not None
    assert len(rel_c4.relationships) == 1
    assert rel_c4.relationships[0].relationship_name == "Descendant"
    assert rel_c4.relationships[0].relationship_distance == 1
