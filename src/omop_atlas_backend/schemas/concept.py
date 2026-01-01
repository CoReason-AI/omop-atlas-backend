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
Phase 2: Vocabulary Engine - Schemas
Pydantic models for serializing Concept search results and API responses.
Matches OHDSI ATLAS API contract (camelCase JSON).
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Concept(BaseModel):
    """
    Pydantic model for Concept.
    Uses 'alias' to support camelCase JSON output, compatible with ATLAS.
    """

    # Field aliases are for JSON input/output (camelCase to match ATLAS)
    # Python attributes are snake_case to match SQLAlchemy models
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

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class ConceptSearch(BaseModel):
    """
    Pydantic model for Concept Search criteria.
    Uses 'alias' to map uppercase JSON keys from ATLAS requests to snake_case python attributes.
    """

    # Using aliases to map uppercase JSON keys to snake_case python attributes
    query: str = Field("", alias="QUERY")
    domain_id: List[str] = Field(default_factory=list, alias="DOMAIN_ID")
    vocabulary_id: List[str] = Field(default_factory=list, alias="VOCABULARY_ID")
    concept_class_id: List[str] = Field(default_factory=list, alias="CONCEPT_CLASS_ID")
    standard_concept: Optional[str] = Field(None, alias="STANDARD_CONCEPT")
    invalid_reason: Optional[str] = Field(None, alias="INVALID_REASON")
    is_lexical: bool = Field(False, alias="IS_LEXICAL")
