"""Pydantic models for the subset of dbt's manifest.json we rely on.

Pydantic v2 ignores unknown fields by default, so we only declare what the rules
actually consume. This keeps us resilient across dbt versions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Column(BaseModel):
    name: str
    description: str = ""
    data_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class Contract(BaseModel):
    enforced: bool = False


class NodeConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    materialized: str | None = None
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    unique_key: str | list[str] | None = None
    on_schema_change: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    group: str | None = None
    contract: Contract = Field(default_factory=Contract)


class DependsOn(BaseModel):
    nodes: list[str] = Field(default_factory=list)
    macros: list[str] = Field(default_factory=list)


class TestMetadata(BaseModel):
    name: str
    kwargs: dict[str, Any] = Field(default_factory=dict)


class Node(BaseModel):
    """A model, test, seed, snapshot or analysis node."""

    unique_id: str
    name: str
    resource_type: str
    package_name: str = ""
    path: str = ""
    original_file_path: str = ""
    fqn: list[str] = Field(default_factory=list)
    alias: str | None = None
    description: str = ""
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    columns: dict[str, Column] = Field(default_factory=dict)
    config: NodeConfig = Field(default_factory=NodeConfig)
    depends_on: DependsOn = Field(default_factory=DependsOn)
    raw_code: str = ""

    # test-only fields
    test_metadata: TestMetadata | None = None
    attached_node: str | None = None
    column_name: str | None = None

    model_config = ConfigDict(populate_by_name=True)

    @property
    def is_model(self) -> bool:
        return self.resource_type == "model"

    @property
    def is_test(self) -> bool:
        return self.resource_type == "test"


class Freshness(BaseModel):
    warn_after: dict[str, Any] | None = None
    error_after: dict[str, Any] | None = None


class Source(BaseModel):
    unique_id: str
    name: str
    source_name: str
    resource_type: str = "source"
    path: str = ""
    original_file_path: str = ""
    fqn: list[str] = Field(default_factory=list)
    description: str = ""
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    columns: dict[str, Column] = Field(default_factory=dict)
    loaded_at_field: str | None = None
    freshness: Freshness | None = None

    model_config = ConfigDict(populate_by_name=True)

    @property
    def has_freshness(self) -> bool:
        return self.freshness is not None and (
            self.freshness.warn_after is not None or self.freshness.error_after is not None
        )


class Owner(BaseModel):
    name: str | None = None
    email: str | None = None


class Exposure(BaseModel):
    unique_id: str
    name: str
    resource_type: str = "exposure"
    original_file_path: str = ""
    type: str | None = None
    owner: Owner = Field(default_factory=Owner)
    depends_on: DependsOn = Field(default_factory=DependsOn)


class UnitTest(BaseModel):
    unique_id: str
    name: str
    model: str | None = None
    depends_on: DependsOn = Field(default_factory=DependsOn)


class Manifest(BaseModel):
    """The full manifest, trimmed to the parts the rules read."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    nodes: dict[str, Node] = Field(default_factory=dict)
    sources: dict[str, Source] = Field(default_factory=dict)
    exposures: dict[str, Exposure] = Field(default_factory=dict)
    unit_tests: dict[str, UnitTest] = Field(default_factory=dict)
    disabled: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    child_map: dict[str, list[str]] = Field(default_factory=dict)
    parent_map: dict[str, list[str]] = Field(default_factory=dict)
