# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConceptSetItemBase(BaseModel):
    concept_id: int = Field(alias="conceptId")
    is_excluded: bool = Field(False, alias="isExcluded")
    include_descendants: bool = Field(False, alias="includeDescendants")
    include_mapped: bool = Field(False, alias="includeMapped")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ConceptSetItemCreate(ConceptSetItemBase):
    pass


class ConceptSetItem(ConceptSetItemBase):
    concept_set_item_id: int = Field(alias="conceptSetItemId")
    concept_set_id: int = Field(alias="conceptSetId")


class ConceptSetBase(BaseModel):
    concept_set_name: str = Field(alias="name")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ConceptSetCreate(ConceptSetBase):
    items: List[ConceptSetItemCreate] = Field(default_factory=list, alias="items")


class ConceptSetUpdate(ConceptSetBase):
    items: List[ConceptSetItemCreate] = Field(default_factory=list, alias="items")


class ConceptSet(ConceptSetBase):
    concept_set_id: int = Field(alias="id")
    created_date: datetime = Field(alias="createdDate")
    modified_date: datetime = Field(alias="modifiedDate")
    created_by: Optional[str] = Field(None, alias="createdBy")
    modified_by: Optional[str] = Field(None, alias="modifiedBy")
    # For GET requests, we often return items, but sometimes not.
    # We'll include them by default or handle with separate schemas if needed.
    # ATLAS often separates metadata from content. But for simplicity:
    items: List[ConceptSetItem] = Field(default_factory=list, alias="items")
