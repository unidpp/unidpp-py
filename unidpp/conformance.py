"""Conformance runner framework: fixture loader + check registry + report.

The positive corpus is the ported TS fixtures (laptop, car); the negative
corpus is derived from the DPP corpus defect register
(``isoiecjtc5/AUDIT.md`` items A1–A6) — real defects found in EN 18223's
own examples. Every negative fixture MUST fail validation with a precise
finding: the conformance suite proves it catches the corpus's real defects,
not just a synthetic "invalid JSON" strawman.

CLI::

    python -m unidpp.conformance --out reports/

writes ``conformance-report.json`` and ``conformance-report.md``.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from . import model as M
from .canonical import canonical_json
from .eventlog import verify_chain
from .fixtures import build_car, build_laptop
from .validate import validate, ValidationIssue

__all__ = [
    "ConformanceCheck",
    "Fixture",
    "CHECK_REGISTRY",
    "negative_fixtures_a1_a6",
    "positive_fixtures",
    "load_fixtures",
    "run_conformance",
    "write_json_report",
    "write_markdown_report",
    "validate_en18223_document",
    "main",
]

# ---------------------------------------------------------------------------
# The EN-18223-style document validator (AUDIT.md A1–A6 rules)
# ---------------------------------------------------------------------------

EN18223_GRANULARITIES = ("model", "batch", "item")  # A1: normative enumeration
EN18223_STATUSES = ("active", "inactive", "archived", "invalid")  # A2
EN18223_CLASS_NAMES = (
    "SingleValueDataElement",  # A3: prose spelling wins
    "MultiValueDataElement",
    "ReferenceDataElement",
    "GroupedDataElement",
)
EN18223_SCHEMA_VERSION_RE = re.compile(
    r"^EN[0-9]{3,6}:v[0-9]+\.[0-9]+(\.[0-9]+)?$"
)  # A6: no format grammar exists in the EN; we impose the obvious one

# ISO 639-1 assigned primary subtags — conformance snapshot (extendable).
# A5: "gr" is NOT assigned (Greek is "el").
ISO639_1_ASSIGNED = frozenset(
    "aa ab af am ar as az ba be bg bn bo br bs ca cs cy da de dz el en eo es "
    "et eu fa fi fo fr fy ga gd gl gu he hi hr hu hy ia id is it ja ka kk km "
    "kn ko ku ky la lg lt lv mk ml mn mr ms mt ne nl no oc om or pa pl ps pt "
    "qu ro ru sa sd si sk sl so sq sr sv sw ta te tg th tk tl tr tt ug uk ur "
    "uz vi vo wa yo zh zu".split()
)

_BCP47_RE = re.compile(
    r"^([A-Za-z]{2,8})(-[A-Za-z0-9]{1,8})*$"
)
_ASCII_HYPHEN_TS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$"
)


def _issue(path: str, code: str, message: str) -> ValidationIssue:
    return ValidationIssue(path=path, keyword=code, message=message)


def validate_en18223_document(doc: Mapping[str, Any]) -> list[ValidationIssue]:
    """Validate an EN 18223-style passport document against AUDIT A1–A6 rules.

    The rules encode what the EN *normatively* says (lowercase granularity
    enumeration, lowercase status enumeration, ISO 8601-1 timestamps with
    ASCII separators, ISO 639/BCP 47 language tags, the prose class-name
    spelling) — the very clauses the EN's own examples violate.
    """
    issues: list[ValidationIssue] = []

    # A1: granularity enumeration is lowercase (model, batch, item).
    gran = doc.get("granularity")
    if gran is not None:
        if gran not in EN18223_GRANULARITIES:
            if str(gran).lower() in EN18223_GRANULARITIES:
                issues.append(
                    _issue(
                        "$.granularity",
                        "A1-granularity-casing",
                        f"granularity {gran!r} violates the normative lowercase "
                        f"enumeration {list(EN18223_GRANULARITIES)} (EN 18223 §4.1.2.2)",
                    )
                )
            else:
                issues.append(
                    _issue(
                        "$.granularity",
                        "granularity-enum",
                        f"granularity {gran!r} not in {list(EN18223_GRANULARITIES)}",
                    )
                )

    # A2: dppStatus enumeration is lowercase.
    status = doc.get("dppStatus")
    if status is not None and status not in EN18223_STATUSES:
        if str(status).lower() in EN18223_STATUSES:
            issues.append(
                _issue(
                    "$.dppStatus",
                    "A2-status-casing",
                    f"dppStatus {status!r} violates the lowercase enumeration "
                    f"{list(EN18223_STATUSES)} (EN 18223 §4.1.2.1)",
                )
            )
        else:
            issues.append(
                _issue(
                    "$.dppStatus",
                    "dppStatus-enum",
                    f"dppStatus {status!r} not in {list(EN18223_STATUSES)}",
                )
            )

    # Key-name casing drift: the normative key is lastUpdated.
    for key in doc:
        if key.lower().startswith("lastupdat") and key != "lastUpdated":
            issues.append(
                _issue(
                    f"$.{key}",
                    "A0-key-casing-drift",
                    f"key {key!r} drifts from the normative 'lastUpdated' casing",
                )
            )

    # A3: class-name spelling (tables vs prose).
    def walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            cls = node.get("class") or node.get("className") or node.get("type")
            if isinstance(cls, str) and cls.endswith("DataElement"):
                if cls not in EN18223_CLASS_NAMES:
                    issues.append(
                        _issue(
                            path,
                            "A3-class-name-drift",
                            f"class name {cls!r} is not one of the defined "
                            f"{list(EN18223_CLASS_NAMES)} (EN 18223 §4.1.2.1/5.2.6 "
                            "SingleValuedDataElement vs SingleValueDataElement)",
                        )
                    )
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(doc, "$")

    # A5: language tag must be an assigned ISO 639-1 primary subtag or a
    # well-formed BCP 47 tag with assigned primary subtag.
    for key in ("language", "lang"):
        lang = doc.get(key)
        if lang is None:
            continue
        if not isinstance(lang, str) or not _BCP47_RE.match(lang):
            issues.append(
                _issue(f"$.{key}", "A5-language-tag-malformed", f"not a well-formed BCP 47 tag: {lang!r}")
            )
            continue
        primary = lang.split("-")[0].lower()
        if len(primary) == 2 and primary not in ISO639_1_ASSIGNED:
            issues.append(
                _issue(
                    f"$.{key}",
                    "A5-language-tag-unassigned",
                    f"primary subtag {primary!r} is not an assigned ISO 639-1 code "
                    "(e.g. Greek is 'el', not 'gr')",
                )
            )

    # A4: strict ISO 8601-1 timestamps — ASCII separators only.
    for key in ("lastUpdated", "validFrom", "validUntil", "issuedAt"):
        ts = doc.get(key)
        if ts is None:
            continue
        if isinstance(ts, str) and not _ASCII_HYPHEN_TS_RE.match(ts):
            detail = " (en/em dashes are not ISO 8601-1 separators)" if any(
                c in ts for c in ("–", "—")
            ) else ""
            issues.append(
                _issue(
                    f"$.{key}",
                    "A4-timestamp-not-iso8601",
                    f"{ts!r} is not an ISO 8601-1 date-time{detail}",
                )
            )

    # A6: schema-version placeholder / no grammar.
    sv = doc.get("dppSchemaVersion")
    if sv is not None:
        if not isinstance(sv, str) or not EN18223_SCHEMA_VERSION_RE.match(sv):
            issues.append(
                _issue(
                    "$.dppSchemaVersion",
                    "A6-schema-version-placeholder",
                    f"dppSchemaVersion {sv!r} does not match the required grammar "
                    f"{EN18223_SCHEMA_VERSION_RE.pattern} (placeholders like 'ENXXX:v1.0' "
                    "or draft self-references are not versions)",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Negative corpus: AUDIT.md A1–A6 as executable fixtures
# ---------------------------------------------------------------------------


def _en_doc(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "granularity": "item",
        "dppStatus": "active",
        "lastUpdated": "2025-08-22T03:12:00Z",
        "language": "el",
        "dppSchemaVersion": "EN18223:v1.0",
        "dataElements": [
            {"class": "SingleValueDataElement", "id": "de.dpp.operator-id"}
        ],
    }
    base.update(overrides)
    return base


def negative_fixtures_a1_a6() -> list[dict[str, Any]]:
    """The AUDIT.md A1–A6 defects, encoded exactly as the EN prints them."""
    return [
        {
            "fixture": "AUDIT-A1",
            "kind": "negative",
            "source": "EN 18223 §4.1.2.2 vs §5.2.4 — granularity 'Model' vs lowercase enumeration",
            "document": _en_doc(granularity="Model"),
            "expectCode": "A1-granularity-casing",
        },
        {
            "fixture": "AUDIT-A2",
            "kind": "negative",
            "source": "EN 18223 §4.1.2.1 vs §5.2.4 — dppStatus 'Active' vs lowercase enumeration",
            "document": _en_doc(dppStatus="Active"),
            "expectCode": "A2-status-casing",
        },
        {
            "fixture": "AUDIT-A3",
            "kind": "negative",
            "source": "EN 18223 §4.1.2.1/5.2.6 — SingleValuedDataElement vs SingleValueDataElement",
            "document": _en_doc(
                dataElements=[
                    {"class": "SingleValuedDataElement", "id": "de.dpp.operator-id"}
                ]
            ),
            "expectCode": "A3-class-name-drift",
        },
        {
            "fixture": "AUDIT-A4",
            "kind": "negative",
            "source": "EN 18223 Annex B Ex.1 — lastUpdated printed with en-dashes",
            "document": _en_doc(lastUpdated="2025–08–22T03:12:00Z"),
            "expectCode": "A4-timestamp-not-iso8601",
        },
        {
            "fixture": "AUDIT-A5",
            "kind": "negative",
            "source": "EN 18223 Annex A Ex.6 — language tag 'gr' (Greek is 'el' per ISO 639)",
            "document": _en_doc(language="gr"),
            "expectCode": "A5-language-tag-unassigned",
        },
        {
            "fixture": "AUDIT-A6",
            "kind": "negative",
            "source": "EN 18223 §5.2.4/Annex B — dppSchemaVersion placeholder 'ENXXX:v1.0'",
            "document": _en_doc(dppSchemaVersion="ENXXX:v1.0"),
            "expectCode": "A6-schema-version-placeholder",
        },
        {
            "fixture": "AUDIT-A0-keydrift",
            "kind": "negative",
            "source": "corpus-wide casing drift — lastUpdate vs normative lastUpdated",
            "document": dict(_en_doc(), lastUpdate="2025-08-22T03:12:00Z"),
            "expectCode": "A0-key-casing-drift",
        },
    ]


# ---------------------------------------------------------------------------
# Check registry
# ---------------------------------------------------------------------------


@dataclass
class ConformanceCheck:
    id: str
    title: str
    fn: Callable[[dict[str, Any]], list[M.Finding]]


@dataclass
class Fixture:
    name: str
    kind: str  # "positive" | "negative" | "file"
    data: dict[str, Any]
    source: str = ""
    expect_code: str | None = None


def _f(severity: str, code: str, message: str) -> M.Finding:
    return M.Finding(severity=severity, code=code, message=message)


def _check_positive(fixture: dict[str, Any]) -> list[M.Finding]:
    """Validate a built positive fixture against the wire schemas."""
    findings: list[M.Finding] = []
    manifest = fixture["manifest"]
    events = fixture["events"]
    links = fixture.get("links", [])

    result = M.validate_manifest(manifest)
    if not result.valid:
        findings.extend(
            _f("error", "manifest-schema", f"{i.path}: {i.message}") for i in result.issues
        )
    for event in events:
        result = M.validate_event(event)
        if not result.valid:
            findings.extend(
                _f("error", "event-schema", f"{i.path}: {i.message}") for i in result.issues
            )
    if not verify_chain(events):
        findings.append(_f("error", "chain-integrity", "event log commitment chain broken"))
    for link in links:
        result = M.validate_link(link)
        if not result.valid:
            findings.extend(
                _f("error", "link-schema", f"{i.path}: {i.message}") for i in result.issues
            )
    cap = M.CLASS_CAPABILITY[manifest.capability_class]
    if cap.max_freshness is None:
        satisfiable = M.freshness_satisfiable("unknown", manifest.capability_class)
    else:
        satisfiable = M.freshness_satisfiable(cap.max_freshness, manifest.capability_class)
    if not satisfiable:
        findings.append(
            _f("error", "capability", "class's own freshness bound is unsatisfiable")
        )
    return findings


def _check_en18223(fixture: dict[str, Any]) -> list[M.Finding]:
    """Run the AUDIT-derived EN document rules; a negative fixture must trip."""
    doc = fixture["document"]
    issues = validate_en18223_document(doc)
    return [
        _f(
            "error" if fixture.get("kind") == "negative" else "warning",
            i.keyword,
            i.message,
        )
        for i in issues
    ]


def positive_fixtures() -> list[Fixture]:
    laptop = build_laptop()
    car = build_car()
    return [
        Fixture(
            name="laptop",
            kind="positive",
            source="unidpp-ts fixtures/laptop.ts (PLAN stream 11 deliverable)",
            data={
                "manifest": laptop.manifest,
                "events": laptop.events,
                "links": laptop.links,
            },
        ),
        Fixture(
            name="car",
            kind="positive",
            source="unidpp-ts fixtures/car.ts (PLAN P4 pilot core)",
            data={
                "manifest": car.car["manifest"],
                "events": car.car["events"],
                "links": car.links,
            },
        ),
        Fixture(
            name="battery",
            kind="positive",
            source="unidpp-ts fixtures/car.ts battery sub-passport",
            data={
                "manifest": car.battery["manifest"],
                "events": car.battery["events"],
                "links": [],
            },
        ),
    ]


CHECK_REGISTRY: dict[str, ConformanceCheck] = {
    "positive-corpus": ConformanceCheck(
        id="positive-corpus",
        title="Ported TS fixtures validate against the wire schemas and chains verify",
        fn=_check_positive,
    ),
    "audit-negative": ConformanceCheck(
        id="audit-negative",
        title="AUDIT.md A1-A6 defects fail validation with precise findings",
        fn=_check_en18223,
    ),
}


def load_fixtures(directory: str | Path) -> list[Fixture]:
    """Load JSON fixtures from a directory.

    Positive fixtures carry ``{"kind": "positive", "manifest": {...},
    "events": [...]}``; negative EN documents carry ``{"kind": "negative",
    "document": {...}, "expectCode": "..."}``.
    """
    out: list[Fixture] = []
    for path in sorted(Path(directory).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        out.append(
            Fixture(
                name=path.stem,
                kind=data.get("kind", "positive"),
                data=data,
                source=str(path),
                expect_code=data.get("expectCode"),
            )
        )
    return out


def run_conformance(
    fixtures: list[Fixture] | None = None,
    directory: str | Path | None = None,
) -> dict[str, Any]:
    """Run the conformance suite; returns the report as a JSON-ready dict."""
    if fixtures is None:
        fixtures = []
        if directory is not None:
            fixtures.extend(load_fixtures(directory))

    results: list[dict[str, Any]] = []
    total = passed = 0

    # Positive corpus.
    for fixture in [f for f in fixtures if f.kind == "positive"] + positive_fixtures():
        total += 1
        findings = CHECK_REGISTRY["positive-corpus"].fn(fixture.data)
        ok = not findings
        passed += ok
        results.append(
            {
                "fixture": fixture.name,
                "kind": "positive",
                "source": fixture.source,
                "outcome": "pass" if ok else "fail",
                "findings": [f.__dict__ for f in findings],
            }
        )

    # Negative corpus: built-in AUDIT A1-A6 plus any file-loaded negatives.
    negatives = [f for f in fixtures if f.kind == "negative"]
    builtin = {
        n["fixture"]: n for n in negative_fixtures_a1_a6()
    }
    for name, n in builtin.items():
        total += 1
        findings = CHECK_REGISTRY["audit-negative"].fn(n)
        codes = [f.code for f in findings]
        expected = n["expectCode"]
        ok = bool(findings) and (expected is None or expected in codes)
        passed += ok
        results.append(
            {
                "fixture": name,
                "kind": "negative",
                "source": n["source"],
                "outcome": "pass" if ok else "fail",
                "expectedCode": expected,
                "findings": [f.__dict__ for f in findings],
            }
        )
    for fixture in negatives:
        total += 1
        findings = CHECK_REGISTRY["audit-negative"].fn(fixture.data)
        codes = [f.code for f in findings]
        ok = bool(findings) and (
            fixture.expect_code is None or fixture.expect_code in codes
        )
        passed += ok
        results.append(
            {
                "fixture": fixture.name,
                "kind": "negative",
                "source": fixture.source,
                "outcome": "pass" if ok else "fail",
                "expectedCode": fixture.expect_code,
                "findings": [f.__dict__ for f in findings],
            }
        )

    return {
        "generatedAt": __import__("unidpp.verify", fromlist=["now_iso"]).now_iso(),
        "suite": "unidpp-py conformance",
        "checks": [c.id for c in CHECK_REGISTRY.values()],
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "results": results,
    }


def write_json_report(report: dict[str, Any], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def write_markdown_report(report: dict[str, Any], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# UniDPP conformance report",
        "",
        f"Generated: {report['generatedAt']}",
        "",
        f"- Total fixtures: **{report['total']}**",
        f"- Passed: **{report['passed']}**",
        f"- Failed: **{report['failed']}**",
        "",
        "| Fixture | Kind | Outcome |",
        "|---|---|---|",
    ]
    for r in report["results"]:
        lines.append(f"| {r['fixture']} | {r['kind']} | {r['outcome']} |")
    lines.append("")
    for r in report["results"]:
        if not r["findings"]:
            continue
        lines.append(f"## {r['fixture']} ({r['kind']}) — {r['outcome']}")
        lines.append("")
        if r.get("source"):
            lines.append(f"Source: {r['source']}")
            lines.append("")
        for f in r["findings"]:
            lines.append(f"- `{f['code']}` ({f['severity']}): {f['message']}")
        lines.append("")
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    out_dir = "reports"
    fixture_dir = None
    it = iter(argv)
    for arg in it:
        if arg == "--out":
            out_dir = next(it, "reports")
        elif arg == "--fixtures":
            fixture_dir = next(it, None)
    report = run_conformance(directory=fixture_dir)
    jp = write_json_report(report, Path(out_dir) / "conformance-report.json")
    mp = write_markdown_report(report, Path(out_dir) / "conformance-report.md")
    print(f"conformance: {report['passed']}/{report['total']} passed")
    print(f"json: {jp}")
    print(f"markdown: {mp}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
