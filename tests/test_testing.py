from __future__ import annotations

M = "model.demo."
MARTS = ["models/marts/**"]


def test_min_tests_per_model(run):
    got = run("min-tests-per-model", include=MARTS, config={"min": 1})
    assert got == {M + "fct_orders", M + "orders_summary"}


def test_require_primary_key(run):
    got = run("require-primary-key", include=MARTS)
    assert got == {M + "fct_orders", M + "orders_summary"}


def test_require_unit_tests(run):
    got = run("require-unit-tests", include=MARTS)
    assert got == {M + "fct_orders", M + "orders_summary"}


def test_source_freshness(run):
    assert run("source-freshness") == {"source.demo.raw.orders"}


def test_no_disabled_nodes(run):
    assert run("no-disabled-nodes") == {"model.demo.deprecated_model"}


def test_require_contract(run):
    got = run("require-contract", include=MARTS)
    assert got == {M + "fct_orders", M + "orders_summary"}
