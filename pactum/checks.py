"""The individual checks plus the registry that knows how to build them.

Each check is a small, self-contained object with a ``run`` method. The
base class handles the boring parts (turning a boolean mask of bad rows
into a CheckResult); subclasses just decide which rows are bad.
"""
from __future__ import annotations

import re
from datetime import timezone
from typing import Any

import pandas as pd

from ._duration import parse_duration
from .results import CheckResult, Severity

# A deliberately tiny namespace for user expressions. No file access, no
# imports -- just enough to write the rules people actually need.
_SAFE_BUILTINS = {
    "len": len,
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}


class Check:
    """Base class for every check."""

    type: str = "check"

    def __init__(
        self,
        *,
        column: str | None = None,
        severity: Severity = Severity.ERROR,
        description: str | None = None,
    ) -> None:
        self.column = column
        self.severity = severity
        self.description = description

    def run(
        self, df: pd.DataFrame, context: dict[str, pd.DataFrame]
    ) -> CheckResult | None:
        raise NotImplementedError

    def _result(self, df: pd.DataFrame, bad: pd.Series, message: str) -> CheckResult:
        failing = int(bad.sum())
        sample: list[Any] = []
        if failing and self.column is not None and self.column in df.columns:
            sample = df.loc[bad, self.column].head(5).tolist()
        return CheckResult(
            check=self.type,
            column=self.column,
            passed=failing == 0,
            severity=self.severity,
            failing_rows=failing,
            message=message if failing else "ok",
            sample=sample,
        )


class _ColumnCheck(Check):
    """A check that only makes sense when its column is present.

    If the column is missing we return ``None`` and let the dedicated
    'required' check be the single source of truth about presence.
    """

    def run(self, df, context):
        if self.column not in df.columns:
            return None
        return self._check(df, context)

    def _check(self, df, context) -> CheckResult:
        raise NotImplementedError


class RequiredColumnCheck(Check):
    type = "required"

    def run(self, df, context):
        present = self.column in df.columns
        return CheckResult(
            check=self.type,
            column=self.column,
            passed=present,
            severity=self.severity,
            failing_rows=0 if present else 1,
            message="ok" if present else f"required column '{self.column}' is missing",
        )


class NotNullCheck(_ColumnCheck):
    type = "not_null"

    def _check(self, df, context):
        bad = df[self.column].isna()
        return self._result(df, bad, f"null values in '{self.column}'")


class UniqueCheck(_ColumnCheck):
    type = "unique"

    def _check(self, df, context):
        col = df[self.column]
        bad = col.duplicated(keep=False) & col.notna()
        return self._result(df, bad, f"duplicate values in '{self.column}'")


class DTypeCheck(_ColumnCheck):
    type = "dtype"

    def __init__(self, *, column, dtype, **kwargs):
        super().__init__(column=column, **kwargs)
        self.dtype = dtype

    def _check(self, df, context):
        col = df[self.column]
        present = col.notna()
        if self.dtype in ("integer", "float"):
            coerced = pd.to_numeric(col, errors="coerce")
            bad = present & coerced.isna()
            if self.dtype == "integer":
                fractional = coerced.notna() & (coerced != coerced.round())
                bad = bad | (present & fractional)
        elif self.dtype == "datetime":
            coerced = pd.to_datetime(col, errors="coerce")
            bad = present & coerced.isna()
        elif self.dtype == "boolean":
            truthy = {True, False, 0, 1, "0", "1", "true", "false", "True", "False", "TRUE", "FALSE"}
            bad = present & ~col.isin(list(truthy))
        else:  # string -- anything renders as text
            bad = pd.Series(False, index=col.index)
        return self._result(df, bad, f"values not compatible with type '{self.dtype}'")


class RangeCheck(_ColumnCheck):
    type = "range"

    def __init__(self, *, column, min=None, max=None, **kwargs):
        super().__init__(column=column, **kwargs)
        self.min = min
        self.max = max

    def _check(self, df, context):
        coerced = pd.to_numeric(df[self.column], errors="coerce")
        bad = pd.Series(False, index=df.index)
        if self.min is not None:
            bad = bad | (coerced < self.min)
        if self.max is not None:
            bad = bad | (coerced > self.max)
        bad = bad & coerced.notna()
        bounds = []
        if self.min is not None:
            bounds.append(f">= {self.min}")
        if self.max is not None:
            bounds.append(f"<= {self.max}")
        return self._result(df, bad, f"values outside range ({', '.join(bounds)})")


class AllowedValuesCheck(_ColumnCheck):
    type = "allowed_values"

    def __init__(self, *, column, values, **kwargs):
        super().__init__(column=column, **kwargs)
        self.values = values

    def _check(self, df, context):
        col = df[self.column]
        bad = col.notna() & ~col.isin(self.values)
        return self._result(df, bad, f"values outside the allowed set {self.values}")


