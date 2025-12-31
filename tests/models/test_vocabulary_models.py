# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

# Phase 2: Vocabulary Engine Tests

from typing import cast

from sqlalchemy import Table

from omop_atlas_backend.models.vocabulary import Concept, ConceptAncestor, ConceptRelationship, Relationship


def test_concept_indices() -> None:
    """
    Verify that the Concept model has the expected indices defined.
    """
    # Access the Table object via __table__
    # Mypy treats __table__ as FromClause which doesn't expose indexes, so we cast to Table
    table = cast(Table, Concept.__table__)
    indexes = table.indexes

    # Create a set of index names for easier assertion
    index_names = {idx.name for idx in indexes}

    expected_indexes = {
        "ix_concept_vocabulary_id",
        "ix_concept_domain_id",
        "ix_concept_class_id",
        "ix_concept_standard_concept",
        "ix_concept_code",
        "ix_concept_name",
    }

    assert expected_indexes.issubset(index_names), f"Missing indices: {expected_indexes - index_names}"

    # Verify column coverage (basic check)
    for idx in indexes:
        if idx.name == "ix_concept_vocabulary_id":
            assert "vocabulary_id" in [c.name for c in idx.columns]
        elif idx.name == "ix_concept_domain_id":
            assert "domain_id" in [c.name for c in idx.columns]


def test_concept_ancestor_indices() -> None:
    """
    Verify that the ConceptAncestor model has the expected indices defined.
    """
    table = cast(Table, ConceptAncestor.__table__)
    indexes = table.indexes
    index_names = {idx.name for idx in indexes}

    expected_indexes = {
        "ix_concept_ancestor_ancestor",
        "ix_concept_ancestor_descendant",
    }
    assert expected_indexes.issubset(index_names)


def test_concept_relationship_indices() -> None:
    """
    Verify that the ConceptRelationship model has the expected indices defined.
    """
    table = cast(Table, ConceptRelationship.__table__)
    indexes = table.indexes
    index_names = {idx.name for idx in indexes}

    expected_indexes = {
        "ix_concept_relationship_id_2",
        "ix_concept_relationship_id_3",
    }
    assert expected_indexes.issubset(index_names)


def test_relationship_table() -> None:
    """
    Verify that the Relationship model is correctly defined.
    """
    assert Relationship.__tablename__ == "relationship"
    # Basic check to ensure instantiation works
    rel = Relationship(
        relationship_id="Is a",
        relationship_name="Is a",
        is_hierarchical="1",
        defines_ancestry="1",
        reverse_relationship_id="Subsumes",
        relationship_concept_id=1,
    )
    assert rel.relationship_id == "Is a"
