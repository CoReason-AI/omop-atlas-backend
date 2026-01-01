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

from omop_atlas_backend.schemas.concept import Concept, ConceptSearch


def test_concept_schema_serialization():
    """Test serialization of Concept model with aliases."""
    data = {
        "concept_id": 1,
        "concept_name": "Test Concept",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "12345",
        "valid_start_date": date(2020, 1, 1),
        "valid_end_date": date(2099, 12, 31),
        "invalid_reason": None,
    }
    concept = Concept(**data)

    # Check JSON output has camelCase keys
    json_output = concept.model_dump(by_alias=True)
    assert json_output["conceptId"] == 1
    assert json_output["conceptName"] == "Test Concept"
    assert json_output["domainId"] == "Condition"
    assert json_output["validStartDate"] == date(2020, 1, 1)


def test_concept_search_schema_deserialization():
    """Test deserialization of ConceptSearch model from API input."""
    data = {
        "QUERY": "aspirin",
        "DOMAIN_ID": ["Drug"],
        "VOCABULARY_ID": ["RxNorm"],
        "CONCEPT_CLASS_ID": ["Ingredient"],
        "STANDARD_CONCEPT": "S",
        "INVALID_REASON": "V",
        "IS_LEXICAL": True,
    }
    search = ConceptSearch(**data)

    assert search.query == "aspirin"
    assert search.domain_id == ["Drug"]
    assert search.vocabulary_id == ["RxNorm"]
    assert search.is_lexical is True


def test_concept_search_defaults():
    """Test default values for ConceptSearch."""
    search = ConceptSearch()
    assert search.query == ""
    assert search.domain_id == []
    assert search.vocabulary_id == []
    assert search.is_lexical is False
