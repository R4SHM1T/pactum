# Architecture

pactum is small on purpose. The whole thing is four ideas that compose:

1. A **contract** is a declarative description of a table.
2. A **check** is one question you can ask of a dataframe.
3. The **engine** runs the checks and collects answers.
4. A **report** renders those answers for whoever is reading.

## The flow of a run

```
YAML  ->  ContractModel (pydantic)  ->  list[Check]  ->  engine.validate  ->  ValidationReport  ->  report
```

### contracts.py

The YAML is parsed into pydantic models with `extra="forbid"`, so a misspelled
key is an error you see immediately instead of a rule that silently never runs.
Once validated, the model is expanded into a flat `list[Check]`:

- Column shortcuts (`unique: true`, `min: 0`, `regex: ...`) each become a
  dedicated check, all inheriting that column's severity.
- Table-level entries under `checks:` are built by `_spec_check`.

Keeping expansion separate from execution means the engine never has to know
anything about YAML.

### checks.py

Every check subclasses `Check` and implements `run(df, context) -> CheckResult`.
Most of them are column checks, so `_ColumnCheck` handles the common case: if
the column is absent it returns `None` and lets the `required` check be the one
place that complains about a missing column. The base class also owns
`_result`, which turns a boolean "bad rows" mask into a `CheckResult` with a
count and a small sample. A new check is usually a dozen lines: build the mask,
hand it to `_result`.

`context` is a read-only `dict[str, DataFrame]` of the other tables in the run.
Only relationship checks use it.

### engine.py

`validate` walks the checks, skips the `None`s, and accumulates a
`ValidationReport`. `Suite` exists for the cross-table case: it loads every
contract's data up front so a relationship check can resolve its target without
each contract knowing how its neighbours load.

### results.py and reports.py

`CheckResult` and `ValidationReport` are plain dataclasses. The report knows how
to answer the only question CI cares about (`passed`, meaning nothing
error-severity failed) and how to serialise itself. `reports.py` turns reports
into console text, JSON, or a standalone HTML page. Rendering is deliberately
separate from the data so adding a format never touches the engine.

## Why not just use great_expectations / pandera?

Both are good and both are bigger than I wanted. pactum is for the case where
you want contracts in version control, a single CLI in CI, and a codebase you
can read in an afternoon. If you outgrow it, the YAML maps cleanly onto the
heavier tools.
