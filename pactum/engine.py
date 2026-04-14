"""Run contracts against data and collect the results."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .contracts import Contract
from .results import ValidationReport
from .sources import load_for_contract


def validate(
    contract: Contract,
    df: pd.DataFrame,
    context: dict[str, pd.DataFrame] | None = None,
) -> ValidationReport:
    """Validate a single dataframe against a contract.

    ``context`` maps contract names to dataframes and is only needed when a
    contract has relationship checks that point at other tables.
    """
    context = context or {}
    report = ValidationReport(contract=contract.name, rows_scanned=len(df))
    for check in contract.checks:
        outcome = check.run(df, context)
        if outcome is None:
            continue
        if isinstance(outcome, list):
            for item in outcome:
                report.add(item)
        else:
            report.add(outcome)
    return report


class Suite:
    """A group of contracts that may reference one another.

    Loading everything up front means relationship checks can resolve their
    targets without each contract having to know how its neighbours load.
    """

    def __init__(self, contracts: list[Contract]) -> None:
        self.contracts = contracts

    @classmethod
    def from_dir(cls, directory: str | Path) -> "Suite":
        directory = Path(directory)
        paths = sorted([*directory.glob("*.yml"), *directory.glob("*.yaml")])
        return cls([Contract.from_yaml(p) for p in paths])

    def run(self) -> dict[str, ValidationReport]:
        frames = {c.name: load_for_contract(c) for c in self.contracts}
        return {c.name: validate(c, frames[c.name], frames) for c in self.contracts}
