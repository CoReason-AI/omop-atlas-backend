# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend


from omop_atlas_backend.models.vocabulary import (
    Concept,
    Domain,
    Vocabulary,
)


def test_concept_model_repr() -> None:
    """Test __repr__ for Concept model."""
    concept = Concept(concept_id=1, concept_name="Test")
    assert repr(concept) == "<Concept(id=1, name='Test')>"


def test_vocabulary_model_repr() -> None:
    """Test __repr__ for Vocabulary model."""
    vocab = Vocabulary(vocabulary_id="SNOMED", vocabulary_name="Systematized Nomenclature of Medicine")
    assert repr(vocab) == "<Vocabulary(id='SNOMED', name='Systematized Nomenclature of Medicine')>"


def test_domain_model_repr() -> None:
    """Test __repr__ for Domain model."""
    domain = Domain(domain_id="Condition", domain_name="Condition")
    assert repr(domain) == "<Domain(id='Condition', name='Condition')>"


def test_concept_indexes() -> None:
    """Test that Concept model has the expected indexes."""
    indexes = {i.name for i in Concept.__table__.indexes}
    expected = {
        "ix_concept_vocabulary_id",
        "ix_concept_domain_id",
        "ix_concept_class_id",
        "ix_concept_standard_concept",
        "ix_concept_code",
        "ix_concept_name",
        "ix_concept_name_tsv",
    }
    assert expected.issubset(indexes)


def test_concept_tsv_index_definition() -> None:
    """Test that the TSVector index is correctly defined."""
    tsv_index = next(i for i in Concept.__table__.indexes if i.name == "ix_concept_name_tsv")
    # Verify postgresql_using='gin'
    assert tsv_index.kwargs.get("postgresql_using") == "gin"
