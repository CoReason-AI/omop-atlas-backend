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
    synonyms: Mapped[list["ConceptSynonym"]] = relationship(back_populates="concept")


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


class Relationship(Base):
    __tablename__ = "relationship"

    relationship_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    relationship_name: Mapped[str] = mapped_column(String(255))
    is_hierarchical: Mapped[str] = mapped_column(String(1))
    defines_ancestry: Mapped[str] = mapped_column(String(1))
    reverse_relationship_id: Mapped[str] = mapped_column(String(20))
    relationship_concept_id: Mapped[int] = mapped_column(Integer)


class ConceptRelationship(Base):
    __tablename__ = "concept_relationship"

    concept_id_1: Mapped[int] = mapped_column(Integer, ForeignKey("concept.concept_id"), primary_key=True)
    concept_id_2: Mapped[int] = mapped_column(Integer, ForeignKey("concept.concept_id"), primary_key=True)
    relationship_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("relationship.relationship_id"), primary_key=True
    )
    valid_start_date: Mapped[date] = mapped_column(Date)
    valid_end_date: Mapped[date] = mapped_column(Date)
    invalid_reason: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)

    # Relationships
    concept_1: Mapped["Concept"] = relationship(foreign_keys=[concept_id_1])
    concept_2: Mapped["Concept"] = relationship(foreign_keys=[concept_id_2])
    relationship_rel: Mapped["Relationship"] = relationship()


class ConceptAncestor(Base):
    __tablename__ = "concept_ancestor"

    ancestor_concept_id: Mapped[int] = mapped_column(Integer, ForeignKey("concept.concept_id"), primary_key=True)
    descendant_concept_id: Mapped[int] = mapped_column(Integer, ForeignKey("concept.concept_id"), primary_key=True)
    min_levels_of_separation: Mapped[int] = mapped_column(Integer)
    max_levels_of_separation: Mapped[int] = mapped_column(Integer)

    # Relationships
    ancestor_concept: Mapped["Concept"] = relationship(foreign_keys=[ancestor_concept_id])
    descendant_concept: Mapped["Concept"] = relationship(foreign_keys=[descendant_concept_id])


class ConceptSynonym(Base):
    __tablename__ = "concept_synonym"

    concept_id: Mapped[int] = mapped_column(Integer, ForeignKey("concept.concept_id"), primary_key=True)
    concept_synonym_name: Mapped[str] = mapped_column(String(1000), primary_key=True)
    language_concept_id: Mapped[int] = mapped_column(Integer)

    # Relationships
    concept: Mapped["Concept"] = relationship(back_populates="synonyms")
