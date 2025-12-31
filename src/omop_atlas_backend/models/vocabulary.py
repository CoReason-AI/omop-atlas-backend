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

from sqlalchemy import BigInteger, Date, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from omop_atlas_backend.models.base import Base


# Phase 2: Vocabulary Engine
class Concept(Base):
    """
    Standard OMOP CDM Concept table.
    Contains the fundamental vocabulary data (SNOMED, RxNorm, etc.).
    """

    __tablename__ = "concept"
    __table_args__ = (
        Index("ix_concept_vocabulary_id", "vocabulary_id"),
        Index("ix_concept_domain_id", "domain_id"),
        Index("ix_concept_class_id", "concept_class_id"),
        Index("ix_concept_standard_concept", "standard_concept"),
        Index("ix_concept_code", "concept_code"),
        Index("ix_concept_name", "concept_name"),
    )

    # Read-only model
    concept_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    concept_name: Mapped[str] = mapped_column(String(255))
    domain_id: Mapped[str] = mapped_column(String(20))
    vocabulary_id: Mapped[str] = mapped_column(String(20))
    concept_class_id: Mapped[str] = mapped_column(String(20))
    standard_concept: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    concept_code: Mapped[str] = mapped_column(String(50))
    valid_start_date: Mapped[date] = mapped_column(Date)
    valid_end_date: Mapped[date] = mapped_column(Date)
    invalid_reason: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)


class Vocabulary(Base):
    """
    OMOP CDM Vocabulary table.
    Defines the source vocabularies (e.g., 'SNOMED', 'ICD10').
    """

    __tablename__ = "vocabulary"

    vocabulary_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    vocabulary_name: Mapped[str] = mapped_column(String(255))
    vocabulary_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vocabulary_version: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vocabulary_concept_id: Mapped[int] = mapped_column(Integer)


class Domain(Base):
    """
    OMOP CDM Domain table.
    Categorizes concepts into high-level domains (e.g., 'Condition', 'Drug').
    """

    __tablename__ = "domain"

    domain_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    domain_name: Mapped[str] = mapped_column(String(255))
    domain_concept_id: Mapped[int] = mapped_column(Integer)


class ConceptClass(Base):
    """
    OMOP CDM Concept Class table.
    Further categorizes concepts within a vocabulary (e.g., 'Ingredient', 'Clinical Finding').
    """

    __tablename__ = "concept_class"

    concept_class_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    concept_class_name: Mapped[str] = mapped_column(String(255))
    concept_class_concept_id: Mapped[int] = mapped_column(Integer)
