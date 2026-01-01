# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend


from omop_atlas_backend.models.concept_set import ConceptSet, ConceptSetItem


def test_concept_set_model_definitions() -> None:
    """Test that ConceptSet model fields are defined correctly."""
    assert ConceptSet.__tablename__ == "concept_set"

    assert hasattr(ConceptSet, "concept_set_id")
    assert hasattr(ConceptSet, "concept_set_name")
    assert hasattr(ConceptSet, "created_by_id")
    assert hasattr(ConceptSet, "created_date")
    assert hasattr(ConceptSet, "created_by")
    assert hasattr(ConceptSet, "items")


def test_concept_set_item_model_definitions() -> None:
    """Test that ConceptSetItem model fields are defined correctly."""
    assert ConceptSetItem.__tablename__ == "concept_set_item"

    assert hasattr(ConceptSetItem, "concept_set_item_id")
    assert hasattr(ConceptSetItem, "concept_set_id")
    assert hasattr(ConceptSetItem, "concept_id")
    assert hasattr(ConceptSetItem, "is_excluded")
    assert hasattr(ConceptSetItem, "include_descendants")
    assert hasattr(ConceptSetItem, "include_mapped")
    assert hasattr(ConceptSetItem, "concept_set")
    assert hasattr(ConceptSetItem, "concept")


def test_concept_set_repr() -> None:
    """Test the __repr__ method of ConceptSet."""
    cs = ConceptSet(concept_set_id=1, concept_set_name="Test Set")
    assert repr(cs) == "<ConceptSet(id=1, name='Test Set')>"


def test_concept_set_item_repr() -> None:
    """Test the __repr__ method of ConceptSetItem."""
    csi = ConceptSetItem(concept_set_item_id=1, concept_id=100)
    assert repr(csi) == "<ConceptSetItem(id=1, concept_id=100)>"
