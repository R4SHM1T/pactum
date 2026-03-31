"""Result objects produced when a contract runs against data."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """How much we care when a check fails.

    ERROR-severity failures break the build; WARN-severity failures are
    surfaced but do not (by default) change the exit code.
    """

    ERROR = "error"
    WARN = "warn"

    def __str__(self) -> str:
        return self.value


@dataclass
class CheckResult:
    """The outcome of running one check against one table."""

    check: str
    passed: bool
    severity: Severity
    column: str | None = None
    message: str = ""
    failing_rows: int = 0
    sample: list[Any] = field(default_factory=list)

    @property
    def is_blocking(self) -> bool:
        """A failed ERROR-severity check; the thing that fails a build."""
        return (not self.passed) and self.severity is Severity.ERROR


@dataclass
class ValidationReport:
    """Everything we learned about a single table."""

    contract: str
    results: list[CheckResult] = field(default_factory=list)
    rows_scanned: int = 0

    def add(self, result: CheckResult) -> None:
        self.results.append(result)

    @property
    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if not r.passed]

    @property
    def errors(self) -> list[CheckResult]:
        return [r for r in self.results if r.is_blocking]

    @property
    def warnings(self) -> list[CheckResult]:
        return [
            r
            for r in self.results
            if not r.passed and r.severity is Severity.WARN
        ]

    @property
    def passed(self) -> bool:
        """True when nothing blocking failed."""
        return not any(r.is_blocking for r in self.results)

    def to_dict(self) -> dict:
        return {
            "contract": self.contract,
            "passed": self.passed,
            "rows_scanned": self.rows_scanned,
            "summary": {
                "checks": len(self.results),
                "failed": len(self.failures),
                "errors": len(self.errors),
                "warnings": len(self.warnings),
            },
            "results": [
                {
                    "check": r.check,
                    "column": r.column,
                    "passed": r.passed,
                    "severity": str(r.severity),
                    "failing_rows": r.failing_rows,
                    "message": r.message,
                    "sample": r.sample,
                }
                for r in self.results
            ],
        }
