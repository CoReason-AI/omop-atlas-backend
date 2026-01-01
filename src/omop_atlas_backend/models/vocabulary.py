# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Concept(Base):
    __tablename__ = "concept"

    concept_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_name: Mapped[str] = mapped_column(String(255), index=True)
    domain_id: Mapped[str] = mapped_column(String(20), ForeignKey("domain.domain_id"), index=True)
    vocabulary_id: Mapped[str] = mapped_column(String(20), ForeignKey("vocabulary.vocabulary_id"), index=True)
    concept_class_id: Mapped[str] = mapped_column(String(20), ForeignKey("concept_class.concept_class_id"), index=True)
    standard_concept: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    concept_code: Mapped[str] = mapped_column(String(50), index=True)
    valid_start_date: Mapped[date] = mapped_column(Date)
    valid_end_date: Mapped[date] = mapped_column(Date)
    invalid_reason: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)

    # Relationships
    domain: Mapped["Domain"] = relationship(back_populates="concepts")
    vocabulary: Mapped["Vocabulary"] = relationship(back_populates="concepts")
    concept_class: Mapped["ConceptClass"] = relationship(back_populates="concepts")


class Vocabulary(Base):
    __tablename__ = "vocabulary"

    vocabulary_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    vocabulary_name: Mapped[str] = mapped_column(String(255))
    vocabulary_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vocabulary_version: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vocabulary_concept_id: Mapped[int] = mapped_column(Integer)

    # Relationships
    concepts: Mapped[list["Concept"]] = relationship(back_populates="vocabulary")


class Domain(Base):
    __tablename__ = "domain"

    domain_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    domain_name: Mapped[str] = mapped_column(String(255))
    domain_concept_id: Mapped[int] = mapped_column(Integer)

    # Relationships
    concepts: Mapped[list["Concept"]] = relationship(back_populates="domain")


class ConceptClass(Base):
    __tablename__ = "concept_class"

    concept_class_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    concept_class_name: Mapped[str] = mapped_column(String(255))
    concept_class_concept_id: Mapped[int] = mapped_column(Integer)

    # Relationships
    concepts: Mapped[list["Concept"]] = relationship(back_populates="concept_class")
