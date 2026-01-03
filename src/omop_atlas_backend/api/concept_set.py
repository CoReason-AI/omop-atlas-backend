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

from fastapi import APIRouter, Depends, HTTPException, status

from omop_atlas_backend.dependencies import get_concept_set_service
from omop_atlas_backend.schemas.concept_set import (
    ConceptSet,
    ConceptSetCreate,
    ConceptSetUpdate,
)
from omop_atlas_backend.services.concept_set import ConceptSetNotFound, ConceptSetService
from omop_atlas_backend.services.exceptions import ConceptNotFound

router = APIRouter(prefix="/conceptset", tags=["Concept Set"])


@router.post("/", response_model=ConceptSet, status_code=status.HTTP_201_CREATED, response_model_by_alias=True)
async def create_concept_set(
    data: ConceptSetCreate,
    service: ConceptSetService = Depends(get_concept_set_service),  # noqa: B008
) -> ConceptSet:
    """
    Create a new Concept Set.
    """
    # TODO: Get actual user ID from auth context. Using 1 for now.
    user_id = 1
    try:
        return await service.create_concept_set(data, user_id)
    except ConceptNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Concept not found: {e.concept_id}"
        ) from e


@router.get("/{id}", response_model=ConceptSet, response_model_by_alias=True)
async def get_concept_set(
    id: int,
    service: ConceptSetService = Depends(get_concept_set_service),  # noqa: B008
) -> ConceptSet:
    """
    Get a Concept Set by ID.
    """
    try:
        return await service.get_concept_set(id)
    except ConceptSetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/{id}", response_model=ConceptSet, response_model_by_alias=True)
async def update_concept_set(
    id: int,
    data: ConceptSetUpdate,
    service: ConceptSetService = Depends(get_concept_set_service),  # noqa: B008
) -> ConceptSet:
    """
    Update a Concept Set.
    """
    try:
        return await service.update_concept_set(id, data)
    except ConceptSetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConceptNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Concept not found: {e.concept_id}"
        ) from e


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_concept_set(
    id: int,
    service: ConceptSetService = Depends(get_concept_set_service),  # noqa: B008
) -> None:
    """
    Delete a Concept Set.
    """
    try:
        await service.delete_concept_set(id)
    except ConceptSetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
