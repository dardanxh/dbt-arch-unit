from __future__ import annotations

M = "model.demo."


def test_model_has_description(run):
    assert run("expect-model-has-description") == {M + "stg_orders"}


def test_column_has_description_clean(run):
    # every documented column in the fixture has a description
    assert run("expect-column-has-description", include=["models/marts/**"]) == set()


def test_exposure_has_owner(run):
    assert "exposure.demo.broken_dashboard" in run("expect-exposure-has-owner")


def test_model_has_owner_meta(run):
    got = run("expect-model-has-owner-meta")
    assert M + "fct_orders" in got
    assert M + "dim_customers" not in got
