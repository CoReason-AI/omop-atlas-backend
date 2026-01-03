# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from omop_atlas_backend.api import concept_set, vocabulary
from omop_atlas_backend.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting omop-atlas-backend...")
    yield
    logger.info("Shutting down omop-atlas-backend...")


app = FastAPI(
    title="OMOP ATLAS Backend",
    description="Modern Python port of OHDSI WebAPI",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(vocabulary.router)
app.include_router(concept_set.router)


@app.get("/")
def hello_world() -> dict[str, str]:
    logger.info("Hello World!")
    return {"message": "Hello World!"}
