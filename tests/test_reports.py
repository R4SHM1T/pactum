from pactum import Contract, validate
from pactum.reports import render_console, render_html, render_json
import pandas as pd


def _report():
    contract = Contract.from_dict(
        {"name": "orders", "columns": [{"name": "id", "unique": True}]}
    )
    return validate(contract, pd.DataFrame({"id": [1, 1, 2]}))


def test_console_mentions_contract_and_verdict():
    out = render_console(_report(), color=False)
    assert "orders" in out
    assert "FAILED" in out


def test_json_is_parseable():
    import json

    data = json.loads(render_json(_report()))
    assert data["contract"] == "orders"
    assert data["passed"] is False


def test_html_contains_table():
    html = render_html(_report())
    assert "<table>" in html
    assert "orders" in html
