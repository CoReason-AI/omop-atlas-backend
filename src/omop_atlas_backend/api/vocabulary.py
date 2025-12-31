# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from omop_atlas_backend.dependencies import get_db, get_redis
from omop_atlas_backend.schemas.concept import Concept as ConceptSchema
from omop_atlas_backend.schemas.concept import ConceptSearch
from omop_atlas_backend.services.vocabulary import VocabularyService
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/vocabulary", tags=["Vocabulary"])


@router.post("/search", response_model=List[ConceptSchema], response_model_by_alias=True)
async def search_concepts(
    search: ConceptSearch,
    limit: int = Query(20000, ge=1),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> List[ConceptSchema]:
    """
    Search for concepts in the vocabulary.
    """
    concepts = await VocabularyService.search_concepts(search, session, limit, offset)
    return [ConceptSchema.model_validate(c) for c in concepts]


@router.get("/concept/{id}", response_model=ConceptSchema, response_model_by_alias=True)
async def get_concept(
    id: int,
    session: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
) -> ConceptSchema:
    """
    Get a concept by ID, utilizing Redis cache if available.
    """
    concept = await VocabularyService.get_concept(id, session, redis)
    if not concept:
        raise HTTPException(status_code=404, detail=f"There is no concept with id = {id}.")
    return ConceptSchema.model_validate(concept)
