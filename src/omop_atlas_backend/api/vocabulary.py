# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from omop_atlas_backend.dependencies import get_vocabulary_service
from omop_atlas_backend.schemas.concept import Concept as ConceptSchema
from omop_atlas_backend.schemas.concept import ConceptSearch
from omop_atlas_backend.services.exceptions import ConceptNotFound
from omop_atlas_backend.services.vocabulary import VocabularyService

router = APIRouter(prefix="/vocabulary", tags=["Vocabulary"])


# Phase 2: Vocabulary Engine
@router.post("/search", response_model=List[ConceptSchema], response_model_by_alias=True)
async def search_concepts(
    search: ConceptSearch,
    limit: int = Query(20000, ge=1),
    offset: int = Query(0, ge=0),
    service: VocabularyService = Depends(get_vocabulary_service),  # noqa: B008
) -> List[ConceptSchema]:
    """
    Search for concepts in the vocabulary (POST).
    """
    # Service now returns List[ConceptSchema]
    return await service.search_concepts(search, limit, offset)


@router.get("/search", response_model=List[ConceptSchema], response_model_by_alias=True)
async def search_concepts_get(
    search: ConceptSearch = Depends(),  # noqa: B008
    limit: int = Query(20000, ge=1),
    offset: int = Query(0, ge=0),
    service: VocabularyService = Depends(get_vocabulary_service),  # noqa: B008
) -> List[ConceptSchema]:
    """
    Search for concepts in the vocabulary (GET).
    Allows searching via query parameters compatible with ConceptSearch aliases.
    e.g. /vocabulary/search?QUERY=aspirin&DOMAIN_ID=Drug
    """
    return await service.search_concepts(search, limit, offset)


@router.get("/concept/{id}", response_model=ConceptSchema, response_model_by_alias=True)
async def get_concept(
    id: int,
    service: VocabularyService = Depends(get_vocabulary_service),  # noqa: B008
) -> ConceptSchema:
    """
    Get a concept by ID, utilizing Redis cache if available.
    """
    try:
        return await service.get_concept_by_id(id)
    except ConceptNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
