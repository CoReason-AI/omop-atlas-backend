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

from typing import Any, Dict, List, Optional

from redis.asyncio import Redis
from sqlalchemy import Float, Select, case, func, literal, or_, select, union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from omop_atlas_backend.models.vocabulary import Concept as ConceptModel
from omop_atlas_backend.models.vocabulary import ConceptAncestor, ConceptRelationship, ConceptSynonym, Relationship
from omop_atlas_backend.schemas.concept import Concept as ConceptSchema
from omop_atlas_backend.schemas.concept import ConceptSearch
from omop_atlas_backend.schemas.concept import RelatedConcept as RelatedConceptSchema
from omop_atlas_backend.services.exceptions import ConceptNotFound


class VocabularyService:
    """
    Service for Vocabulary operations.
    """

    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):  # type: ignore
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
        Supports 'is_lexical' search similar to OHDSI WebAPI.
        """
        if search.is_lexical and search.query:
            return await self._search_lexical(search, limit, offset)

        stmt = select(ConceptModel)

        if search.query:
            # Check dialect for optimization
            dialect_name = self.db.bind.dialect.name if self.db.bind else "postgresql"

            if dialect_name == "postgresql":
                # FTS on name OR ILIKE on code
                fts_condition = func.to_tsvector("english", ConceptModel.concept_name).op("@@")(
                    func.plainto_tsquery("english", search.query)
                )
                code_condition = ConceptModel.concept_code.ilike(f"%{search.query}%")
                stmt = stmt.where(or_(fts_condition, code_condition))
            else:
                # Fallback for SQLite/Other (Tests)
                # Simple ILIKE on name and code
                stmt = stmt.where(
                    or_(
                        ConceptModel.concept_name.ilike(f"%{search.query}%"),
                        ConceptModel.concept_code.ilike(f"%{search.query}%"),
                    )
                )

        stmt = self._apply_filters(stmt, search)
        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        return [ConceptSchema.model_validate(c) for c in result.scalars().all()]

    async def get_related_concepts(self, concept_id: int) -> List[RelatedConceptSchema]:
        """
        Retrieves concepts related to the given concept ID via relationship and ancestor tables.
        Matches OHDSI WebAPI getRelatedConcepts logic.
        """
        cache_key = f"concept_related:{concept_id}"

        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    # Expecting a list of dicts/json
                    import json

                    data = json.loads(cached)
                    return [RelatedConceptSchema.model_validate(item) for item in data]
            except Exception:
                pass

        # 1. Direct Relationships (ConceptRelationship)
        # Query 1: (concept_id_1 = id) -> concept_id_2 is the related concept
        # We need to join Relationship to get relationship_name
        # And join Concept (for concept_id_2) to get related concept details
        c2 = aliased(ConceptModel)
        r = aliased(Relationship)

        q1 = (
            select(
                c2,
                r.relationship_name,
                literal(0).label("relationship_distance"),  # Direct relationships have distance 0 or 1?
            )
            .select_from(ConceptRelationship)
            .join(c2, ConceptRelationship.concept_id_2 == c2.concept_id)
            .join(r, ConceptRelationship.relationship_id == r.relationship_id)
            .where(ConceptRelationship.concept_id_1 == concept_id)
            .where(ConceptRelationship.invalid_reason.is_(None))
        )

        # 2. Ancestry (ConceptAncestor)
        # Query 2: Ancestors (descendant_concept_id = id) -> ancestor_concept_id is related
        # Relationship Name: "Ancestor"
        # Distance: min_levels_of_separation
        ca1 = aliased(ConceptAncestor)
        c_anc = aliased(ConceptModel)
        q2 = (
            select(
                c_anc,
                literal("Ancestor").label("relationship_name"),
                ca1.min_levels_of_separation.label("relationship_distance"),
            )
            .select_from(ca1)
            .join(c_anc, ca1.ancestor_concept_id == c_anc.concept_id)
            .where(ca1.descendant_concept_id == concept_id)
            .where(ca1.ancestor_concept_id != concept_id)  # Exclude self
        )

        # Query 3: Descendants (ancestor_concept_id = id) -> descendant_concept_id is related
        # Relationship Name: "Descendant"
        # Distance: min_levels_of_separation
        ca2 = aliased(ConceptAncestor)
        c_desc = aliased(ConceptModel)
        q3 = (
            select(
                c_desc,
                literal("Descendant").label("relationship_name"),
                ca2.min_levels_of_separation.label("relationship_distance"),
            )
            .select_from(ca2)
            .join(c_desc, ca2.descendant_concept_id == c_desc.concept_id)
            .where(ca2.ancestor_concept_id == concept_id)
            .where(ca2.descendant_concept_id != concept_id)  # Exclude self
        )

        related_map: Dict[int, RelatedConceptSchema] = {}

        # Execute Q1
        res1 = await self.db.execute(q1)
        for row in res1.all():
            concept, rel_name, rel_dist = row
            self._add_relationship(related_map, concept, rel_name, rel_dist)

        # Execute Q2
        res2 = await self.db.execute(q2)
        for row in res2.all():
            concept, rel_name, rel_dist = row
            self._add_relationship(related_map, concept, rel_name, rel_dist)

        # Execute Q3
        res3 = await self.db.execute(q3)
        for row in res3.all():
            concept, rel_name, rel_dist = row
            self._add_relationship(related_map, concept, rel_name, rel_dist)

        results = list(related_map.values())

        if self.redis:
            try:
                # Serialize list of Pydantic models
                json_data = "[" + ",".join([r.model_dump_json(by_alias=True) for r in results]) + "]"
                await self.redis.set(cache_key, json_data, ex=3600)
            except Exception:
                pass

        return results

    def _add_relationship(
        self, related_map: Dict[int, RelatedConceptSchema], concept: ConceptModel, rel_name: str, rel_dist: int
    ) -> None:
        """Helper to aggregate relationships for a concept."""
        if concept.concept_id not in related_map:
            # Create new RelatedConcept
            # We first convert the SQLAlchemy model to the Pydantic Schema
            base_schema = ConceptSchema.model_validate(concept)
            # Then create RelatedConcept (which inherits fields)
            related_obj = RelatedConceptSchema(
                **base_schema.model_dump(by_alias=True),
                relationships=[],
            )
            related_map[concept.concept_id] = related_obj

        # Add relationship details
        # We need a schema for relationship
        from omop_atlas_backend.schemas.concept import ConceptRelationship

        rel_obj = ConceptRelationship(
            relationship_name=rel_name,
            relationship_distance=rel_dist,
        )
        related_map[concept.concept_id].relationships.append(rel_obj)

    async def _search_lexical(self, search: ConceptSearch, limit: int, offset: int) -> List[ConceptSchema]:
        """
        Implements lexical search logic: matching concepts by name or synonym, ranked by similarity.
        """
        # 1. Prepare terms
        # Use .split() to handle multiple spaces correctly
        search_terms = search.query.lower().split()
        truncated_terms = [t[:6] for t in search_terms if len(t) >= 8]
        all_terms = sorted(list(set(search_terms + truncated_terms)), key=len, reverse=True)

        term_map = {f"term_{i + 1}": term for i, term in enumerate(all_terms)}

        # 2. Build REPLACE expression for score calculation
        # REPLACE(REPLACE(lower(concept_name), 'term1',''), 'term2','') ...
        replace_expr_name = func.lower(ConceptModel.concept_name)
        for term in term_map.values():
            replace_expr_name = func.replace(replace_expr_name, term, "")

        # 3. Build Filters
        # Name filters: lower(concept_name) like '%term%'
        name_filters = [ConceptModel.concept_name.ilike(f"%{term}%") for term in term_map.values() if len(term) < 8]

        # Synonym filters: lower(concept_synonym_name) like '%term%'
        synonym_filters = [
            ConceptSynonym.concept_synonym_name.ilike(f"%{term}%") for term in term_map.values() if len(term) < 8
        ]

        # 4. Queries
        # Match from Concept table
        q_concept = select(ConceptModel.concept_id.label("matched_concept"))
        if name_filters:
            q_concept = q_concept.where(or_(*name_filters))

        # Match from Synonym table
        q_synonym = select(ConceptSynonym.concept_id.label("matched_concept"))
        if synonym_filters:
            q_synonym = q_synonym.where(or_(*synonym_filters))

        # Union of matches
        matched_ids_subquery = union(q_concept, q_synonym).subquery()

        # 5. Final Query with Scoring
        # We need to calculate length of (Name - Terms) to get a ratio.
        # Ratio = 1 - (Len(Replaced) / Len(Original))
        # Closer to 1 means more of the string is covered by terms.

        # Note: We need to clean the name (remove spaces, dashes) for accurate length comparison as per Java logic
        # Java: LEN(REPLACE(REPLACE(CONCEPT_NAME, ' ',''), '-', ''))
        def clean_str(col: Any) -> Any:
            return func.replace(func.replace(col, " ", ""), "-", "")

        c_len = func.length(clean_str(ConceptModel.concept_name))
        r_len = func.length(clean_str(replace_expr_name))

        # Avoid division by zero
        ratio_score = case((c_len > 0, 1.0 - (func.cast(r_len, Float) / func.cast(c_len, Float))), else_=0.0)

        # Join back to Concept to get details and apply other filters
        stmt_select: Select[Any] = select(ConceptModel).join(
            matched_ids_subquery, ConceptModel.concept_id == matched_ids_subquery.c.matched_concept
        )

        # If standard_concept is NOT specified in search, OHDSI legacy behavior often defaults to 'S'.
        # However, to allow searching for non-standard, we only default if not provided.
        # But for strict API compatibility with legacy Java code which does:
        # WHERE c1.standard_concept = 'S' @filters
        # We should check if we want to enforce 'S' ONLY if filters don't override it.
        # The Java code effectively forces S unless filters are weird.
        # But standard filters in Java include standard_concept check.
        # Let's apply filters first. If standard_concept is not set in search, maybe we should default to S?
        # The Java SQL has: WHERE c1.standard_concept = 'S' @filters
        # This implies it forces S AND whatever else. This seems restrictive if one wants non-standard.
        # But the prompt review said: "The method should respect the incoming search filters".
        # So I will NOT force 'S' if the user asked for 'N' or something else.
        # If user did NOT specify standard_concept, should I default to S?
        # The legacy SQL forces S. The Review says "This overrides and conflicts...".
        # So I will remove the hardcoded 'S' and rely on _apply_filters.
        # If _apply_filters sees None, it doesn't filter.
        # If we want to replicate "default is S", we should set search.standard_concept to 'S' if None?
        # But ConceptSearch defaults standard_concept to None.
        # Let's trust the Reviewer: "remove hardcoded... respect user input".

        stmt_select = self._apply_filters(stmt_select, search)

        # Order by score
        # Since we can't easily put the complex calculation in order_by without computing it in select,
        # usually we might select it. But we need to return Model objects.
        # We can order by the expression directly.
        stmt_select = stmt_select.order_by(ratio_score.desc())

        stmt_select = stmt_select.limit(limit).offset(offset)

        result = await self.db.execute(stmt_select)
        return [ConceptSchema.model_validate(c) for c in result.scalars().all()]

    def _apply_filters(self, stmt: Select[Any], search: ConceptSearch) -> Select[Any]:
        """Helper to apply standard filters to a query."""
        if search.vocabulary_id:
            stmt = stmt.where(ConceptModel.vocabulary_id.in_(search.vocabulary_id))

        if search.domain_id:
            stmt = stmt.where(ConceptModel.domain_id.in_(search.domain_id))

        if search.concept_class_id:
            stmt = stmt.where(ConceptModel.concept_class_id.in_(search.concept_class_id))

        if search.standard_concept:
            if search.standard_concept == "N":
                stmt = stmt.where(ConceptModel.standard_concept.is_(None))
            else:
                stmt = stmt.where(ConceptModel.standard_concept == search.standard_concept)

        if search.invalid_reason:
            if search.invalid_reason == "V":
                stmt = stmt.where(ConceptModel.invalid_reason.is_(None))
            else:
                stmt = stmt.where(ConceptModel.invalid_reason == search.invalid_reason)
        return stmt
