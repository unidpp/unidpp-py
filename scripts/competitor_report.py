#!/usr/bin/env python3
"""Competitor conformance runner: freeDPP and open-dpp published artifacts.

Runs every machine-checkable artifact published by the two open-source DPP
competitor projects through the same UniDPP EN-18223 conformance pipeline
that produced the EU-profile report (`conformance/eu-profile/REPORT.md`).

Sources:

- freeDPP  (https://github.com/OttoHandle/freeDPP)  — only the
  announcement/overview repo is published; the implementation lives in
  separate sibling repos (freeDPPserver, freeDPPdatabase, freeDPPgui)
  with no source yet. The public machine-checkable artifacts are the
  two live test endpoints at https://drill.freedpp.eu and
  https://insulation.freedpp.eu — both serve EN 18223-style JSON
  documents with `Accept: application/json`.

- open-dpp (https://github.com/open-dpp/open-dpp) — the public
  artifacts are the source tree. The only example document in
  machine-checkable JSON form is the e2e battery-passport fixture
  (`apps/e2e/tests/api/battery-passport.ts`), which exports a single
  giant `Battery_Passport` object literal in `open-dpp:json` format
  (AAS-based, NOT EN 18223 — different wire shape).

The runner detects whether each artifact is EN 18223-shaped (carries the
EN header keys or `elements[]`) or a different format. EN 18223-shaped
artifacts are run through `validate_profile_fixture` exactly like the EU
profile report. Other artifacts receive a coverage observation (info
severity) that records the format-mismatch and the keys that are
present — no findings are manufactured by changing the runner's
semantics.

Usage (from the repository root, any fresh shell)::

    python scripts/competitor_report.py [--fixtures-dir DIR] [--out DIR]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from unidpp import carrier
from unidpp.adapters.en18223 import (
    FixtureResult,
    ProfileFinding,
    validate_profile_fixture,
)

DEFAULT_FIXTURES = REPO_ROOT / "conformance" / "competitors"
DEFAULT_OUT = REPO_ROOT / "conformance" / "competitors"


def _rel(path: Path) -> str:
    """The artifact path as a repo-relative string (reports are
    committed; absolute local paths never enter them)."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)

EN18223_HEADER_KEYS = (
    "digitalProductPassportId",
    "uniqueProductIdentifier",
    "granularity",
    "dppSchemaVersion",
    "dppStatus",
    "lastUpdated",
    "economicOperatorId",
    "facilityId",
    "contentSpecificationIds",
)


def _index_for(dirpath: Path) -> dict[str, Any]:
    """Build an index of the competitor artifact directory.

    Vendors each publish artifacts under ``conformance/competitors/<vendor>/
    artifacts/<file>``; this walker gathers them and groups by vendor.
    """
    out: dict[str, list[dict[str, Any]]] = {}
    for vendor_dir in sorted(p for p in dirpath.iterdir() if p.is_dir()):
        art = vendor_dir / "artifacts"
        if not art.exists():
            continue
        for f in sorted(art.glob("*.json")):
            out.setdefault(vendor_dir.name, []).append(
                {
                    "vendor": vendor_dir.name,
                    "path": f,
                    "name": f.name,
                }
            )
    return out


# ---------------------------------------------------------------------------
# freeDPP source-model corroboration: citations loaded verbatim from the
# mirrored server sources so the report can never print a stale quote.
# ---------------------------------------------------------------------------

_FREEDPP_SERVER_SOURCES = Path(__file__).resolve().parents[1] / "conformance" / "competitors" / "freedpp" / "sources" / "server"

# (file, 1-based line number, substring that must appear on that line, note)
_FREEDPP_EVIDENCE_SPECS = [
    (
        "FreeDppDppFull.cs",
        21,
        '"Model"',
        "default granularity is the capitalized spelling — the origin of the A1-granularity-casing findings on every wire artifact",
    ),
    (
        "FreeDppDppFull.cs",
        22,
        '"0.1"',
        "default dppSchemaVersion does not carry the ENnnn:vX.Y form — the origin of the A6-schema-version-placeholder findings",
    ),
    (
        "FreeDppDppFull.cs",
        23,
        '"Active"',
        "default dppStatus is the capitalized spelling; the live payloads override it with the lowercase 'active' the EN's examples use",
    ),
    (
        "FreeDppDppFull.cs",
        24,
        "DateTime.Now",
        "lastUpdated defaults to server-local time (no timezone designator) — the origin of the not-a-valid-date-time findings",
    ),
    (
        "FreeDppDppFull.cs",
        28,
        "EN 18239",
        "the hash slot is explicitly deferred: integrity is 'to be handled when EN 18239 published' — the trust surface is pending by the vendor's own statement (also FUNCTIONALITY.md: 'security frameworks according EN 18239 and EN 18246 to be delivered after publication of these standards')",
    ),
    (
        "FreeDppDppFull.cs",
        71,
        "laut annex 1",
        "the class name follows the EN's Annex A spelling 'SingleValuedDataElement' — the origin of the A3-class-name-drift findings; the comment cites the standard's annex as its source",
    ),
    (
        "DppValidateController.cs",
        6,
        "not yet comletely implemented",
        "the server's own DPP validation endpoint is a test controller, 'not yet comletely implemented - just a test controller for dpp validation'",
    ),
    (
        "DppValidateController.cs",
        18,
        "Schemas",
        "the validator references Schemas/dpp-schema.json; no Schemas directory exists anywhere in the published freeDPPserver repo (working tree or PublishedVersion260813.zip)",
    ),
]


