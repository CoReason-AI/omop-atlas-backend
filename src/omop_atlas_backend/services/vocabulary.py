# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

import json
from typing import List, Optional

from redis.asyncio import Redis
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import Concept
from omop_atlas_backend.schemas.concept import ConceptSearch, Concept as ConceptSchema


class VocabularyService:
    """
    Service for accessing OMOP Vocabulary data.
    Implements optimized search and Redis caching for concept lookups.
    """

    def __init__(self, session: AsyncSession, redis_client: Optional[Redis] = None):
        self.session = session
        self.redis = redis_client
        self.cache_ttl = 86400  # 24 hours

    async def get_concept(self, concept_id: int) -> Optional[Concept]:
        """
        Retrieve a concept by ID, using Redis cache if available.

        Args:
            concept_id: The ID of the concept to retrieve.

        Returns:
            The Concept model if found, None otherwise.
        """
        cache_key = f"concept:{concept_id}"

        # Try cache first
        if self.redis:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                # Deserialize from JSON to Concept schema, then to Model if needed
                # However, for read-only purposes, returning the Model is typical for services.
                # But since we cache JSON, we might need to reconstruct the object.
                # Let's reconstruct a transient Concept object.
                data = json.loads(cached_data)
                # Using Pydantic to parse, then we can convert to SQLAlchemy model or return Pydantic.
                # The service usually returns Models or Schemas.
                # Given the method signature returns Optional[Concept] (SQLAlchemy model),
                # we should try to return that.
                # For simplicity in this atomic unit, let's reconstruct the minimal Concept.
                # Or better, let's just return the object found in DB.
                # Wait, if we return a transient SQLAlchemy object it might not work well if attached to session is expected.
                # But for read-only it is fine.
                # Let's map dictionary to Concept.
                return Concept(**data)

        # Cache miss, query DB
        stmt = select(Concept).where(Concept.concept_id == concept_id)
        result = await self.session.execute(stmt)
        concept = result.scalar_one_or_none()

        # Update cache
        if concept and self.redis:
            # Serialize using Pydantic Schema for consistency
            schema = ConceptSchema.model_validate(concept)
            # Use by_alias=False (snake_case) for easy reconstruction in Python
            await self.redis.set(
                cache_key,
                schema.model_dump_json(by_alias=False),
                ex=self.cache_ttl
            )

        return concept

    async def search_concepts(self, search: ConceptSearch, limit: int = 100) -> List[Concept]:
        """
        Search for concepts based on criteria.

        Args:
            search: ConceptSearch parameters.
            limit: Maximum number of results.

        Returns:
            List of matching Concept models.
        """
        stmt = select(Concept)

        # Filter by Query (Name or Code)
        if search.query:
            query_str = f"%{search.query}%"
            # Using ILIKE for case-insensitive search
            stmt = stmt.where(
                or_(
                    Concept.concept_name.ilike(query_str),
                    Concept.concept_code.ilike(query_str)
                )
            )

        # Filter by Domain
        if search.domain_id:
            stmt = stmt.where(Concept.domain_id.in_(search.domain_id))

        # Filter by Vocabulary
        if search.vocabulary_id:
            stmt = stmt.where(Concept.vocabulary_id.in_(search.vocabulary_id))

        # Filter by Concept Class
        if search.concept_class_id:
            stmt = stmt.where(Concept.concept_class_id.in_(search.concept_class_id))

        # Filter by Standard Concept
        if search.standard_concept:
            stmt = stmt.where(Concept.standard_concept == search.standard_concept)

        # Filter by Invalid Reason
        if search.invalid_reason:
            stmt = stmt.where(Concept.invalid_reason == search.invalid_reason)

        # Limit results
        stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
