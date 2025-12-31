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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.concept_set import ConceptSet, ConceptSetItem


@pytest.mark.asyncio
async def test_create_concept_set(async_session: AsyncSession) -> None:
    cs = ConceptSet(
        concept_set_name="Test Concept Set",
        created_by="user1",
    )
    async_session.add(cs)
    await async_session.commit()

    assert cs.concept_set_id is not None
    assert cs.created_date is not None
    assert cs.modified_date is not None
    assert cs.concept_set_name == "Test Concept Set"


@pytest.mark.asyncio
async def test_create_concept_set_with_items(async_session: AsyncSession) -> None:
    cs = ConceptSet(
        concept_set_name="Concept Set with Items",
        created_by="user1",
    )
    item1 = ConceptSetItem(concept_id=123, is_excluded=False, include_descendants=True, include_mapped=False)
    item2 = ConceptSetItem(concept_id=456, is_excluded=True, include_descendants=False, include_mapped=False)
    cs.items.append(item1)
    cs.items.append(item2)

    async_session.add(cs)
    await async_session.commit()

    # Re-fetch
    result = await async_session.execute(select(ConceptSet).where(ConceptSet.concept_set_id == cs.concept_set_id))
    fetched_cs = result.scalar_one()

    assert len(fetched_cs.items) == 2
    ids = {item.concept_id for item in fetched_cs.items}
    assert 123 in ids
    assert 456 in ids


@pytest.mark.asyncio
async def test_concept_set_cascade_delete(async_session: AsyncSession) -> None:
    cs = ConceptSet(concept_set_name="Delete Me")
    item = ConceptSetItem(concept_id=999)
    cs.items.append(item)
    async_session.add(cs)
    await async_session.commit()

    item_id = item.concept_set_item_id

    # Delete parent
    await async_session.delete(cs)
    await async_session.commit()

    # Verify items are gone
    result = await async_session.execute(select(ConceptSetItem).where(ConceptSetItem.concept_set_item_id == item_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_concept_set_item_orphan_delete(async_session: AsyncSession) -> None:
    """Test that removing an item from the list deletes it from DB (orphan removal)."""
    cs = ConceptSet(concept_set_name="Orphan Test")
    item1 = ConceptSetItem(concept_id=111)
    item2 = ConceptSetItem(concept_id=222)
    cs.items.extend([item1, item2])
    async_session.add(cs)
    await async_session.commit()

    item1_id = item1.concept_set_item_id
    item2_id = item2.concept_set_item_id

    # Remove item1 from list
    cs.items.remove(item1)
    async_session.add(cs)
    await async_session.commit()

    # Verify item1 is gone from DB
    result1 = await async_session.execute(select(ConceptSetItem).where(ConceptSetItem.concept_set_item_id == item1_id))
    assert result1.scalar_one_or_none() is None

    # Verify item2 is still there
    result2 = await async_session.execute(select(ConceptSetItem).where(ConceptSetItem.concept_set_item_id == item2_id))
    assert result2.scalar_one_or_none() is not None