def _load_freedpp_source_evidence() -> list[dict[str, str]]:
    """Load the verbatim citation lines from the mirrored server sources.

    Raises if the mirror has drifted (line content changed), so the report
    cannot silently quote a stale citation.
    """
    evidence: list[dict[str, str]] = []
    for n, (fname, lineno, needle, note) in enumerate(_FREEDPP_EVIDENCE_SPECS, start=1):
        text = (_FREEDPP_SERVER_SOURCES / fname).read_text(encoding="utf-8-sig")
        lines = text.splitlines()
        line = lines[lineno - 1]
        if needle not in line:
            raise ValueError(
                f"freeDPP source evidence S{n}: {fname}:{lineno} no longer "
                f"contains {needle!r} (found {line!r}) — re-verify the "
                "mirror before regenerating the report"
            )
        evidence.append(
            {
                "id": f"S{n}",
                "file": f"freeDPPserver/{fname}:{lineno}",
                "citation": line,
                "note": note,
            }
        )
    return evidence


def _vendor_meta(vendor: str) -> dict[str, str]:
    """Static metadata about each competitor (URLs, license, what they ship)."""
    if vendor == "freedpp":
        return {
            "vendor": "freeDPP (Otto Handle / CEN/CLC/JTC 24 WG 4 convenor)",
            "repo": "https://github.com/OttoHandle/freeDPP",
            "license": "GPL-3.0 (LICENSE in the overview repo, mirrored in sources/)",
            "published_artifacts": (
                "four published repos: the overview repo "
                "(github.com/OttoHandle/freeDPP, 4 markdown files) plus the "
                "implementation — freeDPPserver (C#/.NET 8 API serving both "
                "EN 18223 serializations), freeDPPdatabase (SQL Server "
                "schema CreateDb.sql, 2048 lines), freeDPPgui (management "
                "frontend). Two live test endpoints at "
                "https://drill.freedpp.eu and https://insulation.freedpp.eu "
                "serve the wire payloads this run exercises: the permalink "
                "route (/01/<GTIN>) and the EN 18222 API route "
                "(/v1/dppsByProductId/<GTIN>?representation=full|compressed)."
            ),
            "fetch_command": (
                "git clone --depth 1 https://github.com/OttoHandle/freeDPP.git conformance/competitors/freedpp/repo\n"
                "git clone --depth 1 https://github.com/OttoHandle/freeDPPserver.git freeDPPserver\n"
                "git clone --depth 1 https://github.com/OttoHandle/freeDPPdatabase.git freeDPPdatabase\n"
                "curl -sH 'Accept: application/json' https://drill.freedpp.eu/01/5012345101095 -o conformance/competitors/freedpp/artifacts/drill-test1.json\n"
                "curl -sH 'Accept: application/json' 'https://drill.freedpp.eu/v1/dppsByProductId/5012345101095?representation=full' -o conformance/competitors/freedpp/artifacts/drill-api-full.json\n"
                "curl -sH 'Accept: application/json' 'https://drill.freedpp.eu/v1/dppsByProductId/5012345101095?representation=compressed' -o conformance/competitors/freedpp/artifacts/drill-api-compressed.json\n"
                "curl -sH 'Accept: application/json' https://insulation.freedpp.eu/01/4003973287696 -o conformance/competitors/freedpp/artifacts/insulation-test2.json\n"
                "curl -sH 'Accept: application/json' 'https://insulation.freedpp.eu/v1/dppsByProductId/4003973287696?representation=full' -o conformance/competitors/freedpp/artifacts/insulation-api-full.json\n"
                "curl -sH 'Accept: application/json' 'https://insulation.freedpp.eu/v1/dppsByProductId/4003973287696?representation=compressed' -o conformance/competitors/freedpp/artifacts/insulation-api-compressed.json"
            ),
        }
    if vendor == "open-dpp":
        return {
            "vendor": "open-dpp (open-source DPP platform; github.com/open-dpp)",
            "repo": "https://github.com/open-dpp/open-dpp",
            "license": "AGPL-3.0 (LICENSE in the repo, mirrored in sources/)",
            "published_artifacts": (
                "source tree (pnpm monorepo). The only example document in "
                "machine-checkable form is the e2e battery-passport fixture "
                "(`apps/e2e/tests/api/battery-passport.ts`), exporting a "
                "`Battery_Passport` object literal in `open-dpp:json` v4.0 "
                "format — AAS-based (environment.assetAdministrationShells "
                "/ submodels / conceptDescriptions), NOT EN 18223."
            ),
            "fetch_command": (
                "git clone --depth 1 https://github.com/open-dpp/open-dpp.git conformance/competitors/open-dpp/repo\n"
                "# extract Battery_Passport with esbuild (transpile TS) + node (execute):\n"
                "node scripts/extract-ts-fixture.cjs apps/e2e/tests/api/battery-passport.ts Battery_Passport conformance/competitors/open-dpp/artifacts/battery-passport.json"
            ),
        }
    return {}


