from __future__ import annotations

M = "model.demo."


def test_layer_dependencies(run):
    allow = {"staging": ["source"], "marts": ["staging", "marts"], "reporting": ["marts"]}
    got = run("layer-dependencies", config={"allow": allow})
    # reporting reads staging; marts (fct_orders) reads a source directly
    assert got == {M + "rpt_revenue", M + "fct_orders"}


def test_sources_only_in_staging(run):
    assert run("sources-only-in-staging") == {M + "fct_orders"}


def test_staging_one_source_clean(run):
    assert run("staging-one-source") == set()


def test_no_orphan_models(run):
    assert run("no-orphan-models") == {M + "orders_summary", M + "rpt_revenue"}


def test_max_fan_in(run):
    assert run("max-fan-in", config={"max": 1}) == {M + "fct_orders"}


def test_max_dependency_depth(run):
    # depths: stg=1, dim=2, fct=3, orders_summary=4, rpt=2
    assert run("max-dependency-depth", config={"max": 3}) == {M + "orders_summary"}


def test_no_model_cycles(run):
    assert run("no-model-cycles") == set()
