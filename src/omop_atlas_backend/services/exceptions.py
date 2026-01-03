# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

"""
Service Layer Exceptions
"""


class ConceptNotFound(Exception):
    """Raised when a requested concept is not found."""

    def __init__(self, concept_id: int | str):
        self.concept_id = concept_id
        super().__init__(f"Concept with ID {concept_id} not found.")


class DuplicateResourceError(Exception):
    """Raised when a resource already exists."""

    pass


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass
