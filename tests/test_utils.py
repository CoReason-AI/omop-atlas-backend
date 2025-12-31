# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

import sys
import importlib
from pathlib import Path
from unittest.mock import patch, MagicMock
from omop_atlas_backend.utils import logger as logger_module
from omop_atlas_backend.utils.logger import logger

def test_logger_initialization():
    """Test that the logger is initialized correctly and creates the log directory."""
    # Since the logger is initialized on import, we check side effects

    # Check if logs directory creation is handled
    # Note: running this test might actually create the directory in the test environment
    # if it doesn't exist.

    log_path = Path("logs")
    assert log_path.exists()
    assert log_path.is_dir()

def test_logger_exports():
    """Test that logger is exported."""
    assert logger is not None

def test_logger_creates_directory():
    """Test that the logger creates the directory if it doesn't exist."""
    with patch("pathlib.Path") as MockPath:
        mock_path_instance = MockPath.return_value
        # First call to exists() returns False (check), subsequent calls might matter but only first matters for if block
        mock_path_instance.exists.return_value = False

        # Reload the module to trigger the code at module level
        importlib.reload(logger_module)

        # Verify mkdir was called
        # We need to find the call on the specific instance that was created with "logs"
        # Since Path("logs") creates a new instance

        # Check if any instance created called mkdir
        # MockPath is the class. MockPath("logs") returns an instance.
        # We want to check if that instance had mkdir called.

        # We can inspect all calls to the class
        # But simpler: MockPath.return_value matches ANY instance created if side_effect is not set

        mock_path_instance.mkdir.assert_called_with(parents=True, exist_ok=True)

    # Reload again to restore normal state for other tests if needed
    importlib.reload(logger_module)
