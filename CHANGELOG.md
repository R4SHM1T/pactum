# Changelog

All notable changes to this project are recorded here.

## 0.3.1
- Relationship checks now report a sample of the offending values.
- Friendlier error when a contract references a dataset that wasn't loaded.

## 0.3.0
- Added `check-suite` for validating a directory of contracts together, so
  relationship checks can resolve across tables.
- HTML report output (`--format html`).

## 0.2.0
- Added freshness, relationship and custom expression checks.
- Severity levels (`error` / `warn`) and `--fail-on`.
- JSON report output for wiring into CI.

## 0.1.0
- First cut: column presence, dtype, null, unique, range, allowed values,
  regex and row-count checks driven from a YAML contract.
