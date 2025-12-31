# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

import pytest
from datetime import date
from sqlalchemy import select
from src.omop_atlas_backend.models.vocabulary import Base, Concept, Vocabulary, Domain, ConceptClass

@pytest.mark.asyncio
async def test_vocabulary_models_creation(async_engine, async_session):
    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Test Concept Model
    concept = Concept(
        concept_id=1,
        concept_name="Test Concept",
        domain_id="Condition",
        vocabulary_id="SNOMED",
        concept_class_id="Clinical Finding",
        standard_concept="S",
        concept_code="12345",
        valid_start_date=date(2020, 1, 1),
        valid_end_date=date(2099, 12, 31),
        invalid_reason=None
    )
    async_session.add(concept)

    # Test Vocabulary Model
    vocab = Vocabulary(
        vocabulary_id="SNOMED",
        vocabulary_name="SNOMED Clinical Terms",
        vocabulary_reference="http://snomed.info",
        vocabulary_version="2023-01",
        vocabulary_concept_id=44819096
    )
    async_session.add(vocab)

    # Test Domain Model
    domain = Domain(
        domain_id="Condition",
        domain_name="Condition",
        domain_concept_id=19
    )
    async_session.add(domain)

    # Test ConceptClass Model
    c_class = ConceptClass(
        concept_class_id="Clinical Finding",
        concept_class_name="Clinical Finding",
        concept_class_concept_id=123
    )
    async_session.add(c_class)

    await async_session.commit()

    # Query back to verify
    stmt = select(Concept).where(Concept.concept_id == 1)
    result = await async_session.execute(stmt)
    fetched_concept = result.scalar_one()

    assert fetched_concept.concept_name == "Test Concept"
    assert fetched_concept.valid_start_date == date(2020, 1, 1)

    stmt = select(Vocabulary).where(Vocabulary.vocabulary_id == "SNOMED")
    result = await async_session.execute(stmt)
    fetched_vocab = result.scalar_one()
    assert fetched_vocab.vocabulary_name == "SNOMED Clinical Terms"

    stmt = select(Domain).where(Domain.domain_id == "Condition")
    result = await async_session.execute(stmt)
    fetched_domain = result.scalar_one()
    assert fetched_domain.domain_name == "Condition"

    stmt = select(ConceptClass).where(ConceptClass.concept_class_id == "Clinical Finding")
    result = await async_session.execute(stmt)
    fetched_class = result.scalar_one()
    assert fetched_class.concept_class_name == "Clinical Finding"
