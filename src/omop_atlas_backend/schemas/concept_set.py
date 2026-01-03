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
Phase 3: Concept Sets - Schemas
Pydantic models for Concept Set operations.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from omop_atlas_backend.schemas.concept import Concept


class ConceptSetItemBase(BaseModel):
    """
    Base schema for Concept Set Item.
    """

    concept_id: int = Field(alias="conceptId")
    is_excluded: bool = Field(False, alias="isExcluded")
    include_descendants: bool = Field(False, alias="includeDescendants")
    include_mapped: bool = Field(False, alias="includeMapped")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class ConceptSetItemCreate(ConceptSetItemBase):
    """
    Schema for adding an item to a Concept Set.
    """

    pass


class ConceptSetItemRead(ConceptSetItemBase):
    """
    Schema for reading a Concept Set Item.
    Includes the resolved Concept details.
    """

    concept_set_item_id: int = Field(alias="conceptSetItemId")
    concept: Optional[Concept] = Field(None, alias="concept")  # Full concept details


class ConceptSetBase(BaseModel):
    """
    Base schema for Concept Set.
    """

    name: str = Field(alias="name", min_length=1, max_length=255)


class ConceptSetCreate(ConceptSetBase):
    """
    Schema for creating a new Concept Set.
    """

    items: List[ConceptSetItemCreate] = Field(default_factory=list, alias="items")


class ConceptSetUpdate(ConceptSetBase):
    """
    Schema for updating a Concept Set.
    """

    items: Optional[List[ConceptSetItemCreate]] = Field(None, alias="items")


class ConceptSetRead(ConceptSetBase):
    """
    Schema for reading a Concept Set.
    """

    id: int = Field(alias="id")
    created_by_id: int = Field(alias="createdById")
    created_date: datetime = Field(alias="createdDate")
    items: List[ConceptSetItemRead] = Field(default_factory=list, alias="items")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
