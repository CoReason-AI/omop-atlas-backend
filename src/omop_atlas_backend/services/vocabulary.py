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
Phase 2: Vocabulary Engine - Service
Handles logic for searching and retrieving concepts.
Implements Rule #1 (Read-Only Vocabulary Optimization) and Redis caching.
"""

from typing import List, Optional

from redis.asyncio import Redis
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import Concept as ConceptModel
from omop_atlas_backend.schemas.concept import Concept as ConceptSchema
from omop_atlas_backend.schemas.concept import ConceptSearch
from omop_atlas_backend.services.exceptions import ConceptNotFound


class VocabularyService:
    """
    Service for Vocabulary operations.
    """

    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):
        self.db = db
        self.redis = redis

    async def get_concept_by_id(self, concept_id: int) -> ConceptSchema:
        """
        Retrieves a single concept by ID.
        """
        cache_key = f"concept:{concept_id}"

        # Try Redis first
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    return ConceptSchema.model_validate_json(cached)
            except Exception:
                # Log error but fall back to DB
                pass

        query = select(ConceptModel).where(ConceptModel.concept_id == concept_id)
        result = await self.db.execute(query)
        concept = result.scalars().first()

        if not concept:
            raise ConceptNotFound(concept_id)

        # Validate and Serialize
        concept_schema = ConceptSchema.model_validate(concept)

        # Cache in Redis
        if self.redis:
            try:
                # Expire in 1 hour (3600 seconds)
                await self.redis.set(cache_key, concept_schema.model_dump_json(), ex=3600)
            except Exception:
                # Log error but continue
                pass

        return concept_schema

    async def search_concepts(
        self,
        search: ConceptSearch,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ConceptSchema]:
        """
        Searches for concepts using optimized SQL queries (Full Text Search) and standard filters.
        """
        stmt = select(ConceptModel)

        if search.query:
            # FTS on name OR ILIKE on code
            # Note: We assume Postgres for FTS optimization as per requirements.

            fts_condition = func.to_tsvector("english", ConceptModel.concept_name).op("@@")(
                func.plainto_tsquery("english", search.query)
            )
            code_condition = ConceptModel.concept_code.ilike(f"%{search.query}%")

            stmt = stmt.where(or_(fts_condition, code_condition))

        if search.vocabulary_id:
            stmt = stmt.where(ConceptModel.vocabulary_id.in_(search.vocabulary_id))

        if search.domain_id:
            stmt = stmt.where(ConceptModel.domain_id.in_(search.domain_id))

        if search.concept_class_id:
            stmt = stmt.where(ConceptModel.concept_class_id.in_(search.concept_class_id))

        if search.standard_concept:
            # OMOP Convention: 'N' (Non-standard) often maps to NULL in standard_concept column
            if search.standard_concept == "N":
                stmt = stmt.where(ConceptModel.standard_concept.is_(None))
            else:
                stmt = stmt.where(ConceptModel.standard_concept == search.standard_concept)

        if search.invalid_reason:
            # OMOP Convention: 'V' (Valid) maps to NULL in invalid_reason column
            if search.invalid_reason == "V":
                stmt = stmt.where(ConceptModel.invalid_reason.is_(None))
            else:
                stmt = stmt.where(ConceptModel.invalid_reason == search.invalid_reason)

        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)

        # Return Schemas instead of Models
        return [ConceptSchema.model_validate(c) for c in result.scalars().all()]
