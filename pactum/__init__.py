"""pactum -- lightweight, runnable data contracts for analytics tables.

The public surface is intentionally small:

    from pactum import Contract, validate
    report = validate(Contract.from_yaml("orders.yml"), df)
    if not report.passed:
        ...

Most users drive it through the command line (`pactum check ...`); the
Python API exists for the cases where you want to wire validation into an
existing pipeline.
"""
from __future__ import annotations

from .contracts import Contract, ContractError
from .engine import Suite, validate
from .results import CheckResult, Severity, ValidationReport

__version__ = "0.3.1"

__all__ = [
    "Contract",
    "ContractError",
    "Suite",
    "validate",
    "CheckResult",
    "Severity",
    "ValidationReport",
    "__version__",
]