def _detect_format(doc: Any) -> dict[str, Any]:
    """Inspect a JSON document and report what shape it carries.

    Returns a small dict describing what the runner saw; callers use it
    to decide whether to invoke the EN 18223 validator (and with which
    serialization kind — expanded Annex-A form vs compressed 5.2 form)
    or to emit a coverage observation instead.
    """
    if not isinstance(doc, dict):
        return {"shape": "non-object", "keys": [], "en18223Kind": None}
    keys = set(doc.keys())
    en_header_overlap = keys & set(EN18223_HEADER_KEYS)
    has_elements = "elements" in keys
    data_keys = keys - set(EN18223_HEADER_KEYS)
    if has_elements or len(en_header_overlap) >= 2:
        # EN 18223 5.2: the compressed form keys data-element collections
        # directly (no `elements[]`); Annex A: the expanded form nests them
        # under `elements[]`.
        kind = "json-expanded" if has_elements else "json-compressed"
    else:
        kind = None
    return {
        "shape": "object",
        "keys": sorted(keys),
        "en18223HeaderOverlap": sorted(en_header_overlap),
        "hasElements": has_elements,
        "dataKeys": sorted(data_keys),
        "en18223Kind": kind,
        "declaredFormat": doc.get("format"),
        "declaredVersion": doc.get("version"),
    }


def _evaluate_artifact(entry: dict[str, Any]) -> dict[str, Any]:
    """Run one competitor artifact through the pipeline.

    The pipeline is the same `validate_profile_fixture` used by the EU
    profile report — we do not alter its semantics. If the artifact is
    not EN 18223-shaped, we record a coverage observation (info
    severity) and skip the validator layers.
    """
    path = entry["path"]
    raw = path.read_text(encoding="utf-8")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        result = FixtureResult(
            fixture=entry["name"],
            kind="competitor-artifact",
            clause="",
            title=path.name,
            source=_rel(path),
            outcome="fail",
            parsed=False,
        )
        result.findings.append(
            ProfileFinding(
                code="competitor-artifact-malformed-json",
                severity="error",
                message=f"artifact is not valid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})",
                path="$",
            )
        )
        return result.to_dict()

    fmt = _detect_format(doc)
    if fmt["en18223Kind"] is None:
        # Not EN 18223-shaped: record a coverage observation, do not invoke
        # the validator (which assumes EN 18223 header + elements keys).
        result = FixtureResult(
            fixture=entry["name"],
            kind="competitor-artifact",
            clause="",
            title=path.name,
            source=_rel(path),
            outcome="not-applicable",
            parsed=True,
        )
        result.findings.append(
            ProfileFinding(
                code="format-not-en-18223",
                severity="info",
                message=(
                    f"artifact declares format {fmt['declaredFormat']!r} "
                    f"version {fmt['declaredVersion']!r}; carries top-level "
                    f"keys {fmt['keys']}; overlap with the EN 18223 header "
                    f"keys is {fmt['en18223HeaderOverlap']} (none or one). "
                    "Coverage observation only — the conformance runner is "
                    "the EU-profile runner; this format is out of its "
                    "machine-checkable surface."
                ),
                citation=(
                    "EN 18223 Table 1 (4.1.2.1) header keys: "
                    + ", ".join(EN18223_HEADER_KEYS)
                    + "."
                ),
                path="$",
            )
        )
        result.adaptations.append("coverage-observation")
        # Carrier observation for the foreign artifact too (size only; the
        # EN-18223 validator layers are not invoked).
        result.carrier = carrier.measure(doc).to_dict()
        return result.to_dict()

    # EN 18223-shaped: run the validator layers with the structurally
    # detected serialization kind (expanded Annex-A form with `elements[]`
    # vs compressed 5.2 form keyed by elementId). `validate_profile_fixture`
    # rebuilds the result.source from the entry dict, always prepending the
    # EU-profile ADOC_ROOT path; we correct the resulting `source` string
    # back to the vendor label afterwards, leaving the runner semantics
    # unchanged.
    fixture_entry = {
        "id": entry["name"].removesuffix(".json"),
        "kind": fmt["en18223Kind"],
        "clause": entry.get("source_url", _rel(path)),
        "title": entry.get("title", path.name),
        "source": entry.get("source_label", _rel(path)),
        "lines": "1-end",
    }
    v = validate_profile_fixture(fixture_entry, raw, raw)
    result = v.to_dict()
    # Restore the vendor source URL (the runner rewrites it to the
    # ADOC_ROOT path it uses for the EU profile; this is correct for the
    # EU profile but wrong for competitor artifacts).
    result["source"] = entry.get("source_label", _rel(path))
    return result


