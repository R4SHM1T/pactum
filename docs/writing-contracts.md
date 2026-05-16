# Writing contracts

A contract is a YAML file describing one table. The smallest useful one is:

```yaml
name: customers
source:
  type: csv
  path: data/customers.csv
columns:
  - name: customer_id
    dtype: integer
    nullable: false
    unique: true
```

`pactum init customers` writes a starter file you can edit.

## Columns

Each entry under `columns:` describes one column and can carry several shortcuts:

```yaml
- name: amount
  dtype: float        # integer | float | string | boolean | datetime
  required: true      # must the column exist (default true)
  nullable: false     # may it contain nulls (default true)
  unique: false       # must values be distinct (default false)
  min: 0              # numeric lower bound
  max: 100000         # numeric upper bound
  allowed_values: [...]
  regex: '^[A-Z]{2}$'
  severity: error     # error (default) or warn
```

Every shortcut you set becomes its own check, so a failure tells you precisely
which rule broke rather than "this column is bad".

## Table-level checks

Anything that isn't about a single column lives under `checks:`.

```yaml
checks:
  - type: row_count
    min: 1
    max: 5000000

  - type: relationship
    column: customer_id
    references:
      contract: customers   # the `name` of another contract in the suite
      column: customer_id

  - type: expression
    description: paid orders must carry a positive amount
    expression: "not (status == 'paid' and amount <= 0)"
```

`relationship` only resolves when you run the whole folder with
`pactum check-suite`, because it needs the other table loaded.

Expressions are evaluated once per row with the column values in scope. A row
passes when the expression is truthy. Only a small set of builtins is available
(`len`, `abs`, `min`, `max`, `round`, `str`, `int`, `float`, `bool`); there are
no imports and no file access.

## Freshness

```yaml
freshness:
  column: created_at
  max_age: 2d     # s, m, h, d, w
  severity: warn
```

This fails (or warns) when the newest timestamp in the table is older than
`max_age`.

## Severity

Default severity is `error`, which fails the build. Use `warn` for things you
want to watch but not block on (stale data is a common one). To make warnings
block too, run with `--fail-on warn`.
