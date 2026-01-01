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

from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omop_atlas_backend.models.base import Base
from omop_atlas_backend.models.security import User
from omop_atlas_backend.models.vocabulary import Concept


class ConceptSet(Base):
    """
    Concept Set Model.
    Represents a collection of concepts used in cohort definitions.
    Maps to 'concept_set' table.
    """

    __tablename__ = "concept_set"

    concept_set_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_set_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # CommonEntity Fields
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    modified_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    modified_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    modified_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[modified_by_id])

    items: Mapped[List["ConceptSetItem"]] = relationship(
        "ConceptSetItem", back_populates="concept_set", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ConceptSet(id={self.concept_set_id}, name='{self.concept_set_name}')>"


class ConceptSetItem(Base):
    """
    Concept Set Item Model.
    Represents a single concept within a concept set, including inclusion/exclusion rules.
    Maps to 'concept_set_item' table.
    """

    __tablename__ = "concept_set_item"

    concept_set_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_set_id: Mapped[int] = mapped_column(ForeignKey("concept_set.concept_set_id"))
    concept_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("concept.concept_id"))

    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    include_descendants: Mapped[bool] = mapped_column(Boolean, default=False)
    include_mapped: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    concept_set: Mapped["ConceptSet"] = relationship("ConceptSet", back_populates="items")
    concept: Mapped["Concept"] = relationship("Concept")

    def __repr__(self) -> str:
        return f"<ConceptSetItem(id={self.concept_set_item_id}, concept_id={self.concept_id})>"
