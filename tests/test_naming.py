from __future__ import annotations

M = "model.demo."


def test_layer_name_prefix(run):
    assert run("layer-name-prefix") == {M + "orders_summary"}


def test_directory_prefix_match_clean(run):
    # nothing is misfiled in the fixture
    assert run("directory-prefix-match") == set()


def test_staging_name_matches_source(run):
    got = run("staging-name-matches-source", severity="warning")
    assert got == {M + "stg_customers", M + "stg_orders"}


def test_model_name_regex_forbid(run):
    assert run("model-name-regex", config={"forbid": ["summary"]}) == {M + "orders_summary"}
