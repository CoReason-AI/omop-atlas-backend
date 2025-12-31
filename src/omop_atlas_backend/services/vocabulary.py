from typing import List, Optional

from redis.asyncio import Redis
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.vocabulary import Concept
from omop_atlas_backend.schemas.concept import Concept as ConceptSchema
from omop_atlas_backend.schemas.concept import ConceptSearch


class VocabularyService:
    DEFAULT_SEARCH_ROWS = 20000

    @staticmethod
    async def search_concepts(
        search: ConceptSearch, session: AsyncSession, limit: int = DEFAULT_SEARCH_ROWS, offset: int = 0
    ) -> List[Concept]:
        stmt = select(Concept)

        # Domain ID Filter
        if search.domain_id:
            domain_clauses = []
            non_measurement_domains = [d for d in search.domain_id if d != "Measurement"]

            if non_measurement_domains:
                domain_clauses.append(Concept.domain_id.in_(non_measurement_domains))

            if "Measurement" in search.domain_id:
                # MEASUREMENT domain special case: ensure concept class is 'lab test' or 'procedure'
                # Note: Java source uses LOWER(concept_class_id) in ('lab test', 'procedure')
                # But here we assume concept_class_id is consistent case or we use ilike if needed.
                # The Java code was: (DOMAIN_ID = 'Measurement' and
                # LOWER(concept_class_id) in ('lab test', 'procedure'))
                domain_clauses.append(
                    (Concept.domain_id == "Measurement")
                    & (func.lower(Concept.concept_class_id).in_(["lab test", "procedure"]))
                )

            if domain_clauses:
                stmt = stmt.where(or_(*domain_clauses))

        # Vocabulary ID Filter
        if search.vocabulary_id:
            stmt = stmt.where(Concept.vocabulary_id.in_(search.vocabulary_id))

        # Concept Class ID Filter
        if search.concept_class_id:
            stmt = stmt.where(Concept.concept_class_id.in_(search.concept_class_id))

        # Invalid Reason Filter
        if search.invalid_reason is not None and search.invalid_reason.strip() != "":
            if search.invalid_reason == "V":
                stmt = stmt.where(Concept.invalid_reason.is_(None))
            else:
                stmt = stmt.where(Concept.invalid_reason == search.invalid_reason.strip())

        # Standard Concept Filter
        if search.standard_concept:
            if search.standard_concept == "N":
                stmt = stmt.where(Concept.standard_concept.is_(None))
            else:
                stmt = stmt.where(Concept.standard_concept == search.standard_concept.strip())

        # Query Filter
        if search.query:
            query_str = search.query.strip()

            if search.is_lexical:
                # Lexical search implementation (simplified ILIKE for now, as per plan)
                # Java implementation does complex tokenization and fuzzy matching.
                # For this step, we'll do basic name/synonym ILIKE.
                # Note: Java lexical search only filters on concept_name (and synonym), NOT concept_code/ID
                stmt = stmt.where(Concept.concept_name.ilike(f"%{query_str}%"))
            else:
                # Non-lexical search
                # Java: LOWER(CONCEPT_NAME) LIKE '%@query%' or LOWER(CONCEPT_CODE) LIKE '%@query%'
                # If numeric: or CONCEPT_ID = CAST(@query as int)

                filters = [Concept.concept_name.ilike(f"%{query_str}%"), Concept.concept_code.ilike(f"%{query_str}%")]

                if query_str.isdigit():
                    filters.append(Concept.concept_id == int(query_str))

                stmt = stmt.where(or_(*filters))

        stmt = stmt.limit(limit).offset(offset)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_concept(concept_id: int, session: AsyncSession, redis: Optional[Redis] = None) -> Optional[Concept]:
        cache_key = f"conceptDetail:{concept_id}"

        if redis:
            cached_data = await redis.get(cache_key)
            if cached_data:
                try:
                    # Use Pydantic schema to validate and parse JSON (handles date parsing)
                    # use alias=True because cache stores camelCase keys
                    schema_obj = ConceptSchema.model_validate_json(cached_data)

                    # Convert Pydantic model to dict, using aliases?
                    # No, Concept Model expects snake_case arguments matching its columns/attributes.
                    # schema_obj.model_dump() returns snake_case keys with correct types (date objects).
                    # schema_obj.model_dump(by_alias=True) returns camelCase.
                    # We want snake_case to populate the SQLAlchemy model.

                    concept_data = schema_obj.model_dump()

                    # Reconstruct the SQLAlchemy model
                    return Concept(**concept_data)
                except Exception:
                    # Fallback to DB if cache parsing fails
                    pass

        stmt = select(Concept).where(Concept.concept_id == concept_id)
        result = await session.execute(stmt)
        concept = result.scalar_one_or_none()

        if concept and redis:
            # Cache the concept
            # Use Pydantic schema for serialization
            schema_model = ConceptSchema.model_validate(concept)
            # Use by_alias=True to get camelCase keys which matches what we expect in cache/API
            await redis.set(cache_key, schema_model.model_dump_json(by_alias=True))

        return concept  # type: ignore[no-any-return]
