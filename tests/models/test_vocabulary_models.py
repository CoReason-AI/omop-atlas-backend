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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import Concept, Vocabulary


@pytest.mark.asyncio
async def test_vocabulary_models(async_session: AsyncSession) -> None:
    """Test that Vocabulary models can be instantiated and persisted (read-only context)."""
    # Create a vocabulary
    vocab = Vocabulary(
        vocabulary_id="TEST_VOCAB",
        vocabulary_name="Test Vocabulary",
        vocabulary_reference="Ref",
        vocabulary_version="v1",
        vocabulary_concept_id=0,
    )
    async_session.add(vocab)

    # Create a concept
    concept = Concept(
        concept_id=1,
        concept_name="Test Concept",
        domain_id="Test",
        vocabulary_id="TEST_VOCAB",
        concept_class_id="Class",
        concept_code="CODE",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None,
    )
    async_session.add(concept)
    await async_session.commit()

    # Query back
    stmt = select(Concept).where(Concept.concept_id == 1)
    result = await async_session.execute(stmt)
    retrieved = result.scalar_one()

    assert retrieved.concept_name == "Test Concept"
    assert retrieved.vocabulary_id == "TEST_VOCAB"
    assert retrieved.valid_start_date == date(2020, 1, 1)
