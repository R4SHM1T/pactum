"""Turn contract definitions (dicts or YAML) into runnable check objects.

The YAML is validated with pydantic so a typo gives a clear error instead
of a confusing failure halfway through a run. Once validated, the model is
expanded into a flat list of Check objects that the engine can execute.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

from . import checks as _checks
from .checks import Check
from .results import Severity


class ContractError(Exception):
    """Raised when a contract is malformed or references something unknown."""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceSpec(_Model):
    type: Literal["csv", "parquet"] = "csv"
    path: Optional[str] = None
    options: dict[str, Any] = Field(default_factory=dict)


class ColumnSpec(_Model):
    name: str
    dtype: Optional[Literal["integer", "float", "string", "boolean", "datetime"]] = None
    required: bool = True
    nullable: bool = True
    unique: bool = False
    min: Optional[float] = None
    max: Optional[float] = None
    allowed_values: Optional[list[Any]] = None
    regex: Optional[str] = None
    severity: Severity = Severity.ERROR


class FreshnessSpec(_Model):
    column: str
    max_age: str
    severity: Severity = Severity.WARN


class ReferenceSpec(_Model):
    contract: str
    column: str


class CheckSpec(_Model):
    type: str
    severity: Severity = Severity.ERROR
    column: Optional[str] = None
    description: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    references: Optional[ReferenceSpec] = None
    expression: Optional[str] = None


class ContractModel(_Model):
    name: str
    description: Optional[str] = None
    source: Optional[SourceSpec] = None
    columns: list[ColumnSpec] = Field(default_factory=list)
    checks: list[CheckSpec] = Field(default_factory=list)
    freshness: Optional[FreshnessSpec] = None


def _column_checks(col: ColumnSpec) -> list[Check]:
    out: list[Check] = []
    if col.required:
        out.append(_checks.RequiredColumnCheck(column=col.name, severity=col.severity))
    if col.dtype:
        out.append(_checks.DTypeCheck(column=col.name, dtype=col.dtype, severity=col.severity))
    if not col.nullable:
        out.append(_checks.NotNullCheck(column=col.name, severity=col.severity))
    if col.unique:
        out.append(_checks.UniqueCheck(column=col.name, severity=col.severity))
    if col.min is not None or col.max is not None:
        out.append(_checks.RangeCheck(column=col.name, min=col.min, max=col.max, severity=col.severity))
    if col.allowed_values is not None:
        out.append(_checks.AllowedValuesCheck(column=col.name, values=col.allowed_values, severity=col.severity))
    if col.regex:
        out.append(_checks.RegexCheck(column=col.name, pattern=col.regex, severity=col.severity))
    return out


def _spec_check(spec: CheckSpec) -> Check:
    t = spec.type
    if t == "row_count":
        return _checks.RowCountCheck(min=spec.min, max=spec.max, severity=spec.severity, description=spec.description)
    if t == "relationship":
        if spec.references is None or spec.column is None:
            raise ContractError("relationship check needs both 'column' and 'references'")
        return _checks.RelationshipCheck(
            column=spec.column,
            ref_contract=spec.references.contract,
            ref_column=spec.references.column,
            severity=spec.severity,
            description=spec.description,
        )
    if t == "expression":
        if not spec.expression:
            raise ContractError("expression check needs an 'expression'")
        return _checks.ExpressionCheck(expression=spec.expression, severity=spec.severity, description=spec.description)
    if t == "unique":
        return _checks.UniqueCheck(column=spec.column, severity=spec.severity)
    if t == "not_null":
        return _checks.NotNullCheck(column=spec.column, severity=spec.severity)
    raise ContractError(f"unknown check type: {t!r}")


@dataclass
class Contract:
    name: str
    checks: list[Check]
    source: Optional[SourceSpec] = None
    description: Optional[str] = None
    base_dir: Path = field(default_factory=lambda: Path("."))

    @classmethod
    def from_model(cls, model: ContractModel, base_dir: Path = Path(".")) -> "Contract":
        built: list[Check] = []
        for col in model.columns:
            built.extend(_column_checks(col))
        if model.freshness:
            built.append(
                _checks.FreshnessCheck(
                    column=model.freshness.column,
                    max_age=model.freshness.max_age,
                    severity=model.freshness.severity,
                )
            )
        for spec in model.checks:
            built.append(_spec_check(spec))
        return cls(
            name=model.name,
            checks=built,
            source=model.source,
            description=model.description,
            base_dir=base_dir,
        )

    @classmethod
    def from_dict(cls, data: dict, base_dir: Path = Path(".")) -> "Contract":
        return cls.from_model(ContractModel(**data), base_dir)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Contract":
        p = Path(path)
        raw = yaml.safe_load(p.read_text())
        if not isinstance(raw, dict):
            raise ContractError(f"{p} does not contain a contract mapping")
        return cls.from_dict(raw, base_dir=p.parent)
