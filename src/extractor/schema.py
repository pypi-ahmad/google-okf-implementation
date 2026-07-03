"""Pydantic schemas for enterprise concept extraction."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityConcept(BaseModel):
    """Business or technical entity definition."""

    name: str
    description: str
    aliases: list[str] = Field(default_factory=list)
    owner: str | None = None
    tags: list[str] = Field(default_factory=list)


class DatasetConcept(BaseModel):
    """Dataset-level concept in the enterprise knowledge base."""

    name: str
    description: str
    owner: str | None = None
    columns: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class APIConcept(BaseModel):
    """API concept and key operational details."""

    name: str
    description: str
    endpoint: str | None = None
    method: str | None = None
    owner: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class TableConcept(BaseModel):
    """Relational table concept."""

    name: str
    description: str
    schema_name: str | None = None
    columns: list[str] = Field(default_factory=list)
    owner: str | None = None
    tags: list[str] = Field(default_factory=list)


class MetricConcept(BaseModel):
    """Business metric definition and dependencies."""

    name: str
    description: str
    formula: str | None = None
    owner: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class GlossaryTermConcept(BaseModel):
    """Glossary term used across documentation."""

    term: str
    definition: str
    related_terms: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class EnterpriseConcepts(BaseModel):
    """Top-level structured extraction output for enterprise documents."""

    entities: list[EntityConcept] = Field(default_factory=list)
    datasets: list[DatasetConcept] = Field(default_factory=list)
    apis: list[APIConcept] = Field(default_factory=list)
    tables: list[TableConcept] = Field(default_factory=list)
    metrics: list[MetricConcept] = Field(default_factory=list)
    glossary_terms: list[GlossaryTermConcept] = Field(default_factory=list)
