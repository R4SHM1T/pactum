import pytest

from pactum.contracts import Contract, ContractError, ContractModel


def test_build_from_dict_creates_expected_checks():
    data = {
        "name": "t",
        "columns": [
            {"name": "id", "dtype": "integer", "nullable": False, "unique": True},
            {"name": "amount", "min": 0, "max": 10},
        ],
        "checks": [{"type": "row_count", "min": 1}],
    }
    contract = Contract.from_dict(data)
    types = {chk.type for chk in contract.checks}
    assert {"required", "dtype", "not_null", "unique", "range", "row_count"} <= types


def test_unknown_field_is_rejected():
    with pytest.raises(Exception):
        ContractModel(name="t", bogus=1)


def test_unknown_check_type_raises():
    with pytest.raises(ContractError):
        Contract.from_dict({"name": "t", "checks": [{"type": "nope"}]})


def test_relationship_requires_references():
    with pytest.raises(ContractError):
        Contract.from_dict(
            {"name": "t", "checks": [{"type": "relationship", "column": "cid"}]}
        )
