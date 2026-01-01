# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from omop_atlas_backend.models.vocabulary import Concept, ConceptClass, Domain, Vocabulary


def test_concept_model_definitions() -> None:
    """Test that Concept model fields are defined correctly."""
    assert Concept.__tablename__ == "concept"

    # Check attributes existence (this checks if SQLAlchemy mapped them)
    assert hasattr(Concept, "concept_id")
    assert hasattr(Concept, "concept_name")
    assert hasattr(Concept, "domain_id")
    assert hasattr(Concept, "vocabulary_id")
    assert hasattr(Concept, "concept_class_id")
    assert hasattr(Concept, "standard_concept")
    assert hasattr(Concept, "concept_code")
    assert hasattr(Concept, "valid_start_date")
    assert hasattr(Concept, "valid_end_date")
    assert hasattr(Concept, "invalid_reason")


def test_vocabulary_model_definitions() -> None:
    """Test that Vocabulary model fields are defined correctly."""
    assert Vocabulary.__tablename__ == "vocabulary"

    assert hasattr(Vocabulary, "vocabulary_id")
    assert hasattr(Vocabulary, "vocabulary_name")
    assert hasattr(Vocabulary, "vocabulary_reference")
    assert hasattr(Vocabulary, "vocabulary_version")
    assert hasattr(Vocabulary, "vocabulary_concept_id")


def test_domain_model_definitions() -> None:
    """Test that Domain model fields are defined correctly."""
    assert Domain.__tablename__ == "domain"

    assert hasattr(Domain, "domain_id")
    assert hasattr(Domain, "domain_name")
    assert hasattr(Domain, "domain_concept_id")


def test_concept_class_model_definitions() -> None:
    """Test that ConceptClass model fields are defined correctly."""
    assert ConceptClass.__tablename__ == "concept_class"

    assert hasattr(ConceptClass, "concept_class_id")
    assert hasattr(ConceptClass, "concept_class_name")
    assert hasattr(ConceptClass, "concept_class_concept_id")
