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
    ConceptSetRead,
    ConceptSetUpdate,
)


def test_concept_set_item_create_schema() -> None:
    """Test creation and validation of ConceptSetItemCreate."""
    data = {"conceptId": 123, "isExcluded": True, "includeDescendants": True, "includeMapped": False}
    item = ConceptSetItemCreate(**data)
    assert item.concept_id == 123
    assert item.is_excluded is True
    assert item.include_descendants is True
    assert item.include_mapped is False

    # Test defaults
    item_default = ConceptSetItemCreate(concept_id=456)
    assert item_default.is_excluded is False
    assert item_default.include_descendants is False
    assert item_default.include_mapped is False


def test_concept_set_create_schema() -> None:
    """Test creation and validation of ConceptSetCreate."""
    item_data = {"conceptId": 1}
    cs_data = {"name": "Test Set", "items": [item_data]}
    cs = ConceptSetCreate(**cs_data)
    assert cs.name == "Test Set"
    assert len(cs.items) == 1
    assert cs.items[0].concept_id == 1

    # Test validation
    with pytest.raises(ValidationError):
        ConceptSetCreate(name="")  # Too short


def test_concept_set_read_schema() -> None:
    """Test ConceptSetRead schema."""
    now = datetime.now()
    item_read_data = {
        "conceptId": 1,
        "conceptSetItemId": 10,
        "isExcluded": False,
        "includeDescendants": False,
        "includeMapped": False,
        "concept": {
            "conceptId": 1,
            "conceptName": "Test",
            "domainId": "Condition",
            "vocabularyId": "SNOMED",
            "conceptClassId": "Clinical Finding",
            "conceptCode": "12345",
            "validStartDate": "2020-01-01",
            "validEndDate": "2099-12-31",
        },
    }

    data = {"id": 100, "name": "My Set", "createdById": 5, "createdDate": now, "items": [item_read_data]}

    cs_read = ConceptSetRead(**data)
    assert cs_read.id == 100
    assert cs_read.items[0].concept_set_item_id == 10
    assert cs_read.items[0].concept is not None
    assert cs_read.items[0].concept.concept_name == "Test"


def test_concept_set_update_schema() -> None:
    """Test ConceptSetUpdate schema."""
    update_data = {"name": "New Name"}
    update = ConceptSetUpdate(**update_data)
    assert update.name == "New Name"
    assert update.items is None

    update_items = ConceptSetUpdate(name="Name", items=[{"conceptId": 1}])
    assert update_items.items is not None
    assert len(update_items.items) == 1
