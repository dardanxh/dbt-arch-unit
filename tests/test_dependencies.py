from __future__ import annotations

M = "model.demo."


def test_dependencies_allow(run):
    allow = ["source > staging > marts > reporting", "marts > marts"]
    got = run("expect-dependencies", config={"allow": allow})
    # reporting reads staging; marts (fct_orders) reads a source directly
    assert got == {M + "rpt_revenue", M + "fct_orders"}


def test_dependencies_deny(run):
    # blacklist mode: only the denied edge is a violation, everything else is fine
    got = run("expect-dependencies", config={"deny": ["staging > marts"]})
    assert got == {M + "dim_customers", M + "fct_orders"}


def test_dependencies_deny_overrides_allow(run):
    # dim_customers is allowed by the chain but denied explicitly -> deny wins
    got = run(
        "expect-dependencies",
        config={
            "allow": ["source > staging > marts > reporting", "marts > marts"],
            "deny": ["staging > marts"],
        },
    )
    assert got == {M + "dim_customers", M + "fct_orders", M + "rpt_revenue"}


# Fixture layer sizes: staging=2, marts=3, reporting=1.


def test_max_models_per_layer_scoped_over(run):
    # cap applies only to the scoped layer(s); marts has 3 > 2
    got = run("expect-max-models-per-layer", scope=["marts"], config={"max": 2})
    assert got == {"layer:marts"}


def test_max_models_per_layer_ignore(run):
    # check every layer except staging; only marts (3) exceeds 2
    got = run("expect-max-models-per-layer", ignore=["staging"], config={"max": 2})
    assert got == {"layer:marts"}


def test_max_models_per_layer_within_limit(run):
    got = run("expect-max-models-per-layer", scope=["reporting", "staging"], config={"max": 2})
    assert got == set()


def test_sources_only_in_staging(run):
    assert run("expect-sources-single-reader") == {M + "fct_orders"}


def test_staging_one_source_clean(run):
    assert run("expect-single-source-per-model") == set()


def test_no_orphan_models(run):
    assert run("expect-no-orphan-models") == {M + "orders_summary", M + "rpt_revenue"}


def test_max_fan_in(run):
    assert run("expect-max-fan-in", config={"max": 1}) == {M + "fct_orders"}


def test_max_dependency_depth(run):
    # depths: stg=1, dim=2, fct=3, orders_summary=4, rpt=2
    assert run("expect-max-dependency-depth", config={"max": 3}) == {M + "orders_summary"}


def test_no_model_cycles(run):
    assert run("expect-no-model-cycles") == set()
