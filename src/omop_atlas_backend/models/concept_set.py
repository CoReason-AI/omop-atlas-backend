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
Phase 3: Concept Sets - Models
Defines the ConceptSet and ConceptSetItem models.
"""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omop_atlas_backend.models.base import Base
from omop_atlas_backend.models.security import User
from omop_atlas_backend.models.vocabulary import Concept


class ConceptSet(Base):
    """
    Represents a collection of OMOP Concepts.
    Used for Cohort Definitions and other analytic assets.
    """

    __tablename__ = "concept_set"

    concept_set_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_set_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_date: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    created_by: Mapped["User"] = relationship()
    items: Mapped[List["ConceptSetItem"]] = relationship(
        back_populates="concept_set", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ConceptSet(id={self.concept_set_id}, name='{self.concept_set_name}')>"


class ConceptSetItem(Base):
    """
    A single item within a Concept Set.
    Links a Concept Set to a specific Concept, with inclusion rules.
    """

    __tablename__ = "concept_set_item"

    concept_set_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_set_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("concept_set.concept_set_id"), nullable=False, index=True
    )
    concept_id: Mapped[int] = mapped_column(Integer, ForeignKey("concept.concept_id"), nullable=False, index=True)

    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    include_descendants: Mapped[bool] = mapped_column(Boolean, default=False)
    include_mapped: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    concept_set: Mapped["ConceptSet"] = relationship(back_populates="items")
    concept: Mapped["Concept"] = relationship()

    def __repr__(self) -> str:
        return f"<ConceptSetItem(id={self.concept_set_item_id}, concept_id={self.concept_id})>"