def _build_competitor_entries(index: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    """Add vendor-specific metadata to each index entry."""
    annotated: dict[str, list[dict[str, Any]]] = {}
    titles = {
        "freedpp": {
            "drill-test1.json": (
                "freeDPP permalink route — cordless drill (GTIN 5012345101095), "
                "Annex-A expanded JSON"
            ),
            "drill-api-full.json": (
                "freeDPP EN 18222 API route, ?representation=full — drill, "
                "Annex-A expanded JSON"
            ),
            "drill-api-compressed.json": (
                "freeDPP EN 18222 API route, ?representation=compressed — "
                "drill, clause 5.2 compressed JSON"
            ),
            "insulation-test2.json": (
                "freeDPP permalink route — insulation (GTIN 4003973287696), "
                "Annex-A expanded JSON"
            ),
            "insulation-api-full.json": (
                "freeDPP EN 18222 API route, ?representation=full — "
                "insulation, Annex-A expanded JSON"
            ),
            "insulation-api-compressed.json": (
                "freeDPP EN 18222 API route, ?representation=compressed — "
                "insulation, clause 5.2 compressed JSON"
            ),
        },
        "open-dpp": {
            "battery-passport.json": (
                "open-dpp battery passport example (open-dpp:json v4.0 AAS)"
            ),
        },
    }
    source_labels = {
        "freedpp": {
            "drill-test1.json": (
                "GET https://drill.freedpp.eu/01/5012345101095 "
                "(Accept: application/json) — captured 2026-09-07"
            ),
            "drill-api-full.json": (
                "GET https://drill.freedpp.eu/v1/dppsByProductId/5012345101095"
                "?representation=full — captured 2026-09-07"
            ),
            "drill-api-compressed.json": (
                "GET https://drill.freedpp.eu/v1/dppsByProductId/5012345101095"
                "?representation=compressed — captured 2026-09-07"
            ),
            "insulation-test2.json": (
                "GET https://insulation.freedpp.eu/01/4003973287696 "
                "(Accept: application/json) — captured 2026-09-07"
            ),
            "insulation-api-full.json": (
                "GET https://insulation.freedpp.eu/v1/dppsByProductId/"
                "4003973287696?representation=full — captured 2026-09-07"
            ),
            "insulation-api-compressed.json": (
                "GET https://insulation.freedpp.eu/v1/dppsByProductId/"
                "4003973287696?representation=compressed — captured 2026-09-07"
            ),
        },
        "open-dpp": {
            "battery-passport.json": (
                "github.com/open-dpp/open-dpp apps/e2e/tests/api/battery-passport.ts "
                "— Battery_Passport exported (4566-line object literal, "
                "format=open-dpp:json, version=4.0); transpiled to JSON via "
                "esbuild + node — captured 2026-09-07"
            ),
        },
    }
    source_urls = {
        "drill-test1.json": "https://drill.freedpp.eu/01/5012345101095",
        "drill-api-full.json": (
            "https://drill.freedpp.eu/v1/dppsByProductId/5012345101095?representation=full"
        ),
        "drill-api-compressed.json": (
            "https://drill.freedpp.eu/v1/dppsByProductId/5012345101095?representation=compressed"
        ),
        "insulation-test2.json": "https://insulation.freedpp.eu/01/4003973287696",
        "insulation-api-full.json": (
            "https://insulation.freedpp.eu/v1/dppsByProductId/4003973287696?representation=full"
        ),
        "insulation-api-compressed.json": (
            "https://insulation.freedpp.eu/v1/dppsByProductId/4003973287696?representation=compressed"
        ),
        "battery-passport.json": "github.com/open-dpp/open-dpp apps/e2e/tests/api/battery-passport.ts",
    }
    for vendor, entries in index.items():
        annotated[vendor] = []
        for e in entries:
            ce = dict(e)
            ce["title"] = titles.get(vendor, {}).get(
                e["name"], e["name"]
            )
            ce["source_label"] = source_labels.get(vendor, {}).get(
                e["name"], str(e["path"])
            )
            ce["source_url"] = source_urls.get(
                e["name"], str(e["path"])
            )
            annotated[vendor].append(ce)
    return annotated


def run_competitor_suite(fixtures_dir: str | Path) -> dict[str, Any]:
    """Run every machine-checkable competitor artifact and return a JSON-ready report."""
    fixtures_dir = Path(fixtures_dir)
    index = _index_for(fixtures_dir)
    if not index:
        raise FileNotFoundError(
            f"no vendor artifact directories found under {fixtures_dir}; "
            "expected conformance/competitors/<vendor>/artifacts/*.json"
        )

    annotated = _build_competitor_entries(index)
    vendor_sections: list[dict[str, Any]] = []
    for vendor, entries in annotated.items():
        meta = _vendor_meta(vendor)
        results = [_evaluate_artifact(e) for e in entries]
        by_audit: Counter[str] = Counter()
        codes: Counter[str] = Counter()
        for r in results:
            for f in r["findings"]:
                if f["auditRef"]:
                    by_audit[f["auditRef"]] += 1
                codes[f["code"]] += 1
        vendor_sections.append(
            {
                "vendor": vendor,
                "meta": meta,
                "totals": {
                    "fixtures": len(results),
                    "passed": sum(1 for r in results if r["outcome"] == "pass"),
                    "failed": sum(1 for r in results if r["outcome"] == "fail"),
                    "notApplicable": sum(1 for r in results if r["outcome"] == "not-applicable"),
                    "errorFindings": sum(r["errorFindings"] for r in results),
                    "findingsByAuditId": dict(sorted(by_audit.items())),
                    "findingsByCode": dict(sorted(codes.items())),
                },
                "results": results,
            }
        )

    overall = {
        "fixtures": sum(v["totals"]["fixtures"] for v in vendor_sections),
        "passed": sum(v["totals"]["passed"] for v in vendor_sections),
        "failed": sum(v["totals"]["failed"] for v in vendor_sections),
        "notApplicable": sum(v["totals"]["notApplicable"] for v in vendor_sections),
        "errorFindings": sum(v["totals"]["errorFindings"] for v in vendor_sections),
    }

    report: dict[str, Any] = {
        "generatedAt": __import__("unidpp.verify", fromlist=["now_iso"]).now_iso(),
        "suite": "unidpp-py competitor conformance — freeDPP and open-dpp published artifacts",
        "purpose": (
            "Factual register of findings produced by running every "
            "machine-checkable artifact published by freeDPP and open-dpp "
            "through the same EN 18223 conformance pipeline that produced "
            "conformance/eu-profile/REPORT.md. Companion to the EU profile "
            "report. Reproducible: see per-vendor fetch commands in the "
            "vendor sections."
        ),
        "runnerSemantics": (
            "Findings are produced by `unidpp.adapters.en18223."
            "validate_profile_fixture` exactly as used by the EU profile "
            "report — no runner semantics were altered for this exercise. "
            "Artifacts that are not EN 18223-shaped receive a single info-"
            "severity `format-not-en-18223` coverage observation and are "
            "skipped; they do not contribute error-severity findings. The "
            "runner reports PASS where it finds zero error-severity findings."
        ),
        "guardrails": [
            "no runner-semantic changes — `validate_profile_fixture` runs unchanged",
            "no manufactured findings — coverage observations only for out-of-scope formats",
            "no FUD — PASSes are reported as PASSes alongside FAILs",
            "no personality — neutral register; findings cite the artifact verbatim",
        ],
        "outcomeSemantics": (
            "pass = zero error-severity findings (artifact is consistent with "
            "the EN 18223 normative text); fail = one or more error-severity "
            "findings; not-applicable = artifact is not EN 18223-shaped and "
            "is recorded as a coverage observation only."
        ),
        "totals": overall,
        "vendors": vendor_sections,
        "freedppSourceEvidence": _load_freedpp_source_evidence(),
    }
    return report


def _collapse_findings(
    findings: list[dict[str, Any]], max_inline: int = 6
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split findings into an inline head and a collapsed remainder.

    Returns (inline, collapsed): inline is the first `max_inline` findings
    rendered individually; collapsed groups the remainder by identical
    (code, audit_ref, message), each with `count`, `paths`, and one
    citation. The JSON report keeps the full un-collapsed list.
    """
    if len(findings) <= max_inline + 1:
        return list(findings), []
    inline = list(findings[:max_inline])
    by_msg: dict[tuple[str, str, str], dict[str, Any]] = {}
    for f in findings[max_inline:]:
        key = (f["code"], f.get("auditRef") or "", f["message"])
        bucket = by_msg.setdefault(
            key,
            {
                "code": f["code"],
                "auditRef": f.get("auditRef"),
                "severity": f["severity"],
                "message": f["message"],
                "paths": [],
                "citation": f.get("citation", ""),
                "count": 0,
            },
        )
        bucket["paths"].append(f["path"])
        bucket["count"] += 1
    return inline, list(by_msg.values())


def _render_finding(f: dict[str, Any]) -> list[str]:
    """Render one finding as a list of markdown lines (no trailing blank)."""
    ref = f" **[AUDIT {f['auditRef']}]**" if f.get("auditRef") else ""
    head = (
        f"- `{f['code']}` ({f['severity']}, path `{f['path']}`)"
        f"{ref}: {f['message']}"
    )
    out = [head]
    if f.get("citation"):
        out.append("")
        out.append("  Citation:")
        out.append("")
        for cl in f["citation"].splitlines():
            out.append(f"  > {cl}" if cl.strip() else "  >")
    return out


def _render_collapsed(b: dict[str, Any]) -> list[str]:
    """Render a collapsed (count, paths) finding block."""
    ref = f" **[AUDIT {b['auditRef']}]**" if b.get("auditRef") else ""
    paths_sample = b["paths"][:5]
    paths_more = "" if len(b["paths"]) <= 5 else f" (+{len(b['paths']) - 5} more)"
    head = (
        f"- `{b['code']}` ({b['severity']}) × **{b['count']} occurrences**"
        f"{ref}: {b['message']}"
    )
    out = [head]
    out.append("")
    out.append(
        f"  Paths (first 5): {', '.join(f'`{p}`' for p in paths_sample)}{paths_more}"
    )
    if b.get("citation"):
        out.append("")
        out.append("  Citation:")
        out.append("")
        for cl in b["citation"].splitlines():
            out.append(f"  > {cl}" if cl.strip() else "  >")
    return out


def _render_artifact_findings(
    findings: list[dict[str, Any]], max_inline: int = 6
) -> list[str]:
    """Render findings for one artifact: inline first N, then collapsed rest."""
    if not findings:
        return ["(no findings)", ""]
    inline, collapsed = _collapse_findings(findings, max_inline=max_inline)
    lines: list[str] = []
    for f in inline:
        lines.extend(_render_finding(f))
        lines.append("")
    if collapsed:
        collapsed_count = sum(b["count"] for b in collapsed)
        lines.append("")
        lines.append(
            f"… and **{collapsed_count}** further findings, collapsed by "
            f"identical message into {len(collapsed)} code(s):"
        )
        lines.append("")
        for b in collapsed:
            lines.extend(_render_collapsed(b))
            lines.append("")
    return lines


def _markdown_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    add = lines.append

    add("# UniDPP competitor conformance report — freeDPP & open-dpp published artifacts")
    add("")
    add(f"Generated: {report['generatedAt']}")
    add("")
    add(
        "**Companion to the EU-profile report.** This report records a "
        "machine-run of every artifact published by freeDPP "
        "(github.com/OttoHandle/freeDPP) and open-dpp "
        "(github.com/open-dpp/open-dpp) through the same EN 18223 "
        "conformance pipeline (`unidpp.adapters.en18223."
        "validate_profile_fixture`) that produced the "
        "`conformance/eu-profile/REPORT.md` register."
    )
    add("")
    add("## 0. Guardrails")
    add("")
    for g in report["guardrails"]:
        add(f"- {g}")
    add("")
    add("## 1. Method")
    add("")
    add("- Artifacts collected per vendor: see vendor sections (§3, §4) "
        "for exact URLs, capture commands, and license notes.")
    add("- Pipeline: same runner as the EU-profile report "
        "(`scripts/eu_profile_report.py`); the runner is invoked with no "
        "parameter changes — its semantics encode what EN 18223 normatively "
        "says (lowercase granularity enumeration, lowercase status "
        "enumeration, ISO 8601-1 timestamps with ASCII separators, ISO "
        "639-1/BCP 47 language tags, the prose class-name spelling, "
        "valueDataType/value JSON-type consistency, etc.).")
    add("- Format detection: the runner inspects each artifact's top-level "
        "shape. Artifacts that carry the EN 18223 header keys "
        "(`digitalProductPassportId`, `uniqueProductIdentifier`, "
        "`granularity`, `dppSchemaVersion`, `dppStatus`, `lastUpdated`, "
        "`economicOperatorId`, `facilityId`, `contentSpecificationIds`) or "
        "an `elements[]` tree are run through all four validation layers "
        "(AUDIT A-rules on the header, EU-profile JSON Schemas, EU-profile "
        "semantic rules, neutral-core identifier mapping).")
    add("- Artifacts that are NOT EN 18223-shaped receive a single "
        "info-severity `format-not-en-18223` coverage observation; the "
        "validator layers are not invoked. No findings are manufactured. "
        "The observation records the artifact's declared format/version "
        "and its top-level keys; the rationale is documented as the "
        "runner semantics.")
    add("- Temporal layer: EN 18223-shaped artifacts additionally run the "
        "DPP temporal profile (`unidpp.temporal`) — every timestamp field "
        "against ISO 8601-1:2019 as impacted by Amd 1:2022, with "
        "precise-path findings (e.g. a server-local timestamp with no "
        "timezone designator).")
    add("- Carrier column: canonical serialized size against the "
        "ISO/IEC 18004 QR byte-capacity tables (`unidpp.carrier`, ported "
        "from the CLI's tables). An observation only — carrier budgets "
        "bind Tier-A carrier-embedded packs, not served documents; no "
        "finding is raised from it.")
    add(
        f"- Outcome semantics: {report['outcomeSemantics']}"
    )
    add("")
    add("## 2. Results summary")
    add("")
    t = report["totals"]
    add(f"- Vendors: **{len(report['vendors'])}** (freeDPP, open-dpp)")
    add(f"- Artifacts run: **{t['fixtures']}**")
    add(f"- Pass: **{t['passed']}**")
    add(f"- Fail (error-severity findings): **{t['failed']}**")
    add(f"- Not applicable (different wire format): **{t['notApplicable']}**")
    add(f"- Error-severity findings (across vendors): **{t['errorFindings']}**")
    add("")
    add("| Vendor | Artifacts | Pass | Fail | N/A | Error findings |")
    add("|---|---|---|---|---|---|")
    for v in report["vendors"]:
        vt = v["totals"]
        add(
            f"| {v['vendor']} | {vt['fixtures']} | {vt['passed']} | "
            f"{vt['failed']} | {vt['notApplicable']} | "
            f"{vt['errorFindings']} |"
        )
    add("")
    add("## 3. freeDPP")
    add("")
    v = report["vendors"][0]
    add(f"**{v['meta']['vendor']}**")
    add("")
    add(f"Repo: `{v['meta']['repo']}`")
    add("")
    add(f"License: {v['meta']['license']}")
    add("")
    add(f"Published artifacts: {v['meta']['published_artifacts']}")
    add("")
    add("Fetch / capture commands:")
    add("")
    add("```bash")
    for line in v["meta"]["fetch_command"].splitlines():
        add(line)
    add("```")
    add("")
    vt = v["totals"]
    add("### 3.1 freeDPP totals")
    add("")
    add(f"- Artifacts: **{vt['fixtures']}**")
    add(f"- Pass: **{vt['passed']}**")
    add(f"- Fail: **{vt['failed']}**")
    add(f"- Error findings: **{vt['errorFindings']}**")
    add("")
    if vt["findingsByAuditId"]:
        add("Findings by AUDIT id (matches the EU-profile register):")
        add("")
        add("| AUDIT id | Count |")
        add("|---|---|")
        for ref, n in vt["findingsByAuditId"].items():
            add(f"| {ref} | {n} |")
        add("")
    add(
        "Note: the AUDIT A3 finding counts the same class-name drift that "
        "the EU-profile report also records 9 times against EN 18223's own "
        "Annex A examples (the EN's prose uses `SingleValueDataElement` "
        "while its tables use `SingleValuedDataElement`). The competitor's "
        "use of the table spelling is consistent with what the EN's own "
        "examples print; the runner's job is to surface the drift, not "
        "to adjudicate it."
    )
    add("")
    add(
        "Serialization asymmetry (factual): the `?representation=compressed` "
        "artifacts carry only header-level findings, while the expanded "
        "artifacts additionally carry the element-tree findings (A3, N3, "
        "N4, N5). The compressed form keys data by elementId without "
        "objectType, so the promotion (PA4) synthesizes the prose-canonical "
        "class spelling and positional elementIds — nothing in the "
        "compressed serialization itself trips A3/N3/N4/N5. The expanded "
        "form as served prints the Annex-A table spelling and duplicate "
        "elementIds verbatim (see §3.4 S6 for the code origin)."
    )
    add("")
    add("### 3.2 freeDPP per-artifact results")
    add("")
    add("| Artifact | Outcome | Error findings | Distinct codes | Carrier |")
    add("|---|---|---|---|---|")
    for r in v["results"]:
        errors = sum(1 for f in r["findings"] if f["severity"] == "error")
        distinct = sorted({f["code"] for f in r["findings"]})
        add(
            f"| {r['fixture']} | {r['outcome']} | {errors} | "
            f"{len(distinct)} ({', '.join(distinct)}) | "
            f"{carrier.render(r.get('carrier'))} |"
        )
    add("")
    add("### 3.3 freeDPP findings detail")
    add("")
    for r in v["results"]:
        add(f"#### {r['fixture']} — **{r['outcome']}**")
        add("")
        add(f"Source: `{r['source']}`")
        add("")
        for ln in _render_artifact_findings(r["findings"]):
            add(ln)
        add("")

    add("### 3.4 freeDPP source-model corroboration (verbatim citations)")
    add("")
    add(
        "The wire findings above are traceable to the published server model "
        "(`github.com/OttoHandle/freeDPPserver`, mirrored under "
        "`conformance/competitors/freedpp/sources/server/`). Each citation "
        "below is loaded verbatim from the mirror by the runner; the run "
        "fails loudly if the mirror drifts from the citation."
    )
    add("")
    for ev in report["freedppSourceEvidence"]:
        add(f"- **{ev['id']}** ({ev['file']}): {ev['note']}")
        add("")
        add("  Verbatim:")
        add("")
        add(f"  > `{ev['citation']}`")
        add("")

    add("## 4. open-dpp")
    add("")
    v = report["vendors"][1]
    add(f"**{v['meta']['vendor']}**")
    add("")
    add(f"Repo: `{v['meta']['repo']}`")
    add("")
    add(f"License: {v['meta']['license']}")
    add("")
    add(f"Published artifacts: {v['meta']['published_artifacts']}")
    add("")
    add("Fetch / extract commands:")
    add("")
    add("```bash")
    for line in v["meta"]["fetch_command"].splitlines():
        add(line)
    add("```")
    add("")
    vt = v["totals"]
    add("### 4.1 open-dpp totals")
    add("")
    add(f"- Artifacts: **{vt['fixtures']}**")
    add(f"- Pass: **{vt['passed']}**")
    add(f"- Fail: **{vt['failed']}**")
    add(f"- Not applicable: **{vt['notApplicable']}**")
    add("")
    if vt["findingsByCode"]:
        add("info-severity coverage-observation codes:")
        add("")
        add("| Code | Count |")
        add("|---|---|")
        for c, n in vt["findingsByCode"].items():
            add(f"| {c} | {n} |")
        add("")
    add("### 4.2 open-dpp per-artifact results")
    add("")
    add("| Artifact | Outcome | Error findings | Distinct codes | Carrier |")
    add("|---|---|---|---|---|")
    for r in v["results"]:
        errors = sum(1 for f in r["findings"] if f["severity"] == "error")
        distinct = sorted({f["code"] for f in r["findings"]})
        add(
            f"| {r['fixture']} | {r['outcome']} | {errors} | "
            f"{len(distinct)} ({', '.join(distinct)}) | "
            f"{carrier.render(r.get('carrier'))} |"
        )
    add("")
    add("### 4.3 open-dpp findings detail")
    add("")
    for r in v["results"]:
        add(f"#### {r['fixture']} — **{r['outcome']}**")
        add("")
        add(f"Source: `{r['source']}`")
        add("")
        for ln in _render_artifact_findings(r["findings"]):
            add(ln)
        add("")

    add("## 5. Coverage observations (where the runner's machine-checkable surface ends)")
    add("")
    add(
        "The machine-checkable surface of both vendors' published material is "
        "the EU wire envelope — what EN 18223 says a passport document must "
        "contain at serialization level. The runner can verify claims on that "
        "surface (class-name spelling, value-data-type consistency, "
        "element-ID uniqueness, granularity/status casing, ISO 8601-1 "
        "timestamps, language-tag validity) and this report does. What the "
        "published artifacts do not expose to machine checking:"
    )
    add("")
    add(
        "- **freeDPP** publishes full server source (C#/.NET 8) and both "
        "serializations on the wire. Its own code comments place the "
        "trust/integrity surface after the pending standards: the `hashMD5` "
        "slot is 'not yet, to be handled when EN 18239 published' "
        "(FreeDppDppFull.cs:28) and FUNCTIONALITY.md states 'security "
        "frameworks according EN 18239 and EN 18246 to be delivered after "
        "publication of these standards'. The `dppValidate` endpoint is "
        "'not yet comletely implemented' and references a "
        "Schemas/dpp-schema.json that is absent from the repo. No published "
        "signature, trust list, revocation, or offline-verification surface "
        "exists in the material examined."
    )
    add("")
    add(
        "- **open-dpp** publishes full application source "
        "(NestJS/MongoDB/S3 monorepo) but its only published passport "
        "document is the e2e fixture in `open-dpp:json` — an AAS-based "
        "format (`environment.assetAdministrationShells` / `submodels` / "
        "`conceptDescriptions`) with no EN 18223 header keys. No published "
        "passport artifact carries signatures, transparency-log commitments, "
        "or trust-list references; interop with the EN 18223 wire format "
        "requires a mapping adapter, none is published."
    )
    add("")
    add(
        "- **Neither vendor's published artifacts address offline "
        "verification or multi-jurisdiction portability** — no Tier-A "
        "offline pack, no QR-carried verdict, no second-jurisdiction lens. "
        "This is a statement about the published artifact surface, not "
        "about implementation intent: both projects state they target the "
        "EN 182xx series (freeDPP FUNCTIONALITY.md; open-dpp README), and "
        "EN 18239/EN 18246 — the access-rights and "
        "authentication/integrity standards — were the last two of the "
        "eight to publish."
    )
    add("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    fixtures_dir = DEFAULT_FIXTURES
    out_dir = DEFAULT_OUT
    it = iter(argv)
    for arg in it:
        if arg == "--fixtures-dir":
            fixtures_dir = Path(next(it))
        elif arg == "--out":
            out_dir = Path(next(it))
        else:
            print(f"unknown argument: {arg}", file=sys.stderr)
            return 2

    report = run_competitor_suite(fixtures_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "REPORT.json"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    md_path = out_dir / "REPORT.md"
    md_path.write_text(_markdown_report(report), encoding="utf-8")
    t = report["totals"]
    print(
        f"competitor conformance: {t['fixtures']} artifacts — "
        f"{t['passed']} pass, {t['failed']} fail, {t['notApplicable']} N/A "
        f"({t['errorFindings']} error findings)"
    )
    for v in report["vendors"]:
        vt = v["totals"]
        print(
            f"  {v['vendor']}: {vt['fixtures']} artifacts, "
            f"{vt['passed']} pass, {vt['failed']} fail, "
            f"{vt['notApplicable']} N/A, {vt['errorFindings']} error findings"
        )
    print(f"json: {json_path}")
    print(f"markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
