# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from omop_atlas_backend.cohort_definition.core import (
    DateRange,
    NumericOp,
    NumericRange,
    Period,
    TextFilter,
    TextOp,
)


def test_text_filter_serialization() -> None:
    tf = TextFilter(text="aspirin", op=TextOp.START_WITH)
    json_output = tf.model_dump(by_alias=True)

    assert json_output["text"] == "aspirin"
    assert json_output["op"] == "startsWith"


def test_text_filter_deserialization() -> None:
    data = {"text": "tylenol", "op": "!contains"}
    tf = TextFilter.model_validate(data)

    assert tf.text == "tylenol"
    assert tf.op == TextOp.NOT_CONTAINS


def test_numeric_range_serialization() -> None:
    nr = NumericRange(value=10, op=NumericOp.GT)
    json_output = nr.model_dump(by_alias=True)

    assert json_output["value"] == 10
    assert json_output["op"] == "gt"
    assert "extent" not in json_output or json_output["extent"] is None


def test_numeric_range_between_serialization() -> None:
    nr = NumericRange(value=5, op=NumericOp.BT, extent=10)
    json_output = nr.model_dump(by_alias=True)

    assert json_output["value"] == 5
    assert json_output["op"] == "bt"
    assert json_output["extent"] == 10


def test_numeric_range_deserialization() -> None:
    data = {"value": 100, "op": "lte"}
    nr = NumericRange.model_validate(data)

    assert nr.value == 100
    assert nr.op == NumericOp.LTE
    assert nr.extent is None


def test_date_range_serialization() -> None:
    dr = DateRange(value="2023-01-01", op=NumericOp.EQ)
    json_output = dr.model_dump(by_alias=True)

    assert json_output["value"] == "2023-01-01"
    assert json_output["op"] == "eq"


def test_period_serialization() -> None:
    p = Period(start_date="2023-01-01", end_date="2023-12-31")
    json_output = p.model_dump(by_alias=True)

    # Check camelCase conversion
    assert json_output["startDate"] == "2023-01-01"
    assert json_output["endDate"] == "2023-12-31"


def test_period_deserialization() -> None:
    data = {"startDate": "2022-01-01", "endDate": "2022-06-30"}
    p = Period.model_validate(data)

    assert p.start_date == "2022-01-01"
    assert p.end_date == "2022-06-30"


def test_snake_case_input_works_with_populate_by_name() -> None:
    """Ensure we can instantiate models using snake_case arguments in Python"""
    p = Period(start_date="2023-01-01", end_date="2023-01-31")
    assert p.start_date == "2023-01-01"
