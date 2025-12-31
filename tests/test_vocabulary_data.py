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

from omop_atlas_backend.models.vocabulary import Concept as ConceptModel
from omop_atlas_backend.schemas.concept import Concept as ConceptSchema
from omop_atlas_backend.schemas.concept import ConceptSearch


def test_concept_schema_serialization() -> None:
    """Test that Concept schema serializes to camelCase JSON."""
    concept = ConceptSchema(
        conceptId=1,
        conceptName="Test Concept",
        domainId="Condition",
        vocabularyId="SNOMED",
        conceptClassId="Clinical Finding",
        standardConcept="S",
        conceptCode="12345",
        validStartDate=date(2020, 1, 1),
        validEndDate=date(2099, 12, 31),
        invalidReason=None,
    )

    # Dump to JSON compatible dict by alias
    data = concept.model_dump(by_alias=True)

    assert data["conceptId"] == 1
    assert data["conceptName"] == "Test Concept"
    assert data["validStartDate"] == date(2020, 1, 1)
    # Ensure snake_case keys are NOT present
    assert "concept_id" not in data


def test_concept_search_deserialization() -> None:
    """Test that ConceptSearch schema deserializes from UpperCase JSON keys."""
    input_data = {
        "QUERY": "heart",
        "DOMAIN_ID": ["Condition", "Drug"],
        "VOCABULARY_ID": ["SNOMED"],
        "STANDARD_CONCEPT": "S",
        "INVALID_REASON": "V",
        "CONCEPT_CLASS_ID": [],
        "IS_LEXICAL": True,
    }

    # Pydantic V2 model validation handles dict unwrapping better with model_validate
    search = ConceptSearch.model_validate(input_data)

    assert search.query == "heart"
    assert search.domain_id == ["Condition", "Drug"]
    assert search.vocabulary_id == ["SNOMED"]
    assert search.standard_concept == "S"
    assert search.is_lexical is True


def test_concept_search_defaults() -> None:
    """Test that ConceptSearch schema handles missing optional fields."""
    input_data = {"QUERY": "aspirin"}

    search = ConceptSearch.model_validate(input_data)

    assert search.query == "aspirin"
    assert search.domain_id is None
    assert search.is_lexical is False


def test_concept_model_instantiation() -> None:
    """Test that SQLAlchemy Concept model can be instantiated."""
    concept = ConceptModel(
        concept_id=100,
        concept_name="Model Test",
        domain_id="Procedure",
        vocabulary_id="CPT4",
        concept_class_id="Procedure",
        standard_concept="S",
        concept_code="99213",
        valid_start_date=date(2023, 1, 1),
        valid_end_date=date(2024, 1, 1),
    )

    assert concept.concept_id == 100
    assert concept.concept_name == "Model Test"
    assert concept.invalid_reason is None


def test_concept_schema_from_orm() -> None:
    """Test creating Concept schema from SQLAlchemy model."""
    model = ConceptModel(
        concept_id=555,
        concept_name="ORM Test",
        domain_id="Measurement",
        vocabulary_id="LOINC",
        concept_class_id="Lab Test",
        standard_concept=None,
        concept_code="L123",
        valid_start_date=date(2022, 5, 5),
        valid_end_date=date(2023, 5, 5),
        invalid_reason="D",
    )

    schema = ConceptSchema.model_validate(model)

    assert schema.concept_id == 555
    assert schema.concept_name == "ORM Test"
    assert schema.invalid_reason == "D"

    json_output = schema.model_dump(by_alias=True)
    assert json_output["conceptId"] == 555
