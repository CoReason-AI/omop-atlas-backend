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
Pydantic models for Concept Sets and Items.
Matches OHDSI ATLAS API contract (camelCase JSON).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from omop_atlas_backend.schemas.concept import Concept


class ConceptSetItemBase(BaseModel):
    """
    Base attributes for a Concept Set Item.
    """

    concept_id: int = Field(alias="conceptId")
    is_excluded: bool = Field(False, alias="isExcluded")
    include_descendants: bool = Field(False, alias="includeDescendants")
    include_mapped: bool = Field(False, alias="includeMapped")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class ConceptSetItemCreate(ConceptSetItemBase):
    """
    Schema for creating a Concept Set Item.
    """

    pass


class ConceptSetItem(ConceptSetItemBase):
    """
    Schema for a Concept Set Item response.
    """

    concept_set_item_id: int = Field(alias="conceptSetItemId")
    concept: Optional[Concept] = Field(None, alias="concept")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class ConceptSetBase(BaseModel):
    """
    Base attributes for a Concept Set.
    """

    concept_set_name: str = Field(alias="name")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class ConceptSetCreate(ConceptSetBase):
    """
    Schema for creating a Concept Set.
    """

    items: List[ConceptSetItemCreate] = Field(default_factory=list, alias="items")


class ConceptSetUpdate(BaseModel):
    """
    Schema for updating a Concept Set.
    """

    concept_set_name: Optional[str] = Field(None, alias="name")
    items: Optional[List[ConceptSetItemCreate]] = Field(None, alias="items")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class ConceptSet(ConceptSetBase):
    """
    Schema for a Concept Set response.
    """

    concept_set_id: int = Field(alias="id")
    created_by_id: int = Field(alias="createdBy")
    created_date: datetime = Field(alias="createdDate")
    items: List[ConceptSetItem] = Field(default_factory=list, alias="items")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
