from __future__ import annotations

from dbt_arch_unit.parsers.sql_parser import ParsedSql


def test_loc_ignores_comments_and_blanks():
    sql = "select 1\n\n-- a comment\nfrom t\n"
    assert ParsedSql(sql).loc(ignore_comments=True) == 2
    assert ParsedSql(sql).loc(ignore_comments=False) == 3


def test_cte_names():
    sql = "with a as (select 1), b as (select 2) select * from a"
    assert ParsedSql(sql).cte_names == ["a", "b"]


def test_join_count():
    sql = "select * from a join b on 1=1 left join c on 2=2"
    assert ParsedSql(sql).join_count == 2


def test_select_star_final_only():
    inside = "with x as (select * from t) select id from x"
    assert ParsedSql(inside).has_select_star(allow_in_ctes=True) is False
    assert ParsedSql(inside).has_select_star(allow_in_ctes=False) is True
    final = "with x as (select id from t) select * from x"
    assert ParsedSql(final).has_select_star(allow_in_ctes=True) is True


def test_final_column_count():
    sql = "select a, b, coalesce(c, 0) as c from t"
    assert ParsedSql(sql).final_column_count == 3


def test_hardcoded_and_cross_db_refs():
    sql = "select * from analytics.public.orders join {{ ref('x') }} on 1=1"
    parsed = ParsedSql(sql)
    assert parsed.hardcoded_refs == ["analytics.public.orders"]
    assert parsed.cross_database_refs == ["analytics.public.orders"]


def test_jinja_ref_not_hardcoded():
    sql = "select * from {{ ref('stg_orders') }}"
    assert ParsedSql(sql).hardcoded_refs == []
