from __future__ import annotations

M = "model.demo."
MARTS = ["models/marts/**"]


def test_materialization_by_layer(run):
    allow = {"staging": ["view"], "marts": ["table"]}
    assert run("materialization-by-layer", config={"allow": allow}) == {M + "stg_orders"}


def test_incremental_requires_keys(run):
    assert run("incremental-requires-keys") == {M + "rpt_revenue"}


def test_require_tags_by_layer(run):
    got = run("require-tags-by-layer", include=MARTS, config={"required": {"marts": ["governed"]}})
    assert got == {M + "fct_orders", M + "orders_summary"}


def test_custom_schema_required(run):
    assert run("custom-schema-required") == {M + "orders_summary"}


def test_max_ephemeral_models_none(run):
    assert run("max-ephemeral-models", config={"max": 0}) == set()
