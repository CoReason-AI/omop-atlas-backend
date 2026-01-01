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


def test_concept_schema_aliasing() -> None:
    """Test that Concept schema handles camelCase aliases correctly."""
    data = {
        "conceptId": 1,
        "conceptName": "Test",
        "domainId": "Condition",
        "vocabularyId": "SNOMED",
        "conceptClassId": "Class",
        "standardConcept": "S",
        "conceptCode": "123",
        "validStartDate": "2020-01-01",
        "validEndDate": "2099-12-31",
        "invalidReason": None,
    }

    concept = Concept(**data)

    assert concept.concept_id == 1
    assert concept.concept_name == "Test"
    assert concept.valid_start_date == date(2020, 1, 1)

    # Verify serialization uses aliases
    dump = concept.model_dump(by_alias=True)
    assert dump["conceptId"] == 1
    assert "concept_id" not in dump


def test_concept_search_defaults() -> None:
    """Test ConceptSearch defaults and aliasing."""
    search = ConceptSearch()
    assert search.query == ""
    assert search.domain_id == []

    data = {"QUERY": "Fever", "DOMAIN_ID": ["Condition"], "INVALID_REASON": "V"}
    search = ConceptSearch(**data)
    assert search.query == "Fever"
    assert search.domain_id == ["Condition"]
    assert search.invalid_reason == "V"
