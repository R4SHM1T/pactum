# Contributing

Thanks for taking a look. This is a small project and I'd like to keep it that
way, but fixes and well-scoped features are welcome.

## Getting set up

```bash
git clone https://github.com/R4SHM1T/pactum
cd pactum
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## A few ground rules

- Every new check needs tests, both a passing and a failing case.
- Keep checks independent. A check looks at one table (plus a read-only
  context for relationships) and returns a `CheckResult`. No global state.
- New check types go in `checks.py` and get wired into the `REGISTRY` and the
  contract parser in `contracts.py`.
- Run `pytest` before opening a PR.

If you're planning something larger, open an issue first so we can talk it
through.
