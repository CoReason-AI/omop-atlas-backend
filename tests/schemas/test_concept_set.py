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

import pytest
from pydantic import ValidationError

from omop_atlas_backend.schemas.concept_set import (
    ConceptSetCreate,
    ConceptSetItemCreate,
    ConceptSetItemRead,
    ConceptSetRead,
    ConceptSetUpdate,
)


def test_concept_set_item_create_schema() -> None:
    """Test creation of ConceptSetItemCreate schema."""
    item = ConceptSetItemCreate(concept_id=123, is_excluded=True)
    assert item.concept_id == 123
    assert item.is_excluded is True
    assert item.include_descendants is False  # Default
    assert item.include_mapped is False  # Default

    # Test camelCase alias input
    item_alias = ConceptSetItemCreate.model_validate({"conceptId": 456, "includeDescendants": True})
    assert item_alias.concept_id == 456
    assert item_alias.include_descendants is True


def test_concept_set_create_schema() -> None:
    """Test creation of ConceptSetCreate schema."""
    data = {"name": "My Concept Set", "items": [{"conceptId": 1}, {"conceptId": 2, "isExcluded": True}]}
    cs = ConceptSetCreate.model_validate(data)
    assert cs.name == "My Concept Set"
    assert len(cs.items) == 2
    assert cs.items[0].concept_id == 1
    assert cs.items[1].is_excluded is True


def test_concept_set_create_validation() -> None:
    """Test validation of ConceptSetCreate schema."""
    with pytest.raises(ValidationError):
        # Missing conceptId in item
        ConceptSetCreate.model_validate({"name": "Invalid Set", "items": [{"isExcluded": True}]})

    with pytest.raises(ValidationError):
        # Empty name
        ConceptSetCreate.model_validate({"name": "", "items": []})


def test_concept_set_read_schema() -> None:
    """Test ConceptSetRead schema serialization."""
    now = datetime.now()
    data = {
        "id": 1,
        "name": "Read Set",
        "createdById": 10,
        "createdDate": now,
        "items": [{"conceptSetItemId": 1, "conceptId": 100}],
    }
    cs = ConceptSetRead.model_validate(data)
    assert cs.id == 1
    assert cs.name == "Read Set"
    assert cs.created_by_id == 10
    assert cs.created_date == now
    assert len(cs.items) == 1
    assert isinstance(cs.items[0], ConceptSetItemRead)
    assert cs.items[0].concept_set_item_id == 1

    # Test serialization to JSON (camelCase)
    json_output = cs.model_dump(by_alias=True, mode="json")
    assert json_output["id"] == 1
    assert json_output["name"] == "Read Set"
    assert json_output["createdById"] == 10
    assert "items" in json_output
    assert json_output["items"][0]["conceptSetItemId"] == 1


def test_concept_set_update_schema() -> None:
    """Test ConceptSetUpdate schema."""
    # Update name only
    update1 = ConceptSetUpdate(name="New Name")
    assert update1.name == "New Name"
    assert update1.items is None

    # Update items only
    update2 = ConceptSetUpdate(name="Same Name", items=[{"conceptId": 999}])
    assert update2.items is not None
    assert len(update2.items) == 1
    assert update2.items[0].concept_id == 999
