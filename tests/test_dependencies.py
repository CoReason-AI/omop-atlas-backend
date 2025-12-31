# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omop_atlas_backend.dependencies import get_db, get_redis


@pytest.mark.asyncio
async def test_get_db() -> None:
    """Test get_db yields a session."""
    mock_session = AsyncMock()
    mock_maker = AsyncMock(return_value=mock_session)
    # The async generator yields the session object returned by the context manager
    mock_session.__aenter__.return_value = "session"

    with patch("omop_atlas_backend.dependencies.async_session_maker", return_value=mock_session):
        gen = get_db()
        session = await anext(gen)
        assert session == "session"


@pytest.mark.asyncio
async def test_get_redis() -> None:
    """Test get_redis yields a redis client."""
    mock_client = AsyncMock()
    # Mock the Redis class so from_url returns our async mock client synchronously
    mock_redis_cls = MagicMock()
    mock_redis_cls.from_url.return_value = mock_client

    with patch("omop_atlas_backend.dependencies.Redis", mock_redis_cls):
        gen = get_redis()
        client = await anext(gen)
        assert client is mock_client

        # Verify cleanup
        try:
            await anext(gen)
        except StopAsyncIteration:
            pass

        assert mock_client.aclose.called

@pytest.mark.asyncio
async def test_get_redis_failure() -> None:
    """Test get_redis yields None on failure."""
    mock_redis_cls = MagicMock()
    mock_redis_cls.from_url.side_effect = Exception("Connection failed")

    with patch("omop_atlas_backend.dependencies.Redis", mock_redis_cls):
        gen = get_redis()
        client = await anext(gen)
        assert client is None

        # Verify generator exits
        with pytest.raises(StopAsyncIteration):
            await anext(gen)
