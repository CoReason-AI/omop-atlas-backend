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
Handles CRUD logic for Concept Sets and Items.
Ensures validation of Concept IDs using VocabularyService.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from omop_atlas_backend.models.concept_set import ConceptSet as ConceptSetModel
from omop_atlas_backend.models.concept_set import ConceptSetItem as ConceptSetItemModel
from omop_atlas_backend.schemas.concept_set import ConceptSet as ConceptSetSchema
from omop_atlas_backend.schemas.concept_set import ConceptSetCreate, ConceptSetUpdate
from omop_atlas_backend.services.vocabulary import VocabularyService


class ConceptSetNotFound(Exception):
    def __init__(self, concept_set_id: int):
        self.concept_set_id = concept_set_id
        super().__init__(f"Concept Set with ID {concept_set_id} not found")


class ConceptSetService:
    def __init__(self, db: AsyncSession, vocabulary_service: VocabularyService):
        self.db = db
        self.vocab_service = vocabulary_service

    async def create_concept_set(self, data: ConceptSetCreate, user_id: int) -> ConceptSetSchema:
        """
        Creates a new Concept Set.
        Validates that all included concept IDs exist.
        """
        # 1. Extract concept IDs
        concept_ids = [item.concept_id for item in data.items]

        # 2. Validate concepts
        await self.vocab_service.validate_concepts(concept_ids)

        # 3. Create ConceptSet
        concept_set = ConceptSetModel(
            concept_set_name=data.concept_set_name,
            created_by_id=user_id,
        )
        self.db.add(concept_set)
        await self.db.flush()  # Get ID

        # 4. Create Items
        for item_data in data.items:
            item = ConceptSetItemModel(
                concept_set_id=concept_set.concept_set_id,
                concept_id=item_data.concept_id,
                is_excluded=item_data.is_excluded,
                include_descendants=item_data.include_descendants,
                include_mapped=item_data.include_mapped,
            )
            self.db.add(item)

        await self.db.commit()

        # 5. Reload with relationships for schema
        # We need to load items and items.concept
        return await self.get_concept_set(concept_set.concept_set_id)

    async def get_concept_set(self, concept_set_id: int) -> ConceptSetSchema:
        """
        Retrieves a Concept Set by ID, including its items and their concepts.
        """
        query = (
            select(ConceptSetModel)
            .where(ConceptSetModel.concept_set_id == concept_set_id)
            .options(
                selectinload(ConceptSetModel.items).selectinload(ConceptSetItemModel.concept),
            )
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(query)
        concept_set = result.scalars().first()

        if not concept_set:
            raise ConceptSetNotFound(concept_set_id)

        return ConceptSetSchema.model_validate(concept_set)

    async def update_concept_set(
        self, concept_set_id: int, data: ConceptSetUpdate
    ) -> ConceptSetSchema:
        """
        Updates a Concept Set.
        If items are provided, replaces ALL existing items (full update strategy for items).
        """
        # Check existence
        query = select(ConceptSetModel).where(ConceptSetModel.concept_set_id == concept_set_id)
        result = await self.db.execute(query)
        concept_set = result.scalars().first()

        if not concept_set:
            raise ConceptSetNotFound(concept_set_id)

        # Update name
        if data.concept_set_name is not None:
            concept_set.concept_set_name = data.concept_set_name

        # Update items
        if data.items is not None:
            # Validate new concepts
            concept_ids = [item.concept_id for item in data.items]
            await self.vocab_service.validate_concepts(concept_ids)

            # Delete existing items
            from sqlalchemy import delete
            await self.db.execute(
                delete(ConceptSetItemModel).where(ConceptSetItemModel.concept_set_id == concept_set_id)
            )

            # Add new items
            for item_data in data.items:
                item = ConceptSetItemModel(
                    concept_set_id=concept_set_id,
                    concept_id=item_data.concept_id,
                    is_excluded=item_data.is_excluded,
                    include_descendants=item_data.include_descendants,
                    include_mapped=item_data.include_mapped,
                )
                self.db.add(item)

        await self.db.commit()
        return await self.get_concept_set(concept_set_id)

    async def delete_concept_set(self, concept_set_id: int) -> None:
        """
        Deletes a Concept Set.
        """
        query = select(ConceptSetModel).where(ConceptSetModel.concept_set_id == concept_set_id)
        result = await self.db.execute(query)
        concept_set = result.scalars().first()

        if not concept_set:
            raise ConceptSetNotFound(concept_set_id)

        await self.db.delete(concept_set)
        await self.db.commit()
