# UniDPP competitor conformance report — freeDPP & open-dpp published artifacts

Generated: 2026-09-07T17:34:45Z

**Companion to the EU-profile report.** This report records a machine-run of every artifact published by freeDPP (github.com/OttoHandle/freeDPP) and open-dpp (github.com/open-dpp/open-dpp) through the same EN 18223 conformance pipeline (`unidpp.adapters.en18223.validate_profile_fixture`) that produced the `conformance/eu-profile/REPORT.md` register.

## 0. Guardrails

- no runner-semantic changes — `validate_profile_fixture` runs unchanged
- no manufactured findings — coverage observations only for out-of-scope formats
- no FUD — PASSes are reported as PASSes alongside FAILs
- no personality — neutral register; findings cite the artifact verbatim

## 1. Method

- Artifacts collected per vendor: see vendor sections (§3, §4) for exact URLs, capture commands, and license notes.
- Pipeline: same runner as the EU-profile report (`scripts/eu_profile_report.py`); the runner is invoked with no parameter changes — its semantics encode what EN 18223 normatively says (lowercase granularity enumeration, lowercase status enumeration, ISO 8601-1 timestamps with ASCII separators, ISO 639-1/BCP 47 language tags, the prose class-name spelling, valueDataType/value JSON-type consistency, etc.).
- Format detection: the runner inspects each artifact's top-level shape. Artifacts that carry the EN 18223 header keys (`digitalProductPassportId`, `uniqueProductIdentifier`, `granularity`, `dppSchemaVersion`, `dppStatus`, `lastUpdated`, `economicOperatorId`, `facilityId`, `contentSpecificationIds`) or an `elements[]` tree are run through all four validation layers (AUDIT A-rules on the header, EU-profile JSON Schemas, EU-profile semantic rules, neutral-core identifier mapping).
- Artifacts that are NOT EN 18223-shaped receive a single info-severity `format-not-en-18223` coverage observation; the validator layers are not invoked. No findings are manufactured. The observation records the artifact's declared format/version and its top-level keys; the rationale is documented as the runner semantics.
- Temporal layer: EN 18223-shaped artifacts additionally run the DPP temporal profile (`unidpp.temporal`) — every timestamp field against ISO 8601-1:2019 as impacted by Amd 1:2022, with precise-path findings (e.g. a server-local timestamp with no timezone designator).
- Carrier column: canonical serialized size against the ISO/IEC 18004 QR byte-capacity tables (`unidpp.carrier`, ported from the CLI's tables). An observation only — carrier budgets bind Tier-A carrier-embedded packs, not served documents; no finding is raised from it.
- Outcome semantics: pass = zero error-severity findings (artifact is consistent with the EN 18223 normative text); fail = one or more error-severity findings; not-applicable = artifact is not EN 18223-shaped and is recorded as a coverage observation only.

## 2. Results summary

- Vendors: **2** (freeDPP, open-dpp)
- Artifacts run: **7**
- Pass: **0**
- Fail (error-severity findings): **6**
- Not applicable (different wire format): **1**
- Error-severity findings (across vendors): **251**

| Vendor | Artifacts | Pass | Fail | N/A | Error findings |
|---|---|---|---|---|---|
| freedpp | 6 | 0 | 6 | 0 | 251 |
| open-dpp | 1 | 0 | 0 | 1 | 0 |

## 3. freeDPP

**freeDPP (Otto Handle / CEN/CLC/JTC 24 WG 4 convenor)**

Repo: `https://github.com/OttoHandle/freeDPP`

License: GPL-3.0 (LICENSE in the overview repo, mirrored in sources/)

Published artifacts: four published repos: the overview repo (github.com/OttoHandle/freeDPP, 4 markdown files) plus the implementation — freeDPPserver (C#/.NET 8 API serving both EN 18223 serializations), freeDPPdatabase (SQL Server schema CreateDb.sql, 2048 lines), freeDPPgui (management frontend). Two live test endpoints at https://drill.freedpp.eu and https://insulation.freedpp.eu serve the wire payloads this run exercises: the permalink route (/01/<GTIN>) and the EN 18222 API route (/v1/dppsByProductId/<GTIN>?representation=full|compressed).

Fetch / capture commands:

```bash
git clone --depth 1 https://github.com/OttoHandle/freeDPP.git conformance/competitors/freedpp/repo
git clone --depth 1 https://github.com/OttoHandle/freeDPPserver.git freeDPPserver
git clone --depth 1 https://github.com/OttoHandle/freeDPPdatabase.git freeDPPdatabase
curl -sH 'Accept: application/json' https://drill.freedpp.eu/01/5012345101095 -o conformance/competitors/freedpp/artifacts/drill-test1.json
curl -sH 'Accept: application/json' 'https://drill.freedpp.eu/v1/dppsByProductId/5012345101095?representation=full' -o conformance/competitors/freedpp/artifacts/drill-api-full.json
curl -sH 'Accept: application/json' 'https://drill.freedpp.eu/v1/dppsByProductId/5012345101095?representation=compressed' -o conformance/competitors/freedpp/artifacts/drill-api-compressed.json
curl -sH 'Accept: application/json' https://insulation.freedpp.eu/01/4003973287696 -o conformance/competitors/freedpp/artifacts/insulation-test2.json
curl -sH 'Accept: application/json' 'https://insulation.freedpp.eu/v1/dppsByProductId/4003973287696?representation=full' -o conformance/competitors/freedpp/artifacts/insulation-api-full.json
curl -sH 'Accept: application/json' 'https://insulation.freedpp.eu/v1/dppsByProductId/4003973287696?representation=compressed' -o conformance/competitors/freedpp/artifacts/insulation-api-compressed.json
```

### 3.1 freeDPP totals

- Artifacts: **6**
- Pass: **0**
- Fail: **6**
- Error findings: **251**

Findings by AUDIT id (matches the EU-profile register):

| AUDIT id | Count |
|---|---|
| A1 | 6 |
| A3 | 170 |
| A4 | 6 |
| A6 | 6 |
| C4 | 6 |
| N3 | 10 |
| N4 | 42 |
| N5 | 2 |

Note: the AUDIT A3 finding counts the same class-name drift that the EU-profile report also records 9 times against EN 18223's own Annex A examples (the EN's prose uses `SingleValueDataElement` while its tables use `SingleValuedDataElement`). The competitor's use of the table spelling is consistent with what the EN's own examples print; the runner's job is to surface the drift, not to adjudicate it.

Serialization asymmetry (factual): the `?representation=compressed` artifacts carry only header-level findings, while the expanded artifacts additionally carry the element-tree findings (A3, N3, N4, N5). The compressed form keys data by elementId without objectType, so the promotion (PA4) synthesizes the prose-canonical class spelling and positional elementIds — nothing in the compressed serialization itself trips A3/N3/N4/N5. The expanded form as served prints the Annex-A table spelling and duplicate elementIds verbatim (see §3.4 S6 for the code origin).

### 3.2 freeDPP per-artifact results

| Artifact | Outcome | Error findings | Distinct codes | Carrier |
|---|---|---|---|---|
| drill-api-compressed | fail | 5 | 5 (A1-granularity-casing, A6-schema-version-placeholder, C4-content-spec-placeholder, T7-timezone-missing, profile-header-schema) | 2917 B · exceeds QR v40-M |
| drill-api-full | fail | 88 | 9 (A1-granularity-casing, A3-class-name-drift, A6-schema-version-placeholder, C4-content-spec-placeholder, N3-duplicate-element-id, N4-value-data-type-mismatch, N5-multivalued-child-key-divergence, T7-timezone-missing, profile-header-schema) | 15728 B · exceeds QR v40-M |
| drill-test1 | fail | 88 | 9 (A1-granularity-casing, A3-class-name-drift, A6-schema-version-placeholder, C4-content-spec-placeholder, N3-duplicate-element-id, N4-value-data-type-mismatch, N5-multivalued-child-key-divergence, T7-timezone-missing, profile-header-schema) | 15728 B · exceeds QR v40-M |
| insulation-api-compressed | fail | 4 | 5 (A1-granularity-casing, A6-schema-version-placeholder, C4-content-spec-placeholder, T7-timezone-missing, profile-header-schema) | 1410 B · QR v31-M |
| insulation-api-full | fail | 33 | 7 (A1-granularity-casing, A3-class-name-drift, A6-schema-version-placeholder, C4-content-spec-placeholder, N4-value-data-type-mismatch, T7-timezone-missing, profile-header-schema) | 6924 B · exceeds QR v40-M |
| insulation-test2 | fail | 33 | 7 (A1-granularity-casing, A3-class-name-drift, A6-schema-version-placeholder, C4-content-spec-placeholder, N4-value-data-type-mismatch, T7-timezone-missing, profile-header-schema) | 6924 B · exceeds QR v40-M |

### 3.3 freeDPP findings detail

#### drill-api-compressed — **fail**

Source: `GET https://drill.freedpp.eu/v1/dppsByProductId/5012345101095?representation=compressed — captured 2026-09-07`

- `A1-granularity-casing` (error, path `$.granularity`) **[AUDIT A1]**: granularity 'Model' violates the normative lowercase enumeration ['model', 'batch', 'item'] (EN 18223 §4.1.2.2)

- `A6-schema-version-placeholder` (error, path `$.dppSchemaVersion`) **[AUDIT A6]**: dppSchemaVersion '0.1' does not match the required grammar ^EN[0-9]{3,6}:v[0-9]+\.[0-9]+(\.[0-9]+)?$ (placeholders like 'ENXXX:v1.0' or draft self-references are not versions)

- `profile-header-schema` (error, path `$.lastUpdated`): $.lastUpdated: not a valid date-time: '2026-06-17T23:20:58.0000000' (Table 1, 4.1.2.1)

- `profile-header-schema` (error, path `$.facilityId`): $.facilityId: shorter than 1 (Table 1, 4.1.2.1)

- `C4-content-spec-placeholder` (info, path `$.contentSpecificationIds`) **[AUDIT C4]**: contentSpecificationIds values are placeholders (['EN 01234-5:2027']); identifier space, allocator and validation undefined (AUDIT C4).

  Citation:

  > ["EN 01234-5:2027"]

- `T7-timezone-missing` (error, path `$.lastUpdated`) **[AUDIT A4]**: '2026-06-17T23:20:58.0000000' carries no timezone designator; timestamps are UTC-based — use 'Z' or a numeric offset ±hh:mm (local time is a presentation concern; EN 18223 Table 1 (4.1.2.1): 'String formatted as Timestamp UTC-based according to ISO 8601-1:2019' (as impacted by ISO 8601-1:2019/A1:2022))

  Citation:

  > "lastUpdated": "2026-06-17T23:20:58.0000000"


#### drill-api-full — **fail**

Source: `GET https://drill.freedpp.eu/v1/dppsByProductId/5012345101095?representation=full — captured 2026-09-07`

- `A1-granularity-casing` (error, path `$.granularity`) **[AUDIT A1]**: granularity 'Model' violates the normative lowercase enumeration ['model', 'batch', 'item'] (EN 18223 §4.1.2.2)

- `A6-schema-version-placeholder` (error, path `$.dppSchemaVersion`) **[AUDIT A6]**: dppSchemaVersion '0.1' does not match the required grammar ^EN[0-9]{3,6}:v[0-9]+\.[0-9]+(\.[0-9]+)?$ (placeholders like 'ENXXX:v1.0' or draft self-references are not versions)

- `profile-header-schema` (error, path `$.lastUpdated`): $.lastUpdated: not a valid date-time: '2026-06-17T23:20:58' (Table 1, 4.1.2.1)

- `profile-header-schema` (error, path `$.facilityId`): $.facilityId: shorter than 1 (Table 1, 4.1.2.1)

- `N3-duplicate-element-id` (error, path `$.elements[0].elements[21].elementId`) **[AUDIT N3]**: elementId '_p_d_SafetyInstructions' is used by two siblings (elements[20] and elements[21]); Table 2 (4.1.2.3): 'The relative identifier of the DataElement shall be unique within its location (i.e. in the DataElementCollection or MultiValuedDataElement)' (finding N3).

  Citation:

  > "elementId": "_p_d_SafetyInstructions"

- `A3-class-name-drift` (error, path `$.elements[0].elements[0].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Citation:

  > "objectType": "SingleValuedDataElement"


… and **83** further findings, collapsed by identical message into 23 code(s):

- `A3-class-name-drift` (error) × **59 occurrences** **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Paths (first 5): `$.elements[0].elements[1].objectType`, `$.elements[0].elements[2].objectType`, `$.elements[0].elements[3].objectType`, `$.elements[0].elements[4].objectType`, `$.elements[0].elements[5].objectType` (+54 more)

  Citation:

  > "objectType": "SingleValuedDataElement"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '20'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[0].elements[2].value`

  Citation:

  > "value": "20"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:integer' with value serialized as a JSON string '1000'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[0].elements[5].value`

  Citation:

  > "value": "1000"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:integer' with value serialized as a JSON string '6'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[0].elements[8].value`

  Citation:

  > "value": "6"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '1.8'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[0].elements[13].value`

  Citation:

  > "value": "1.8"

- `N5-multivalued-child-key-divergence` (error) × **1 occurrences** **[AUDIT N5]**: MultiValuedDataElement children serialized under 'value'; Annex A Example 1 serializes the same class's children under 'elements'; Table 4 (4.1.2.6) models them as '[DataElement]' entries (finding N5).

  Paths (first 5): `$.elements[0].elements[14].value`

  Citation:

  > "value": [ { "elementId": "efficiencyRating1", … } ]

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '2'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[0].elements[15].value`

  Citation:

  > "value": "2"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '10'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[0].elements[19].value`

  Citation:

  > "value": "10"

- `N3-duplicate-element-id` (error) × **1 occurrences** **[AUDIT N3]**: elementId '_p_d_AddressLine2PostalCodeCity' is used by two siblings (elements[0] and elements[1]); Table 2 (4.1.2.3): 'The relative identifier of the DataElement shall be unique within its location (i.e. in the DataElementCollection or MultiValuedDataElement)' (finding N3).

  Paths (first 5): `$.elements[1].elements[1].elementId`

  Citation:

  > "elementId": "_p_d_AddressLine2PostalCodeCity"

- `N3-duplicate-element-id` (error) × **1 occurrences** **[AUDIT N3]**: elementId '_p_d_RecyclingInstructions' is used by two siblings (elements[0] and elements[1]); Table 2 (4.1.2.3): 'The relative identifier of the DataElement shall be unique within its location (i.e. in the DataElementCollection or MultiValuedDataElement)' (finding N3).

  Paths (first 5): `$.elements[4].elements[1].elementId`

  Citation:

  > "elementId": "_p_d_RecyclingInstructions"

- `N3-duplicate-element-id` (error) × **1 occurrences** **[AUDIT N3]**: elementId '_p_d_MaterialComposition' is used by two siblings (elements[2] and elements[3]); Table 2 (4.1.2.3): 'The relative identifier of the DataElement shall be unique within its location (i.e. in the DataElementCollection or MultiValuedDataElement)' (finding N3).

  Paths (first 5): `$.elements[4].elements[3].elementId`

  Citation:

  > "elementId": "_p_d_MaterialComposition"

- `N3-duplicate-element-id` (error) × **1 occurrences** **[AUDIT N3]**: elementId '_p_d_HazardousSubstancesConcentrationLocation' is used by two siblings (elements[4] and elements[5]); Table 2 (4.1.2.3): 'The relative identifier of the DataElement shall be unique within its location (i.e. in the DataElementCollection or MultiValuedDataElement)' (finding N3).

  Paths (first 5): `$.elements[4].elements[5].elementId`

  Citation:

  > "elementId": "_p_d_HazardousSubstancesConcentrationLocation"

- `N4-value-data-type-mismatch` (error) × **3 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '100'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[5].elements[0].value`, `$.elements[5].elements[2].value`, `$.elements[5].elements[6].value`

  Citation:

  > "value": "100"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '12'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[5].elements[4].value`

  Citation:

  > "value": "12"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '60'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[5].elements[5].value`

  Citation:

  > "value": "60"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '230'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[5].elements[7].value`

  Citation:

  > "value": "230"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '30'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[5].elements[8].value`

  Citation:

  > "value": "30"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '66'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[6].elements[0].value`

  Citation:

  > "value": "66"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '34'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[6].elements[1].value`

  Citation:

  > "value": "34"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '1'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[6].elements[2].value`

  Citation:

  > "value": "1"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '12016'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[6].elements[3].value`

  Citation:

  > "value": "12016"

- `C4-content-spec-placeholder` (info) × **1 occurrences** **[AUDIT C4]**: contentSpecificationIds values are placeholders (['EN 01234-5:2027']); identifier space, allocator and validation undefined (AUDIT C4).

  Paths (first 5): `$.contentSpecificationIds`

  Citation:

  > ["EN 01234-5:2027"]

- `T7-timezone-missing` (error) × **1 occurrences** **[AUDIT A4]**: '2026-06-17T23:20:58' carries no timezone designator; timestamps are UTC-based — use 'Z' or a numeric offset ±hh:mm (local time is a presentation concern; EN 18223 Table 1 (4.1.2.1): 'String formatted as Timestamp UTC-based according to ISO 8601-1:2019' (as impacted by ISO 8601-1:2019/A1:2022))

  Paths (first 5): `$.lastUpdated`

  Citation:

  > "lastUpdated": "2026-06-17T23:20:58"


#### drill-test1 — **fail**

Source: `GET https://drill.freedpp.eu/01/5012345101095 (Accept: application/json) — captured 2026-09-07`

- `A1-granularity-casing` (error, path `$.granularity`) **[AUDIT A1]**: granularity 'Model' violates the normative lowercase enumeration ['model', 'batch', 'item'] (EN 18223 §4.1.2.2)

- `A6-schema-version-placeholder` (error, path `$.dppSchemaVersion`) **[AUDIT A6]**: dppSchemaVersion '0.1' does not match the required grammar ^EN[0-9]{3,6}:v[0-9]+\.[0-9]+(\.[0-9]+)?$ (placeholders like 'ENXXX:v1.0' or draft self-references are not versions)

- `profile-header-schema` (error, path `$.lastUpdated`): $.lastUpdated: not a valid date-time: '2026-06-17T23:20:58' (Table 1, 4.1.2.1)

- `profile-header-schema` (error, path `$.facilityId`): $.facilityId: shorter than 1 (Table 1, 4.1.2.1)

- `N3-duplicate-element-id` (error, path `$.elements[0].elements[21].elementId`) **[AUDIT N3]**: elementId '_p_d_SafetyInstructions' is used by two siblings (elements[20] and elements[21]); Table 2 (4.1.2.3): 'The relative identifier of the DataElement shall be unique within its location (i.e. in the DataElementCollection or MultiValuedDataElement)' (finding N3).

  Citation:

  > "elementId": "_p_d_SafetyInstructions"

- `A3-class-name-drift` (error, path `$.elements[0].elements[0].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Citation:

  > "objectType": "SingleValuedDataElement"


… and **83** further findings, collapsed by identical message into 23 code(s):

- `A3-class-name-drift` (error) × **59 occurrences** **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Paths (first 5): `$.elements[0].elements[1].objectType`, `$.elements[0].elements[2].objectType`, `$.elements[0].elements[3].objectType`, `$.elements[0].elements[4].objectType`, `$.elements[0].elements[5].objectType` (+54 more)

  Citation:

  > "objectType": "SingleValuedDataElement"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '20'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[0].elements[2].value`

  Citation:

  > "value": "20"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:integer' with value serialized as a JSON string '1000'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[0].elements[5].value`

  Citation:

  > "value": "1000"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:integer' with value serialized as a JSON string '6'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[0].elements[8].value`

  Citation:

  > "value": "6"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '1.8'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[0].elements[13].value`

  Citation:

  > "value": "1.8"

- `N5-multivalued-child-key-divergence` (error) × **1 occurrences** **[AUDIT N5]**: MultiValuedDataElement children serialized under 'value'; Annex A Example 1 serializes the same class's children under 'elements'; Table 4 (4.1.2.6) models them as '[DataElement]' entries (finding N5).

  Paths (first 5): `$.elements[0].elements[14].value`

  Citation:

  > "value": [ { "elementId": "efficiencyRating1", … } ]

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '2'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[0].elements[15].value`

  Citation:

  > "value": "2"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '10'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[0].elements[19].value`

  Citation:

  > "value": "10"

- `N3-duplicate-element-id` (error) × **1 occurrences** **[AUDIT N3]**: elementId '_p_d_AddressLine2PostalCodeCity' is used by two siblings (elements[0] and elements[1]); Table 2 (4.1.2.3): 'The relative identifier of the DataElement shall be unique within its location (i.e. in the DataElementCollection or MultiValuedDataElement)' (finding N3).

  Paths (first 5): `$.elements[1].elements[1].elementId`

  Citation:

  > "elementId": "_p_d_AddressLine2PostalCodeCity"

- `N3-duplicate-element-id` (error) × **1 occurrences** **[AUDIT N3]**: elementId '_p_d_RecyclingInstructions' is used by two siblings (elements[0] and elements[1]); Table 2 (4.1.2.3): 'The relative identifier of the DataElement shall be unique within its location (i.e. in the DataElementCollection or MultiValuedDataElement)' (finding N3).

  Paths (first 5): `$.elements[4].elements[1].elementId`

  Citation:

  > "elementId": "_p_d_RecyclingInstructions"

- `N3-duplicate-element-id` (error) × **1 occurrences** **[AUDIT N3]**: elementId '_p_d_MaterialComposition' is used by two siblings (elements[2] and elements[3]); Table 2 (4.1.2.3): 'The relative identifier of the DataElement shall be unique within its location (i.e. in the DataElementCollection or MultiValuedDataElement)' (finding N3).

  Paths (first 5): `$.elements[4].elements[3].elementId`

  Citation:

  > "elementId": "_p_d_MaterialComposition"

- `N3-duplicate-element-id` (error) × **1 occurrences** **[AUDIT N3]**: elementId '_p_d_HazardousSubstancesConcentrationLocation' is used by two siblings (elements[4] and elements[5]); Table 2 (4.1.2.3): 'The relative identifier of the DataElement shall be unique within its location (i.e. in the DataElementCollection or MultiValuedDataElement)' (finding N3).

  Paths (first 5): `$.elements[4].elements[5].elementId`

  Citation:

  > "elementId": "_p_d_HazardousSubstancesConcentrationLocation"

- `N4-value-data-type-mismatch` (error) × **3 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '100'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[5].elements[0].value`, `$.elements[5].elements[2].value`, `$.elements[5].elements[6].value`

  Citation:

  > "value": "100"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '12'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[5].elements[4].value`

  Citation:

  > "value": "12"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '60'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[5].elements[5].value`

  Citation:

  > "value": "60"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '230'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[5].elements[7].value`

  Citation:

  > "value": "230"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '30'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[5].elements[8].value`

  Citation:

  > "value": "30"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '66'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[6].elements[0].value`

  Citation:

  > "value": "66"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '34'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[6].elements[1].value`

  Citation:

  > "value": "34"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '1'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[6].elements[2].value`

  Citation:

  > "value": "1"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:decimal' with value serialized as a JSON string '12016'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[6].elements[3].value`

  Citation:

  > "value": "12016"

- `C4-content-spec-placeholder` (info) × **1 occurrences** **[AUDIT C4]**: contentSpecificationIds values are placeholders (['EN 01234-5:2027']); identifier space, allocator and validation undefined (AUDIT C4).

  Paths (first 5): `$.contentSpecificationIds`

  Citation:

  > ["EN 01234-5:2027"]

- `T7-timezone-missing` (error) × **1 occurrences** **[AUDIT A4]**: '2026-06-17T23:20:58' carries no timezone designator; timestamps are UTC-based — use 'Z' or a numeric offset ±hh:mm (local time is a presentation concern; EN 18223 Table 1 (4.1.2.1): 'String formatted as Timestamp UTC-based according to ISO 8601-1:2019' (as impacted by ISO 8601-1:2019/A1:2022))

  Paths (first 5): `$.lastUpdated`

  Citation:

  > "lastUpdated": "2026-06-17T23:20:58"


#### insulation-api-compressed — **fail**

Source: `GET https://insulation.freedpp.eu/v1/dppsByProductId/4003973287696?representation=compressed — captured 2026-09-07`

- `A1-granularity-casing` (error, path `$.granularity`) **[AUDIT A1]**: granularity 'Model' violates the normative lowercase enumeration ['model', 'batch', 'item'] (EN 18223 §4.1.2.2)

- `A6-schema-version-placeholder` (error, path `$.dppSchemaVersion`) **[AUDIT A6]**: dppSchemaVersion '0.1' does not match the required grammar ^EN[0-9]{3,6}:v[0-9]+\.[0-9]+(\.[0-9]+)?$ (placeholders like 'ENXXX:v1.0' or draft self-references are not versions)

- `profile-header-schema` (error, path `$.lastUpdated`): $.lastUpdated: not a valid date-time: '2026-04-01T16:07:24.0000000' (Table 1, 4.1.2.1)

- `C4-content-spec-placeholder` (info, path `$.contentSpecificationIds`) **[AUDIT C4]**: contentSpecificationIds values are placeholders (['EN 13162:2012+A1:2015']); identifier space, allocator and validation undefined (AUDIT C4).

  Citation:

  > ["EN 13162:2012+A1:2015"]

- `T7-timezone-missing` (error, path `$.lastUpdated`) **[AUDIT A4]**: '2026-04-01T16:07:24.0000000' carries no timezone designator; timestamps are UTC-based — use 'Z' or a numeric offset ±hh:mm (local time is a presentation concern; EN 18223 Table 1 (4.1.2.1): 'String formatted as Timestamp UTC-based according to ISO 8601-1:2019' (as impacted by ISO 8601-1:2019/A1:2022))

  Citation:

  > "lastUpdated": "2026-04-01T16:07:24.0000000"


#### insulation-api-full — **fail**

Source: `GET https://insulation.freedpp.eu/v1/dppsByProductId/4003973287696?representation=full — captured 2026-09-07`

- `A1-granularity-casing` (error, path `$.granularity`) **[AUDIT A1]**: granularity 'Model' violates the normative lowercase enumeration ['model', 'batch', 'item'] (EN 18223 §4.1.2.2)

- `A6-schema-version-placeholder` (error, path `$.dppSchemaVersion`) **[AUDIT A6]**: dppSchemaVersion '0.1' does not match the required grammar ^EN[0-9]{3,6}:v[0-9]+\.[0-9]+(\.[0-9]+)?$ (placeholders like 'ENXXX:v1.0' or draft self-references are not versions)

- `profile-header-schema` (error, path `$.lastUpdated`): $.lastUpdated: not a valid date-time: '2026-04-01T16:07:24' (Table 1, 4.1.2.1)

- `A3-class-name-drift` (error, path `$.elements[0].elements[0].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Citation:

  > "objectType": "SingleValuedDataElement"

- `A3-class-name-drift` (error, path `$.elements[0].elements[1].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Citation:

  > "objectType": "SingleValuedDataElement"

- `A3-class-name-drift` (error, path `$.elements[0].elements[2].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Citation:

  > "objectType": "SingleValuedDataElement"


… and **28** further findings, collapsed by identical message into 7 code(s):

- `A3-class-name-drift` (error) × **22 occurrences** **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Paths (first 5): `$.elements[0].elements[3].objectType`, `$.elements[0].elements[4].objectType`, `$.elements[1].elements[0].objectType`, `$.elements[1].elements[1].objectType`, `$.elements[1].elements[2].objectType` (+17 more)

  Citation:

  > "objectType": "SingleValuedDataElement"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:float' with value serialized as a JSON string '0,0011'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[4].elements[0].elements[0].value`

  Citation:

  > "value": "0,0011"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:float' with value serialized as a JSON string '0.000012'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[4].elements[0].elements[1].value`

  Citation:

  > "value": "0.000012"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:float' with value serialized as a JSON string '1.01'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[4].elements[0].elements[2].value`

  Citation:

  > "value": "1.01"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:float' with value serialized as a JSON string '0,0022'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[4].elements[0].elements[3].value`

  Citation:

  > "value": "0,0022"

- `C4-content-spec-placeholder` (info) × **1 occurrences** **[AUDIT C4]**: contentSpecificationIds values are placeholders (['EN 13162:2012+A1:2015']); identifier space, allocator and validation undefined (AUDIT C4).

  Paths (first 5): `$.contentSpecificationIds`

  Citation:

  > ["EN 13162:2012+A1:2015"]

- `T7-timezone-missing` (error) × **1 occurrences** **[AUDIT A4]**: '2026-04-01T16:07:24' carries no timezone designator; timestamps are UTC-based — use 'Z' or a numeric offset ±hh:mm (local time is a presentation concern; EN 18223 Table 1 (4.1.2.1): 'String formatted as Timestamp UTC-based according to ISO 8601-1:2019' (as impacted by ISO 8601-1:2019/A1:2022))

  Paths (first 5): `$.lastUpdated`

  Citation:

  > "lastUpdated": "2026-04-01T16:07:24"


#### insulation-test2 — **fail**

Source: `GET https://insulation.freedpp.eu/01/4003973287696 (Accept: application/json) — captured 2026-09-07`

- `A1-granularity-casing` (error, path `$.granularity`) **[AUDIT A1]**: granularity 'Model' violates the normative lowercase enumeration ['model', 'batch', 'item'] (EN 18223 §4.1.2.2)

- `A6-schema-version-placeholder` (error, path `$.dppSchemaVersion`) **[AUDIT A6]**: dppSchemaVersion '0.1' does not match the required grammar ^EN[0-9]{3,6}:v[0-9]+\.[0-9]+(\.[0-9]+)?$ (placeholders like 'ENXXX:v1.0' or draft self-references are not versions)

- `profile-header-schema` (error, path `$.lastUpdated`): $.lastUpdated: not a valid date-time: '2026-04-01T16:07:24' (Table 1, 4.1.2.1)

- `A3-class-name-drift` (error, path `$.elements[0].elements[0].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Citation:

  > "objectType": "SingleValuedDataElement"

- `A3-class-name-drift` (error, path `$.elements[0].elements[1].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Citation:

  > "objectType": "SingleValuedDataElement"

- `A3-class-name-drift` (error, path `$.elements[0].elements[2].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Citation:

  > "objectType": "SingleValuedDataElement"


… and **28** further findings, collapsed by identical message into 7 code(s):

- `A3-class-name-drift` (error) × **22 occurrences** **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Paths (first 5): `$.elements[0].elements[3].objectType`, `$.elements[0].elements[4].objectType`, `$.elements[1].elements[0].objectType`, `$.elements[1].elements[1].objectType`, `$.elements[1].elements[2].objectType` (+17 more)

  Citation:

  > "objectType": "SingleValuedDataElement"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:float' with value serialized as a JSON string '0,0011'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[4].elements[0].elements[0].value`

  Citation:

  > "value": "0,0011"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:float' with value serialized as a JSON string '0.000012'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[4].elements[0].elements[1].value`

  Citation:

  > "value": "0.000012"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:float' with value serialized as a JSON string '1.01'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[4].elements[0].elements[2].value`

  Citation:

  > "value": "1.01"

- `N4-value-data-type-mismatch` (error) × **1 occurrences** **[AUDIT N4]**: valueDataType 'xsd:float' with value serialized as a JSON string '0,0022'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Paths (first 5): `$.elements[4].elements[0].elements[3].value`

  Citation:

  > "value": "0,0022"

- `C4-content-spec-placeholder` (info) × **1 occurrences** **[AUDIT C4]**: contentSpecificationIds values are placeholders (['EN 13162:2012+A1:2015']); identifier space, allocator and validation undefined (AUDIT C4).

  Paths (first 5): `$.contentSpecificationIds`

  Citation:

  > ["EN 13162:2012+A1:2015"]

- `T7-timezone-missing` (error) × **1 occurrences** **[AUDIT A4]**: '2026-04-01T16:07:24' carries no timezone designator; timestamps are UTC-based — use 'Z' or a numeric offset ±hh:mm (local time is a presentation concern; EN 18223 Table 1 (4.1.2.1): 'String formatted as Timestamp UTC-based according to ISO 8601-1:2019' (as impacted by ISO 8601-1:2019/A1:2022))

  Paths (first 5): `$.lastUpdated`

  Citation:

  > "lastUpdated": "2026-04-01T16:07:24"


### 3.4 freeDPP source-model corroboration (verbatim citations)

The wire findings above are traceable to the published server model (`github.com/OttoHandle/freeDPPserver`, mirrored under `conformance/competitors/freedpp/sources/server/`). Each citation below is loaded verbatim from the mirror by the runner; the run fails loudly if the mirror drifts from the citation.

- **S1** (freeDPPserver/FreeDppDppFull.cs:21): default granularity is the capitalized spelling — the origin of the A1-granularity-casing findings on every wire artifact

  Verbatim:

  > `            public string granularity { get; set; } = "Model"; //batch, item`

- **S2** (freeDPPserver/FreeDppDppFull.cs:22): default dppSchemaVersion does not carry the ENnnn:vX.Y form — the origin of the A6-schema-version-placeholder findings

  Verbatim:

  > `            public string dppSchemaVersion { get; set; } = "0.1";`

- **S3** (freeDPPserver/FreeDppDppFull.cs:23): default dppStatus is the capitalized spelling; the live payloads override it with the lowercase 'active' the EN's examples use

  Verbatim:

  > `            public string dppStatus { get; set; } = "Active";`

- **S4** (freeDPPserver/FreeDppDppFull.cs:24): lastUpdated defaults to server-local time (no timezone designator) — the origin of the not-a-valid-date-time findings

  Verbatim:

  > `            public DateTime lastUpdated { get; set; } = DateTime.Now;`

- **S5** (freeDPPserver/FreeDppDppFull.cs:28): the hash slot is explicitly deferred: integrity is 'to be handled when EN 18239 published' — the trust surface is pending by the vendor's own statement (also FUNCTIONALITY.md: 'security frameworks according EN 18239 and EN 18246 to be delivered after publication of these standards')

  Verbatim:

  > `            public string hashMD5 { get; set; } // not yet, to be handled when EN 18239 published; but must not be deleted because JS code needs it`

- **S6** (freeDPPserver/FreeDppDppFull.cs:71): the class name follows the EN's Annex A spelling 'SingleValuedDataElement' — the origin of the A3-class-name-drift findings; the comment cites the standard's annex as its source

  Verbatim:

  > `            public string objectType { get; set; } = "SingleValuedDataElement";// laut annex 1 `

- **S7** (freeDPPserver/DppValidateController.cs:6): the server's own DPP validation endpoint is a test controller, 'not yet comletely implemented - just a test controller for dpp validation'

  Verbatim:

  > `//oh260810 - not yet comletely implemented - just a test controller for dpp validation`

- **S8** (freeDPPserver/DppValidateController.cs:18): the validator references Schemas/dpp-schema.json; no Schemas directory exists anywhere in the published freeDPPserver repo (working tree or PublishedVersion260813.zip)

  Verbatim:

  > `    private readonly string _schemaPfad = Path.Combine("Schemas", "dpp-schema.json");`

## 4. open-dpp

**open-dpp (open-source DPP platform; github.com/open-dpp)**

Repo: `https://github.com/open-dpp/open-dpp`

License: AGPL-3.0 (LICENSE in the repo, mirrored in sources/)

Published artifacts: source tree (pnpm monorepo). The only example document in machine-checkable form is the e2e battery-passport fixture (`apps/e2e/tests/api/battery-passport.ts`), exporting a `Battery_Passport` object literal in `open-dpp:json` v4.0 format — AAS-based (environment.assetAdministrationShells / submodels / conceptDescriptions), NOT EN 18223.

Fetch / extract commands:

```bash
git clone --depth 1 https://github.com/open-dpp/open-dpp.git conformance/competitors/open-dpp/repo
# extract Battery_Passport with esbuild (transpile TS) + node (execute):
node scripts/extract-ts-fixture.cjs apps/e2e/tests/api/battery-passport.ts Battery_Passport conformance/competitors/open-dpp/artifacts/battery-passport.json
```

### 4.1 open-dpp totals

- Artifacts: **1**
- Pass: **0**
- Fail: **0**
- Not applicable: **1**

info-severity coverage-observation codes:

| Code | Count |
|---|---|
| format-not-en-18223 | 1 |

### 4.2 open-dpp per-artifact results

| Artifact | Outcome | Error findings | Distinct codes | Carrier |
|---|---|---|---|---|
| battery-passport.json | not-applicable | 0 | 1 (format-not-en-18223) | 70400 B · exceeds QR v40-M |

### 4.3 open-dpp findings detail

#### battery-passport.json — **not-applicable**

Source: `conformance/competitors/open-dpp/artifacts/battery-passport.json`

- `format-not-en-18223` (info, path `$`): artifact declares format 'open-dpp:json' version '4.0'; carries top-level keys ['createdAt', 'environment', 'format', 'id', 'lastStatusChange', 'presentationConfiguration', 'updatedAt', 'version']; overlap with the EN 18223 header keys is [] (none or one). Coverage observation only — the conformance runner is the EU-profile runner; this format is out of its machine-checkable surface.

  Citation:

  > EN 18223 Table 1 (4.1.2.1) header keys: digitalProductPassportId, uniqueProductIdentifier, granularity, dppSchemaVersion, dppStatus, lastUpdated, economicOperatorId, facilityId, contentSpecificationIds.


## 5. Coverage observations (where the runner's machine-checkable surface ends)

The machine-checkable surface of both vendors' published material is the EU wire envelope — what EN 18223 says a passport document must contain at serialization level. The runner can verify claims on that surface (class-name spelling, value-data-type consistency, element-ID uniqueness, granularity/status casing, ISO 8601-1 timestamps, language-tag validity) and this report does. What the published artifacts do not expose to machine checking:

- **freeDPP** publishes full server source (C#/.NET 8) and both serializations on the wire. Its own code comments place the trust/integrity surface after the pending standards: the `hashMD5` slot is 'not yet, to be handled when EN 18239 published' (FreeDppDppFull.cs:28) and FUNCTIONALITY.md states 'security frameworks according EN 18239 and EN 18246 to be delivered after publication of these standards'. The `dppValidate` endpoint is 'not yet comletely implemented' and references a Schemas/dpp-schema.json that is absent from the repo. No published signature, trust list, revocation, or offline-verification surface exists in the material examined.

- **open-dpp** publishes full application source (NestJS/MongoDB/S3 monorepo) but its only published passport document is the e2e fixture in `open-dpp:json` — an AAS-based format (`environment.assetAdministrationShells` / `submodels` / `conceptDescriptions`) with no EN 18223 header keys. No published passport artifact carries signatures, transparency-log commitments, or trust-list references; interop with the EN 18223 wire format requires a mapping adapter, none is published.

- **Neither vendor's published artifacts address offline verification or multi-jurisdiction portability** — no Tier-A offline pack, no QR-carried verdict, no second-jurisdiction lens. This is a statement about the published artifact surface, not about implementation intent: both projects state they target the EN 182xx series (freeDPP FUNCTIONALITY.md; open-dpp README), and EN 18239/EN 18246 — the access-rights and authentication/integrity standards — were the last two of the eight to publish.
