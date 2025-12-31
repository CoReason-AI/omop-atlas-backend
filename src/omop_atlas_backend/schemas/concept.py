# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Concept(BaseModel):
    concept_id: int = Field(alias="conceptId")
    concept_name: str = Field(alias="conceptName")
    domain_id: str = Field(alias="domainId")
    vocabulary_id: str = Field(alias="vocabularyId")
    concept_class_id: str = Field(alias="conceptClassId")
    standard_concept: Optional[str] = Field(None, alias="standardConcept")
    concept_code: str = Field(alias="conceptCode")
    valid_start_date: date = Field(alias="validStartDate")
    valid_end_date: date = Field(alias="validEndDate")
    invalid_reason: Optional[str] = Field(None, alias="invalidReason")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ConceptSearch(BaseModel):
    query: str = Field(..., alias="QUERY")
    domain_id: Optional[List[str]] = Field(None, alias="DOMAIN_ID")
    vocabulary_id: Optional[List[str]] = Field(None, alias="VOCABULARY_ID")
    concept_class_id: Optional[List[str]] = Field(None, alias="CONCEPT_CLASS_ID")
    standard_concept: Optional[str] = Field(None, alias="STANDARD_CONCEPT")
    invalid_reason: Optional[str] = Field(None, alias="INVALID_REASON")
    is_lexical: bool = Field(False, alias="IS_LEXICAL")
