"""Command line entry point: `pactum check`, `check-suite` and `init`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .contracts import Contract
from .engine import Suite, validate
from .reports import render_console, render_html, render_json
from .sources import load_for_contract

_SCAFFOLD = """name: {name}
description: describe what this dataset is and who owns it
source:
  type: csv
  path: data/{name}.csv
columns:
  - name: id
    dtype: integer
    nullable: false
    unique: true
checks:
  - type: row_count
    min: 1
"""


def _use_color(args) -> bool:
    if getattr(args, "no_color", False):
        return False
    return sys.stdout.isatty()


def _write(text: str, output: str | None) -> None:
    if output:
        Path(output).write_text(text)
    else:
        print(text)


def _exit_code(report, fail_on: str) -> int:
    if fail_on == "warn":
        return 0 if (report.passed and not report.warnings) else 1
    return 0 if report.passed else 1


def _check_command(args) -> int:
    contract = Contract.from_yaml(args.contract)
    if args.data:
        import pandas as pd

        df = pd.read_csv(args.data)
    else:
        df = load_for_contract(contract)
    report = validate(contract, df)
    if args.format == "json":
        _write(render_json(report), args.output)
    elif args.format == "html":
        _write(render_html(report), args.output)
    else:
        _write(render_console(report, color=_use_color(args)), args.output)
    return _exit_code(report, args.fail_on)


def _suite_command(args) -> int:
    suite = Suite.from_dir(args.directory)
    reports = list(suite.run().values())
    if args.format == "json":
        _write(render_json(reports), args.output)
    elif args.format == "html":
        _write(render_html(reports), args.output)
    else:
        joined = "\n\n".join(render_console(r, color=_use_color(args)) for r in reports)
        _write(joined, args.output)
    return 0 if all(_exit_code(r, args.fail_on) == 0 for r in reports) else 1


def _init_command(args) -> int:
    target = args.output or f"{args.name}.yml"
    Path(target).write_text(_SCAFFOLD.format(name=args.name))
    print(f"wrote {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pactum", description="Run data contracts against your tables."
    )
    parser.add_argument("--version", action="version", version=f"pactum {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    chk = sub.add_parser("check", help="validate a single contract")
    chk.add_argument("contract")
    chk.add_argument("--data", help="override the data file named in the contract")
    chk.add_argument("--format", choices=["text", "json", "html"], default="text")
    chk.add_argument("--output", help="write the report to a file instead of stdout")
    chk.add_argument("--fail-on", choices=["error", "warn"], default="error", dest="fail_on")
    chk.add_argument("--no-color", action="store_true")
    chk.set_defaults(func=_check_command)

    suite = sub.add_parser("check-suite", help="validate every contract in a directory")
    suite.add_argument("directory")
    suite.add_argument("--format", choices=["text", "json", "html"], default="text")
    suite.add_argument("--output")
    suite.add_argument("--fail-on", choices=["error", "warn"], default="error", dest="fail_on")
    suite.add_argument("--no-color", action="store_true")
    suite.set_defaults(func=_suite_command)

    init = sub.add_parser("init", help="write a starter contract")
    init.add_argument("name")
    init.add_argument("--output")
    init.set_defaults(func=_init_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
