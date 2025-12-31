# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CirceModel(BaseModel):
    """
    Base model for all Circe objects.
    Handles CamelCase (JSON) <-> snake_case (Python) conversion automatically.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",  # Ignore extra fields to be forward compatible
    )
