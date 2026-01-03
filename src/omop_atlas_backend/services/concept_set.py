# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

"""
Phase 3: Concept Sets - Service
Handles logic for creating, retrieving, updating, and deleting Concept Sets.
Implements Atomic Unit 2 (Create/Read) and Unit 3 (Update/Delete).
"""

from typing import List, Set

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from omop_atlas_backend.models.concept_set import ConceptSet, ConceptSetItem
from omop_atlas_backend.models.vocabulary import Concept
from omop_atlas_backend.schemas.concept_set import ConceptSetCreate, ConceptSetItemCreate, ConceptSetUpdate
from omop_atlas_backend.services.exceptions import (
    ConceptNotFound,
    DuplicateResourceError,
    ValidationError,
)


class ConceptSetService:
    """
    Service for Concept Set operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _validate_items(self, items: List[ConceptSetItemCreate]) -> None:
        """
        Validates a list of concept set items.
        Checks for duplicate concept IDs in the input and existence in the database.
        """
        # Rule: Check for duplicate concept_ids in input
        concept_ids_in_input = [item.concept_id for item in items]
        if len(concept_ids_in_input) != len(set(concept_ids_in_input)):
            raise ValidationError("Duplicate concept IDs found in the items list.")

        # Rule: Validate all concepts exist
        if concept_ids_in_input:
            stmt = select(Concept.concept_id).where(Concept.concept_id.in_(concept_ids_in_input))
            result = await self.db.execute(stmt)
            existing_ids: Set[int] = set(result.scalars().all())

            missing_ids = set(concept_ids_in_input) - existing_ids
            if missing_ids:
                raise ConceptNotFound(f"Concepts not found: {missing_ids}")

    async def create_concept_set(self, data: ConceptSetCreate, user_id: int) -> ConceptSet:
        """
        Creates a new Concept Set.
        """
        await self._validate_items(data.items)

        # Create Concept Set Entity
        new_concept_set = ConceptSet(concept_set_name=data.name, created_by_id=user_id)
        self.db.add(new_concept_set)

        try:
            # Flush to get the ID (and check name uniqueness early)
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            if "concept_set_name" in str(e) or "UNIQUE constraint failed" in str(e):
                raise DuplicateResourceError(f"Concept Set with name '{data.name}' already exists.") from e
            raise e

        # Create Items
        for item_data in data.items:
            item = ConceptSetItem(
                concept_set_id=new_concept_set.concept_set_id,
                concept_id=item_data.concept_id,
                is_excluded=item_data.is_excluded,
                include_descendants=item_data.include_descendants,
                include_mapped=item_data.include_mapped,
            )
            self.db.add(item)

        await self.db.commit()
        await self.db.refresh(new_concept_set, attribute_names=["items"])

        return new_concept_set

    async def get_concept_set(self, concept_set_id: int) -> ConceptSet:
        """
        Retrieves a Concept Set by ID, including its items and resolved concepts.
        """
        stmt = (
            select(ConceptSet)
            .where(ConceptSet.concept_set_id == concept_set_id)
            .options(selectinload(ConceptSet.items).selectinload(ConceptSetItem.concept))
            .execution_options(populate_existing=True)
        )

        result = await self.db.execute(stmt)
        concept_set = result.scalars().first()

        if not concept_set:
            raise ValidationError(f"Concept Set with ID {concept_set_id} not found.")

        return concept_set

    async def update_concept_set(self, concept_set_id: int, data: ConceptSetUpdate) -> ConceptSet:
        """
        Updates a Concept Set.
        Handles renaming and item replacement.
        """
        # Fetch existing
        concept_set = await self.get_concept_set(concept_set_id)

        # Update Name
        if data.name and data.name != concept_set.concept_set_name:
            concept_set.concept_set_name = data.name
            try:
                await self.db.flush()
            except IntegrityError as e:
                await self.db.rollback()
                if "concept_set_name" in str(e) or "UNIQUE constraint failed" in str(e):
                    raise DuplicateResourceError(f"Concept Set with name '{data.name}' already exists.") from e
                raise e

        # Update Items (if provided)
        if data.items is not None:
            await self._validate_items(data.items)

            # Clear existing items (SQLAlchemy will handle DELETEs due to orphan handling config if strictly mapped,
            # but explicit clear is safer here)
            concept_set.items.clear()

            # Add new items
            for item_data in data.items:
                item = ConceptSetItem(
                    concept_set_id=concept_set.concept_set_id,
                    concept_id=item_data.concept_id,
                    is_excluded=item_data.is_excluded,
                    include_descendants=item_data.include_descendants,
                    include_mapped=item_data.include_mapped,
                )
                self.db.add(item)  # Explicit add to session, though appending to relationship usually works

        await self.db.commit()
        await self.db.refresh(concept_set, attribute_names=["items"])
        return concept_set

    async def delete_concept_set(self, concept_set_id: int) -> None:
        """
        Deletes a Concept Set.
        """
        concept_set = await self.get_concept_set(concept_set_id)
        await self.db.delete(concept_set)
        await self.db.commit()
