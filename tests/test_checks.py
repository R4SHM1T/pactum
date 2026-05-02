import pandas as pd

from pactum import checks
from pactum.results import Severity


def test_not_null_flags_missing():
    df = pd.DataFrame({"a": [1, None, 3]})
    res = checks.NotNullCheck(column="a").run(df, {})
    assert not res.passed
    assert res.failing_rows == 1


def test_unique_flags_duplicates():
    df = pd.DataFrame({"id": [1, 2, 2, 3]})
    res = checks.UniqueCheck(column="id").run(df, {})
    assert res.failing_rows == 2


def test_range_flags_out_of_bounds():
    df = pd.DataFrame({"amt": [-1.0, 5.0, 11.0]})
    res = checks.RangeCheck(column="amt", min=0, max=10).run(df, {})
    assert res.failing_rows == 2


def test_allowed_values():
    df = pd.DataFrame({"s": ["a", "b", "z"]})
    res = checks.AllowedValuesCheck(column="s", values=["a", "b"]).run(df, {})
    assert res.failing_rows == 1


def test_regex_skips_nulls():
    df = pd.DataFrame({"e": ["a@b.com", "bad", None]})
    res = checks.RegexCheck(column="e", pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$").run(df, {})
    assert res.failing_rows == 1


def test_dtype_integer_rejects_fraction_and_text():
    df = pd.DataFrame({"n": ["1", "2.5", "x", None]})
    res = checks.DTypeCheck(column="n", dtype="integer").run(df, {})
    assert res.failing_rows == 2


def test_dtype_datetime():
    df = pd.DataFrame({"d": ["2026-01-01", "nonsense", None]})
    res = checks.DTypeCheck(column="d", dtype="datetime").run(df, {})
    assert res.failing_rows == 1


def test_row_count_bounds():
    df = pd.DataFrame({"a": [1, 2]})
    assert checks.RowCountCheck(min=1).run(df, {}).passed
    assert not checks.RowCountCheck(min=5).run(df, {}).passed


def test_relationship_uses_context():
    orders = pd.DataFrame({"cid": [1, 2, 99]})
    customers = pd.DataFrame({"cid": [1, 2, 3]})
    res = checks.RelationshipCheck(
        column="cid", ref_contract="customers", ref_column="cid"
    ).run(orders, {"customers": customers})
    assert res.failing_rows == 1
    assert res.sample == [99]


def test_relationship_without_context_fails():
    orders = pd.DataFrame({"cid": [1]})
    res = checks.RelationshipCheck(
        column="cid", ref_contract="customers", ref_column="cid"
    ).run(orders, {})
    assert not res.passed


def test_expression_flags_violations():
    df = pd.DataFrame({"status": ["paid", "paid"], "amount": [10, 0]})
    res = checks.ExpressionCheck(
        expression="not (status == 'paid' and amount <= 0)"
    ).run(df, {})
    assert res.failing_rows == 1


def test_missing_column_returns_none():
    df = pd.DataFrame({"a": [1]})
    assert checks.NotNullCheck(column="zzz").run(df, {}) is None


def test_freshness_warns_when_stale():
    df = pd.DataFrame({"ts": ["2000-01-01T00:00:00Z"]})
    res = checks.FreshnessCheck(
        column="ts", max_age="1d", severity=Severity.WARN
    ).run(df, {})
    assert not res.passed
    assert res.severity is Severity.WARN
