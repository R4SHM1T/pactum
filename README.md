# pactum

[![ci](https://github.com/R4SHM1T/pactum/actions/workflows/ci.yml/badge.svg)](https://github.com/R4SHM1T/pactum/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

Data contracts you can actually run. Describe what a table is supposed to look
like in a small YAML file, point pactum at the data, and it tells you exactly
where reality and expectation disagree. Wire it into CI and a bad upstream
change fails the build instead of quietly poisoning a dashboard.

I built this after one too many mornings spent tracing a broken report back to
a column that had silently changed type overnight. The checks were always the
same handful of questions (is it unique? is it null? does this id exist in the
other table?), so I wrote them down once in a form a machine could enforce.

```yaml
# contracts/orders.yml
name: orders
description: One row per customer order. Owned by the data platform team.
source:
  type: csv
  path: ../data/orders.csv
freshness:
  column: created_at
  max_age: 7d
  severity: warn
columns:
  - name: order_id
    dtype: integer
    nullable: false
    unique: true
  - name: amount
    dtype: float
    min: 0
  - name: status
    dtype: string
    allowed_values: [pending, paid, shipped, cancelled]
checks:
  - type: relationship
    column: customer_id
    references:
      contract: customers
      column: customer_id
  - type: expression
    description: paid orders must carry a positive amount
    expression: "not (status == 'paid' and amount <= 0)"
```

```text
$ pactum check-suite contracts/

orders  (7 rows)
  PASS  unique order_id: ok
  FAIL  range amount: values outside range (>= 0.0)  (1 rows)
        e.g. -5.0
  FAIL  allowed_values status: values outside the allowed set [...]  (1 rows)
        e.g. delivered
  WARN  freshness created_at: latest row is 9 days old (limit 7d)
  FAIL  relationship customer_id: values missing from customers.customer_id  (1 rows)
        e.g. 99
  FAIL  expression: rows violating: paid orders must carry a positive amount
        e.g. {'order_id': 1002, 'amount': 0.0, 'status': 'paid'}
  FAILED: 19 checks, 4 errors, 1 warnings
```

pactum exits non-zero, so the CI job goes red.

## Install

```bash
git clone https://github.com/R4SHM1T/pactum
cd pactum
pip install -e ".[dev]"
```

A packaged PyPI release is on the roadmap; for now it installs from source.

## Quick start

```bash
# scaffold a contract next to your data
pactum init orders

# edit orders.yml, then run it
pactum check orders.yml

# or validate a whole folder so relationship checks can resolve
pactum check-suite contracts/
```

There's a runnable example in this repo:

```bash
python examples/quickstart.py
```

## The checks

| Check | What it asks |
| --- | --- |
| `required` | is this column present at all |
| `dtype` | do the values fit `integer` / `float` / `string` / `boolean` / `datetime` |
| `not_null` | are there any missing values |
| `unique` | are there duplicates |
| `range` | are numbers within `min` / `max` |
| `allowed_values` | is every value in a known set |
| `regex` | do strings match a pattern |
| `row_count` | is the table roughly the size you expect |
| `freshness` | how old is the newest row (e.g. `max_age: 2d`) |
| `relationship` | does every value exist in another table's column |
| `expression` | a custom rule written as a Python expression over each row |

Column shortcuts (`unique`, `min`, `regex`, ...) live under `columns:`. Anything
that spans columns or tables (`row_count`, `relationship`, `expression`) goes
under `checks:`. Both are just sugar over the same check objects.

## Severity and CI

Every check is either `error` (default) or `warn`. Errors fail the build; warnings
are reported but don't change the exit code unless you ask:

```bash
pactum check orders.yml --fail-on warn
```

Reports come in three flavours for different audiences:

```bash
pactum check orders.yml --format text     # for your terminal
pactum check orders.yml --format json     # for a CI step or a bot
pactum check orders.yml --format html --output report.html
```

### In GitHub Actions

```yaml
- run: pip install git+https://github.com/R4SHM1T/pactum
- run: pactum check-suite contracts/
```

## Using it from Python

```python
import pandas as pd
from pactum import Contract, validate

contract = Contract.from_yaml("contracts/orders.yml")
report = validate(contract, pd.read_csv("data/orders.csv"))

if not report.passed:
    for failure in report.failures:
        print(failure.check, failure.column, failure.message)
```

## How it works

There are three moving parts and they stay out of each other's way:

- **contracts.py** validates the YAML with pydantic and expands it into a flat
  list of check objects.
- **checks.py** holds the checks themselves. Each one looks at a dataframe and
  returns a `CheckResult`. They don't share state, which is why adding a new
  one is a contained job.
- **engine.py** runs the checks and gathers the results. A `Suite` loads a
  folder of contracts together so relationship checks can see neighbouring
  tables.

There's more detail in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and a guide
to writing contracts in [docs/writing-contracts.md](docs/writing-contracts.md).

## Roadmap

- A `dbt`-style `sources.yml` importer so you don't have to retype schemas.
- Per-column drift tracking between runs.
- A `--diff` mode that only reports what changed since the last run.

## License

MIT. See [LICENSE](LICENSE).
