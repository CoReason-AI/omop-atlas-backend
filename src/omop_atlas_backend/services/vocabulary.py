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
Handles high-performance search and retrieval of OMOP Concepts.
"""

from typing import List, Optional

from redis.asyncio import Redis
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import Concept
from omop_atlas_backend.schemas.concept import Concept as ConceptSchema
from omop_atlas_backend.schemas.concept import ConceptSearch


class VocabularyService:
    """
    Service for Vocabulary operations: Searching and Retrieving Concepts.
    Includes Redis caching for high-performance single-concept lookups.
    """

    def __init__(self, db: AsyncSession, redis: Optional["Redis[str]"]):
        self.db = db
        self.redis = redis

    async def get_concept(self, concept_id: int) -> Optional[ConceptSchema]:
        """
        Get a concept by ID. First checks Redis cache, then DB.

        :param concept_id: The OMOP Concept ID.
        :return: ConceptSchema if found, else None.
        """
        cache_key = f"concept:{concept_id}"
        cached_data = None
        if self.redis:
            try:
                cached_data = await self.redis.get(cache_key)
            except Exception:
                # Fallback to DB if Redis fails
                pass

        if cached_data:
            return ConceptSchema.model_validate_json(cached_data)

        stmt = select(Concept).where(Concept.concept_id == concept_id)
        result = await self.db.execute(stmt)
        concept = result.scalar_one_or_none()

        if concept:
            schema = ConceptSchema.model_validate(concept)
            if self.redis:
                try:
                    await self.redis.set(cache_key, schema.model_dump_json(), ex=3600)  # Cache for 1 hour
                except Exception:
                    pass
            return schema

        return None

    async def search_concepts(self, search: ConceptSearch, limit: int = 20000, offset: int = 0) -> List[ConceptSchema]:
        """
        Search concepts based on criteria with pagination.
        Uses ILIKE for case-insensitive matching on Name and Code.

        :param search: ConceptSearch criteria (query, filters).
        :param limit: Max number of results (default 20,000).
        :param offset: Pagination offset.
        :return: List of ConceptSchema.
        """
        # Ensure limit and offset are positive
        limit = max(1, limit)
        offset = max(0, offset)

        stmt = select(Concept)

        # Basic text search (using ILIKE for case-insensitive search)
        # Note: For production, consider using Postgres Full Text Search (tsvector)
        # e.g., using search.query with websearch_to_tsquery or plainto_tsquery
        if search.query:
            # Check for Postgres dialect to use Full Text Search
            is_postgres = False
            try:
                if self.db.bind and self.db.bind.dialect.name == "postgresql":
                    is_postgres = True
            except Exception:
                pass  # Fallback if bind is not available or other error

            if is_postgres:
                # Optimized FTS for Postgres
                # Match name using FTS OR code using ILIKE
                stmt = stmt.where(
                    or_(
                        func.to_tsvector("english", Concept.concept_name).op("@@")(
                            func.websearch_to_tsquery("english", search.query)
                        ),
                        Concept.concept_code.ilike(f"%{search.query}%"),
                    )
                )
            else:
                # Fallback for SQLite/others
                query_str = f"%{search.query}%"
                stmt = stmt.where(or_(Concept.concept_name.ilike(query_str), Concept.concept_code.ilike(query_str)))

        # Filters
        if search.domain_id:
            stmt = stmt.where(Concept.domain_id.in_(search.domain_id))

        if search.vocabulary_id:
            stmt = stmt.where(Concept.vocabulary_id.in_(search.vocabulary_id))

        if search.concept_class_id:
            stmt = stmt.where(Concept.concept_class_id.in_(search.concept_class_id))

        if search.invalid_reason:
            if search.invalid_reason == "V":
                stmt = stmt.where(Concept.invalid_reason.is_(None))
            else:
                stmt = stmt.where(Concept.invalid_reason == search.invalid_reason)

        if search.standard_concept:
            if search.standard_concept == "N":
                stmt = stmt.where(Concept.standard_concept.is_(None))
            else:
                stmt = stmt.where(Concept.standard_concept == search.standard_concept)

        # Pagination
        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        concepts = result.scalars().all()

        return [ConceptSchema.model_validate(c) for c in concepts]
