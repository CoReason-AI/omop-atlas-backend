# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from omop_atlas_backend.schemas.concept_set import ConceptSetCreate
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
    # The error message should NOT contain "concept_set_name" or "UNIQUE constraint failed"
    error_instance = IntegrityError("INSERT failed", {"param": 1}, Exception("Generic DB Error"))
    mock_session.flush.side_effect = error_instance

    service = ConceptSetService(mock_session)

    data = ConceptSetCreate(name="Fail Set", items=[])
    user_id = 123

    with pytest.raises(IntegrityError) as exc:
        await service.create_concept_set(data, user_id)

    assert exc.value is error_instance

    # Verify rollback was called
    mock_session.rollback.assert_awaited_once()
