#!/usr/bin/env python3
"""EU-profile conformance runner: EN 18223:2026 example corpus.

Runs every example payload printed in EN 18223:2026 (clause 5.2 compressed
JSON, Annex A expanded JSON, Annex B XML) — extracted verbatim under
``conformance/eu-profile/fixtures/en-18223/`` — through the UniDPP
validators, and writes ``conformance/eu-profile/REPORT.md`` and
``REPORT.json`` (the evidence annex for paper 4, P3 deliverable).

Exit status: 0 when the suite ran to completion and both reports were
written; 1 on harness errors (missing/unfaithful fixtures, unwritable
reports). Findings about the standard under test are report content, not
harness failures — the standard's own inconsistencies are the evidence
this annex exists to collect.

Usage (from the repository root, any fresh shell)::

    python scripts/eu_profile_report.py [--fixtures DIR] [--out DIR]
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from unidpp.adapters.en18223 import (
    run_eu_profile_suite,
    write_eu_profile_reports,
)

DEFAULT_FIXTURES = REPO_ROOT / "conformance" / "eu-profile" / "fixtures" / "en-18223"
DEFAULT_OUT = REPO_ROOT / "conformance" / "eu-profile"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    fixtures_dir = DEFAULT_FIXTURES
    out_dir = DEFAULT_OUT
    it = iter(argv)
    for arg in it:
        if arg == "--fixtures":
            fixtures_dir = Path(next(it))
        elif arg == "--out":
            out_dir = Path(next(it))
        else:
            print(f"unknown argument: {arg}", file=sys.stderr)
            return 2

    report = run_eu_profile_suite(fixtures_dir)
    json_path, md_path = write_eu_profile_reports(report, out_dir)

    t = report["totals"]
    print(f"EU-profile conformance: {t['fixtures']} fixtures — "
          f"{t['passed']} pass, {t['failed']} fail (findings)")
    print("findings by AUDIT id:")
    for ref, count in t["findingsByAuditId"].items():
        print(f"  {ref}: {count}")
    print(f"new finding ids: {', '.join(t['newFindingIds'])}")
    print(f"probes: {len(report['probes'])} "
          f"({', '.join(p['id'] for p in report['probes'])})")
    print(f"json: {json_path}")
    print(f"markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
