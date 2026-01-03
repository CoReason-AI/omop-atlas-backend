# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError

from omop_atlas_backend.schemas.concept_set import ConceptSetCreate, ConceptSetUpdate
from omop_atlas_backend.services.concept_set import ConceptSetService


@pytest.mark.asyncio
async def test_create_concept_set_integrity_error_passthrough() -> None:
    """
    Unit Test: Verify that non-unique-constraint IntegrityErrors are re-raised.
    This ensures 100% coverage for the `raise e` line in `create_concept_set`.
    """
    # Mock Session
    mock_session = AsyncMock()

    # Configure flush to raise a generic IntegrityError
    error_instance = IntegrityError("INSERT failed", {"param": 1}, Exception("Generic DB Error"))
    mock_session.flush.side_effect = error_instance

    service = ConceptSetService(mock_session)

    data = ConceptSetCreate(name="Fail Set", items=[])
    user_id = 123

    with pytest.raises(IntegrityError) as exc:
        await service.create_concept_set(data, user_id)

    assert exc.value is error_instance
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_concept_set_integrity_error_passthrough() -> None:
    """
    Unit Test: Verify that non-unique-constraint IntegrityErrors are re-raised during update.
    This ensures 100% coverage for the `raise e` line in `update_concept_set`.
    """
    # Mock Session
    mock_session = AsyncMock()

    # Mock get_concept_set return value
    mock_concept_set = Mock()
    mock_concept_set.concept_set_name = "Original Name"

    # Mock query result
    mock_result = Mock()
    mock_result.scalars.return_value.first.return_value = mock_concept_set
    mock_session.execute.return_value = mock_result

    # Configure flush to raise a generic IntegrityError
    error_instance = IntegrityError("UPDATE failed", {"param": 1}, Exception("Generic DB Error"))
    mock_session.flush.side_effect = error_instance

    service = ConceptSetService(mock_session)

    update_data = ConceptSetUpdate(name="New Name", items=None)
    concept_set_id = 1

    with pytest.raises(IntegrityError) as exc:
        await service.update_concept_set(concept_set_id, update_data)

    assert exc.value is error_instance
    mock_session.rollback.assert_awaited_once()
