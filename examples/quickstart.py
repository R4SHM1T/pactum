"""Run the bundled example contracts and print the reports.

    python examples/quickstart.py

The orders table has a few deliberately broken rows so you can see what a
failing run looks like.
"""
from pathlib import Path

from pactum import Suite
from pactum.reports import render_console

here = Path(__file__).parent

for name, report in Suite.from_dir(here / "contracts").run().items():
    print(render_console(report, color=False))
    print()
