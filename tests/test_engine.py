import pandas as pd

from pactum import Contract, Suite, validate


def test_clean_frame_passes():
    contract = Contract.from_dict(
        {"name": "t", "columns": [{"name": "id", "dtype": "integer", "nullable": False, "unique": True}]}
    )
    report = validate(contract, pd.DataFrame({"id": [1, 2, 3]}))
    assert report.passed
    assert report.rows_scanned == 3


def test_problems_are_detected():
    contract = Contract.from_dict(
        {"name": "t", "columns": [{"name": "id", "dtype": "integer", "nullable": False, "unique": True}]}
    )
    report = validate(contract, pd.DataFrame({"id": [1, 1, None]}))
    assert not report.passed
    assert report.failures


def test_example_suite(examples_dir):
    reports = Suite.from_dir(examples_dir / "contracts").run()
    assert set(reports) == {"orders", "customers"}
    assert reports["customers"].passed
    # orders has four planted, blocking problems
    assert not reports["orders"].passed
    failing_checks = {r.check for r in reports["orders"].errors}
    assert {"range", "allowed_values", "relationship", "expression"} <= failing_checks
