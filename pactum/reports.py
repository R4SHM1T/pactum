"""Render validation reports for humans (console, HTML) and machines (JSON)."""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone

from .results import Severity, ValidationReport

_ESC = chr(27)
_RESET = f"{_ESC}[0m"
_RED = f"{_ESC}[31m"
_GREEN = f"{_ESC}[32m"
_YELLOW = f"{_ESC}[33m"
_BOLD = f"{_ESC}[1m"
_DIM = f"{_ESC}[2m"


def _paint(text: str, code: str, enabled: bool) -> str:
    return f"{code}{text}{_RESET}" if enabled else text


def render_console(report: ValidationReport, color: bool = True) -> str:
    lines = [_paint(f"{report.contract}  ({report.rows_scanned} rows)", _BOLD, color)]
    for r in report.results:
        if r.passed:
            mark = _paint("PASS", _GREEN, color)
        elif r.severity is Severity.WARN:
            mark = _paint("WARN", _YELLOW, color)
        else:
            mark = _paint("FAIL", _RED, color)
        target = f" {r.column}" if r.column else ""
        extra = f"  ({r.failing_rows} rows)" if (not r.passed and r.failing_rows) else ""
        lines.append(f"  {mark}  {r.check}{target}: {r.message}{extra}")
        if not r.passed and r.sample:
            preview = ", ".join(str(s) for s in r.sample[:5])
            lines.append(_paint(f"        e.g. {preview}", _DIM, color))
    summary = (
        f"{len(report.results)} checks, "
        f"{len(report.errors)} errors, "
        f"{len(report.warnings)} warnings"
    )
    verdict = _paint("OK", _GREEN, color) if report.passed else _paint("FAILED", _RED, color)
    lines.append(f"  {verdict}: {summary}")
    return "\n".join(lines)


def render_json(reports) -> str:
    if isinstance(reports, ValidationReport):
        payload = reports.to_dict()
    else:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "contracts": [r.to_dict() for r in reports],
        }
    return json.dumps(payload, indent=2, default=str)


_HTML_HEAD = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<title>pactum report</title><style>"
    "body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,sans-serif;margin:2rem;color:#1b1b1b}"
    "h1{font-size:20px}h2{margin:1.6rem 0 .4rem;font-size:16px}"
    "small{color:#888;font-weight:400}"
    "table{border-collapse:collapse;width:100%;margin-bottom:1rem;font-size:14px}"
    "th,td{text-align:left;padding:6px 10px;border-bottom:1px solid #eee}"
    "th{color:#666;font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:.04em}"
    "tr.pass td:first-child{color:#1a7f37}tr.warn td:first-child{color:#9a6700}"
    "tr.fail td:first-child{color:#cf222e}td:first-child{font-weight:600}"
    "</style></head><body>"
)


def render_html(reports) -> str:
    if isinstance(reports, ValidationReport):
        reports = [reports]
    parts = [_HTML_HEAD, "<h1>Data contract report</h1>"]
    for rep in reports:
        parts.append(
            f"<h2>{html.escape(rep.contract)} <small>{rep.rows_scanned} rows</small></h2>"
        )
        parts.append(
            "<table><thead><tr><th>Status</th><th>Check</th><th>Column</th>"
            "<th>Detail</th><th>Rows</th></tr></thead><tbody>"
        )
        for r in rep.results:
            status = "pass" if r.passed else ("warn" if r.severity is Severity.WARN else "fail")
            parts.append(
                f"<tr class='{status}'><td>{status.upper()}</td>"
                f"<td>{html.escape(r.check)}</td>"
                f"<td>{html.escape(r.column or '')}</td>"
                f"<td>{html.escape(r.message)}</td>"
                f"<td>{r.failing_rows or ''}</td></tr>"
            )
        parts.append("</tbody></table>")
    parts.append(
        f"<p style='color:#aaa;font-size:12px'>generated "
        f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}</p>"
    )
    parts.append("</body></html>")
    return "\n".join(parts)