class RegexCheck(_ColumnCheck):
    type = "regex"

    def __init__(self, *, column, pattern, **kwargs):
        super().__init__(column=column, **kwargs)
        self.pattern = pattern
        self._re = re.compile(pattern)

    def _check(self, df, context):
        def matches(value):
            if pd.isna(value):
                return True
            return self._re.search(str(value)) is not None

        bad = ~df[self.column].map(matches)
        return self._result(df, bad, f"values not matching /{self.pattern}/")


class RowCountCheck(Check):
    type = "row_count"

    def __init__(self, *, min=None, max=None, **kwargs):
        super().__init__(**kwargs)
        self.min = min
        self.max = max

    def run(self, df, context):
        n = len(df)
        ok = True
        if self.min is not None and n < self.min:
            ok = False
        if self.max is not None and n > self.max:
            ok = False
        return CheckResult(
            check=self.type,
            column=None,
            passed=ok,
            severity=self.severity,
            failing_rows=0 if ok else n,
            message="ok" if ok else f"row count {n} is outside the expected range",
        )


class FreshnessCheck(Check):
    type = "freshness"

    def __init__(self, *, column, max_age, **kwargs):
        super().__init__(column=column, **kwargs)
        self.max_age_text = max_age
        self.max_age = parse_duration(max_age) if isinstance(max_age, str) else max_age

    def run(self, df, context):
        if self.column not in df.columns:
            return None
        stamps = pd.to_datetime(df[self.column], errors="coerce", utc=True)
        if int(stamps.notna().sum()) == 0:
            return CheckResult(
                check=self.type,
                column=self.column,
                passed=False,
                severity=self.severity,
                failing_rows=len(df),
                message=f"no parseable timestamps in '{self.column}'",
            )
        age = pd.Timestamp.now(tz=timezone.utc) - stamps.max()
        ok = age <= self.max_age
        return CheckResult(
            check=self.type,
            column=self.column,
            passed=ok,
            severity=self.severity,
            failing_rows=0 if ok else 1,
            message="ok" if ok else f"latest row is {age} old (limit {self.max_age_text})",
        )


class RelationshipCheck(Check):
    type = "relationship"

    def __init__(self, *, column, ref_contract, ref_column, **kwargs):
        super().__init__(column=column, **kwargs)
        self.ref_contract = ref_contract
        self.ref_column = ref_column

    def run(self, df, context):
        if self.column not in df.columns:
            return None
        ref = context.get(self.ref_contract)
        if ref is None:
            return CheckResult(
                check=self.type,
                column=self.column,
                passed=False,
                severity=self.severity,
                message=f"referenced dataset '{self.ref_contract}' was not provided",
            )
        if self.ref_column not in ref.columns:
            return CheckResult(
                check=self.type,
                column=self.column,
                passed=False,
                severity=self.severity,
                message=f"referenced column '{self.ref_contract}.{self.ref_column}' not found",
            )
        known = set(ref[self.ref_column].dropna().tolist())
        col = df[self.column]
        bad = col.notna() & ~col.isin(known)
        return self._result(
            df, bad, f"values missing from {self.ref_contract}.{self.ref_column}"
        )


class ExpressionCheck(Check):
    type = "expression"

    def __init__(self, *, expression, **kwargs):
        super().__init__(**kwargs)
        self.expression = expression
        self._code = compile(expression, "<contract-expression>", "eval")

    def run(self, df, context):
        if df.empty:
            return CheckResult(
                check=self.type,
                column=None,
                passed=True,
                severity=self.severity,
                message="ok",
            )

        def holds(row):
            try:
                return bool(eval(self._code, {"__builtins__": _SAFE_BUILTINS}, row.to_dict()))
            except Exception:
                return False

        bad = ~df.apply(holds, axis=1)
        failing = int(bad.sum())
        sample = df.loc[bad].head(5).to_dict(orient="records") if failing else []
        label = self.description or self.expression
        return CheckResult(
            check=self.type,
            column=None,
            passed=failing == 0,
            severity=self.severity,
            failing_rows=failing,
            message=f"rows violating: {label}" if failing else "ok",
            sample=sample,
        )


# Maps the 'type' you write in a contract to the class that implements it.
REGISTRY: dict[str, type[Check]] = {
    cls.type: cls
    for cls in (
        RequiredColumnCheck,
        NotNullCheck,
        UniqueCheck,
        DTypeCheck,
        RangeCheck,
        AllowedValuesCheck,
        RegexCheck,
        RowCountCheck,
        FreshnessCheck,
        RelationshipCheck,
        ExpressionCheck,
    )
}


def available_checks() -> list[str]:
    return sorted(REGISTRY)
