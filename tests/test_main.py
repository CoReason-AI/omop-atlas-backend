# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from unittest.mock import patch

from fastapi.testclient import TestClient

from omop_atlas_backend.main import app, hello_world


def test_hello_world() -> None:
    assert hello_world() == {"message": "Hello World!"}


def test_lifespan() -> None:
    """Test that lifespan logs startup and shutdown events."""
    with patch("omop_atlas_backend.main.logger") as mock_logger:
        with TestClient(app) as client:
            client.get("/")  # Trigger startup
            assert mock_logger.info.called
            args, _ = mock_logger.info.call_args_list[0]
            assert "Starting" in args[0]

        # Trigger shutdown
        assert mock_logger.info.call_count >= 2
        args, _ = mock_logger.info.call_args_list[-1]
        assert "Shutting down" in args[0]
