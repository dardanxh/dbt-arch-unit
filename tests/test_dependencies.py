from __future__ import annotations

M = "model.demo."


def test_dependencies_allow(run):
    allow = ["source > staging > marts > reporting", "marts > marts"]
    got = run("test-dependencies", config={"allow": allow})
    # reporting reads staging; marts (fct_orders) reads a source directly
    assert got == {M + "rpt_revenue", M + "fct_orders"}


def test_dependencies_deny(run):
    # blacklist mode: only the denied edge is a violation, everything else is fine
    got = run("test-dependencies", config={"deny": ["staging > marts"]})
    assert got == {M + "dim_customers", M + "fct_orders"}


def test_dependencies_deny_overrides_allow(run):
    # dim_customers is allowed by the chain but denied explicitly -> deny wins
    got = run(
        "test-dependencies",
        config={
            "allow": ["source > staging > marts > reporting", "marts > marts"],
            "deny": ["staging > marts"],
        },
    )
    assert got == {M + "dim_customers", M + "fct_orders", M + "rpt_revenue"}


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
