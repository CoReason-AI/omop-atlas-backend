# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.concept_set import ConceptSet, ConceptSetItem
from omop_atlas_backend.models.security import User
from omop_atlas_backend.models.vocabulary import Concept


@pytest.mark.asyncio
async def test_concept_set_models(async_session: AsyncSession) -> None:
    """
    Test that ConceptSet and ConceptSetItem models can be instantiated and persisted.
    """
    # 1. Create a User (for CommonEntity fields)
    user = User(
        username="test_user",
        password_hash="hash",
        is_active=True
    )
    async_session.add(user)
    await async_session.flush()

    # 2. Create a Concept (for foreign key)
    concept = Concept(
        concept_id=12345,
        concept_name="Test Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        concept_code="C12345",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31)
    )
    async_session.add(concept)
    await async_session.flush()

    # 3. Create a ConceptSet
    concept_set = ConceptSet(
        concept_set_name="Test Concept Set",
        description="A test set",
        created_by_id=user.id,
        created_date=datetime.now(timezone.utc)
    )
    async_session.add(concept_set)
    await async_session.commit()

    # 4. Verify ConceptSet creation
    stmt = select(ConceptSet).where(ConceptSet.concept_set_name == "Test Concept Set")
    result = await async_session.execute(stmt)
    retrieved_cs = result.scalar_one()

    assert retrieved_cs.concept_set_id is not None
    assert retrieved_cs.description == "A test set"
    assert retrieved_cs.created_by_id == user.id

    # Test __repr__
    assert "ConceptSet" in repr(retrieved_cs)
    assert "Test Concept Set" in repr(retrieved_cs)

    # 5. Add a ConceptSetItem
    item = ConceptSetItem(
        concept_set_id=retrieved_cs.concept_set_id,
        concept_id=concept.concept_id,
        is_excluded=False,
        include_descendants=True,
        include_mapped=False
    )
    async_session.add(item)
    await async_session.commit()

    # 6. Verify Relationships
    # Reload ConceptSet to get items
    await async_session.refresh(retrieved_cs)

    # We used lazy="selectin" so items should be available
    assert len(retrieved_cs.items) == 1
    assert retrieved_cs.items[0].concept_id == 12345
    assert retrieved_cs.items[0].include_descendants is True

    # Check Concept relationship
    assert retrieved_cs.items[0].concept.concept_name == "Test Concept"

    # Check User relationship
    assert retrieved_cs.created_by.username == "test_user"

    # Test __repr__ for item
    assert "ConceptSetItem" in repr(retrieved_cs.items[0])
    assert "12345" in repr(retrieved_cs.items[0])
