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
Implements Atomic Unit 2 (Create/Read) with strict validation.
"""

from typing import Set

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from omop_atlas_backend.models.concept_set import ConceptSet, ConceptSetItem
from omop_atlas_backend.models.vocabulary import Concept
from omop_atlas_backend.schemas.concept_set import ConceptSetCreate
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

    async def create_concept_set(self, data: ConceptSetCreate, user_id: int) -> ConceptSet:
        """
        Creates a new Concept Set.

        Validation Rules:
        1. Concept Set Name must be unique.
        2. All Concept IDs in items must exist in the Vocabulary.
        3. No duplicate Concept IDs allowed within the same Concept Set.
        """
        # Rule 3: Check for duplicate concept_ids in input
        concept_ids_in_input = [item.concept_id for item in data.items]
        if len(concept_ids_in_input) != len(set(concept_ids_in_input)):
            raise ValidationError("Duplicate concept IDs found in the items list.")

        # Rule 2: Validate all concepts exist
        if concept_ids_in_input:
            stmt = select(Concept.concept_id).where(Concept.concept_id.in_(concept_ids_in_input))
            result = await self.db.execute(stmt)
            existing_ids: Set[int] = set(result.scalars().all())

            missing_ids = set(concept_ids_in_input) - existing_ids
            if missing_ids:
                raise ConceptNotFound(f"Concepts not found: {missing_ids}")

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
            raise ValidationError(
                f"Concept Set with ID {concept_set_id} not found."
            )  # Using ValidationError as a generic Not Found for now or define ResourceNotFound

        return concept_set
