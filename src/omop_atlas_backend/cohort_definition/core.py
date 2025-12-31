# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from enum import StrEnum
from typing import Optional, Union

from pydantic import Field

from omop_atlas_backend.cohort_definition.base import CirceModel


class NumericOp(StrEnum):
    GT = "gt"  # Greater than
    LT = "lt"  # Less than
    EQ = "eq"  # Equal to
    LTE = "lte"  # Less than or equal to
    GTE = "gte"  # Greater than or equal to
    BT = "bt"  # Between
    NOT_BT = "!bt"  # Not between


class TextOp(StrEnum):
    CONTAINS = "contains"
    START_WITH = "startsWith"
    ENDS_WITH = "endsWith"
    NOT_CONTAINS = "!contains"
    NOT_START_WITH = "!startsWith"
    NOT_ENDS_WITH = "!endsWith"


class TextFilter(CirceModel):
    text: str
    op: TextOp = TextOp.CONTAINS


class NumericRange(CirceModel):
    value: Union[float, int]
    op: NumericOp
    extent: Optional[Union[float, int]] = None


class DateRange(CirceModel):
    value: str  # YYYY-MM-DD
    op: NumericOp
    extent: Optional[str] = None  # YYYY-MM-DD


class Period(CirceModel):
    start_date: str
    end_date: str
