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
from typing import List

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omop_atlas_backend.models.base import Base


class ConceptSet(Base):
    """
    Concept Set definition.
    A collection of concepts used to define a cohort or feature.
    """

    __tablename__ = "concept_set"

    concept_set_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    concept_set_name: Mapped[str] = mapped_column(String(255))
    created_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    modified_date: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    created_by: Mapped[str] = mapped_column(String(255), nullable=True)  # User ID or Name
    modified_by: Mapped[str] = mapped_column(String(255), nullable=True)

    items: Mapped[List["ConceptSetItem"]] = relationship(
        "ConceptSetItem", back_populates="concept_set", cascade="all, delete-orphan"
    )


class ConceptSetItem(Base):
    """
    Individual item within a Concept Set.
    Links a specific Concept ID with inclusion/exclusion logic.
    """

    __tablename__ = "concept_set_item"

    concept_set_item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    concept_set_id: Mapped[int] = mapped_column(Integer, ForeignKey("concept_set.concept_set_id"), nullable=False)
    concept_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    include_descendants: Mapped[bool] = mapped_column(Boolean, default=False)
    include_mapped: Mapped[bool] = mapped_column(Boolean, default=False)

    concept_set: Mapped["ConceptSet"] = relationship("ConceptSet", back_populates="items")
