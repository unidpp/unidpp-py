# unidpp-py

The UniDPP Python library — the semantics mirror and conformance
tooling. Part of UniDPP (github.com/unidpp). License: MIT.

Pure stdlib (no runtime dependencies). The package mirrors the
Rust/TypeScript core so the semantics have a second, independent
statement:

- `unidpp.model` — the mirrored model (documents, findings, verdicts);
- `unidpp.eventlog` — the commitment-chained event log;
- `unidpp.verify` — the verification-pipeline harness (the I13
  degradation ladder + I9 verdicts; stdlib `hmac`/`hashlib` replace
  WebCrypto, ECDSA is a deliberate unsupported-slot placeholder per
  the multi-suite degrade model);
- `unidpp.canonical` — canonical JSON (RFC 8785-lite);
- `unidpp.adapters` — protocol adapters: `untp` (UNTP verifiable
  credentials), `en18223` (the EN 18223 document validator +
  EU-profile runner), `epcis`;
- `unidpp.temporal` — the DPP temporal profile;
- `unidpp.carrier` — QR carrier-budget conformance;
- `unidpp.conformance` — the conformance runner.

## Conformance

The conformance runner proves the validators catch real defects, not
synthetic strawmen. `CHECK_REGISTRY` carries the check classes:

| check | what it proves |
|---|---|
| `positive-corpus` | the ported TS fixtures (laptop, car) validate against the wire schemas and their chains verify |
| `audit-negative` | the AUDIT A1–A6 corpus defects (found in EN 18223's own examples) fail with precise findings |
| `temporal-conformance` | every timestamp field conforms to the DPP temporal profile (ISO 8601-1:2019 incl. Amd 1:2022 disambiguation) |
| `carrier-budget` | serialized payload sizes fit their declared carrier class (ISO/IEC 18004 QR capacity tables, ported from the CLI) |

```sh
python -m unidpp.conformance --out reports/
```

The **temporal profile** (`unidpp.temporal`) validates every
timestamp field with a distinct finding code — separator typography
(`T1`, the en-dash the EN's own Annex B prints), extended-format and
precision rules, calendar ranges, the `24:00:00` end-of-day form,
timezone discipline, and the decimal sign:

```pycon
>>> from unidpp.temporal import validate_timestamp
>>> validate_timestamp("2025–08–22T03:12:00Z", "lastUpdated").code
'T1-separator-typography'
>>> validate_timestamp("2025-08-22T03:12:00Z", "lastUpdated") is None
True
```

The **carrier budget** (`unidpp.carrier`) measures the canonical
serialized size of a payload against the ported ISO/IEC 18004 QR
byte-capacity tables; a payload that exceeds its declared class is
flagged with the computed size versus the capacity — never silently
truncated:

```pycon
>>> from unidpp.carrier import measure
>>> m = measure({"a": "x" * 380}, declared="qr-v15-M")
>>> (m.size_bytes, m.fits_declared)
(388, True)
```

Two report suites build on the runner (`scripts/`):

- **EU profile** (`eu_profile_report.py`) — the full EN 18223:2026
  example corpus through the validators. The corpus itself is an
  extraction from licensed sources and is deliberately **not
  distributed** with the repository (gitignored); the suite runs
  where the corpus is present and its findings are published as
  `conformance/eu-profile/REPORT.md`.
- **Competitor register** (`competitor_report.py`) — the published
  artifacts of the open-source DPP implementations (freeDPP live
  endpoints, open-dpp's e2e fixture) through the same pipeline, with
  verbatim source citations; findings in
  `conformance/competitors/REPORT.md`.

## Build & test

```sh
pip install -e ".[test]"
pytest
```

The suite covers the model, event log, verification ladder, adapters
(UNTP round-trip, EN 18223 projection), the conformance checks
(temporal, carrier, corpus), and the competitor register. The
EU-profile corpus tests skip automatically when the licensed
extraction is not present.
