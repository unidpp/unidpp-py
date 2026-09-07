# UniDPP EU-profile conformance report — EN 18223:2026 example corpus

Generated: 2026-09-07T17:34:45Z

**Evidence annex for paper 4 (P3 deliverable).** This report records a machine-run of every example payload printed in EN 18223:2026 through the UniDPP validators, with findings cited verbatim and cross-referenced to the DPP corpus defect register (AUDIT.md).

Standard: EN 18223:2026 Digital Product Passport — System interoperability (CEN/CLC/JTC 24, final text May 2026, corrected and reissued 2 June 2026)
Source conversion: `references/internal-paid-standards/sources/en-18223-2026/sections-en`
Defect register: `the UniDPP defect register`

## 1. Method

- Corpus: **22 payloads** — clause 5.2 compressed JSON examples, Annex A expanded JSON Examples 1–6, Annex B XML Examples 1–8 — extracted verbatim into `conformance/eu-profile/fixtures/en-18223/raw/`, with typography-only corrected copies in `corrected/` (curly quotes → straight; en/em dashes → hyphens inside quoted timestamps; nothing else altered).
- Validation layers: (1) `unidpp.conformance.validate_en18223_document` (AUDIT A1–A6 rules) on the header as printed; (2) EU-profile JSON Schemas (Tables 1–6) checked with the model's own `unidpp.validate` engine on the normalized document; (3) EU-profile semantic rules encoding the EN's own normative text; (4) neutral-core identifier mapping validated with `unidpp.model.validate_identifier`; (5) the DPP temporal profile (`unidpp.temporal`) — every timestamp field against ISO 8601-1:2019 as impacted by Amd 1:2022, with precise JSONPath findings. A carrier-budget observation (`unidpp.carrier`) records each fixture's canonical serialized size against the ISO/IEC 18004 QR capacity tables (ported from the CLI): observation only, since carrier budgets bind Tier-A carrier-embedded packs, not served documents.
- Outcome semantics: pass = no error-severity finding (payload consistent with the EN's own normative text and sibling examples); info-severity findings are AUDIT vacancy references (C1, C4) and do not affect the outcome.
- Typography-correction outcome: the correction pass altered **0 of 22 payloads** — the Metanorma conversion layer already prints payload typography in ASCII form (the en-dash timestamp attested for the source PDF, AUDIT A4, appears in this conversion as ASCII hyphens; it is exercised by probe P-A4). The corrected/ mechanism remains in force: the runner regenerates and verifies every corrected copy against its raw copy on each run.
- Handling: source is an internal conversion of a purchased single-user SIST license; this report and its fixtures inherit the same constraint and must not be redistributed.

## 2. Results summary

- Fixtures run: **22**
- Pass: **14**
- Fail (findings): **8**
- Error-severity findings: **26**

| AUDIT id | Findings (fixtures + probes) |
|---|---|
| A1 | 2 |
| A2 | 2 |
| A3 | 9 |
| A4 | 1 |
| A5 | 2 |
| A6 | 2 |
| B2 | 1 |
| C1 | 2 |
| C4 | 2 |
| N1 | 1 |
| N2 | 2 |
| N3 | 1 |
| N4 | 3 |
| N5 | 1 |
| N6 | 1 |

## 3. Per-fixture results

| Fixture | Clause | Kind | Parsed | Outcome | Carrier | Findings |
|---|---|---|---|---|---|---|
| cl5-5.2.4-header | 5.2.4 | json-compressed | yes | fail | 362 B · QR v14-M | A1-granularity-casing (A1), A2-status-casing (A2), A6-schema-version-placeholder (A6), C4-content-spec-placeholder (C4) |
| cl5-5.2.5-dataelementcollection | 5.2.5 | json-compressed | yes | pass | 206 B · QR v10-M | — |
| cl5-5.2.6-singlevalued-standalone | 5.2.6 | json-compressed | yes | pass | 67 B · QR v5-M | — |
| cl5-5.2.6-singlevalued-in-complex | 5.2.6 | json-compressed | yes | pass | 102 B · QR v6-M | — |
| cl5-5.2.7-multivalued-native | 5.2.7 | json-compressed | yes | pass | 35 B · QR v3-M | — |
| cl5-5.2.7-multivalued-objects | 5.2.7 | json-compressed | yes | pass | 107 B · QR v7-M | — |
| cl5-5.2.8-relatedresource | 5.2.8 | json-compressed | yes | pass | 176 B · QR v9-M | — |
| cl5-5.2.9-multilanguage | 5.2.9 | json-compressed | yes | pass | 146 B · QR v8-M | — |
| annexA-example1 | Annex A, Example 1 | json-expanded | yes | fail | 1043 B · QR v26-M | A3-class-name-drift (A3), A3-class-name-drift (A3), A3-class-name-drift (A3), A3-class-name-drift (A3), C1-repository-placeholder (C1) |
| annexA-example2 | Annex A, Example 2 | json-expanded | no | fail | — | N1-example-not-valid-json (N1) |
| annexA-example3 | Annex A, Example 3 | json-expanded | yes | fail | 371 B · QR v15-M | A3-class-name-drift (A3), N2-dictionary-reference-malformed-uri (N2), A3-class-name-drift (A3), N2-dictionary-reference-malformed-uri (N2) |
| annexA-example4 | Annex A, Example 4 | json-expanded | yes | fail | 729 B · QR v22-M | N5-multivalued-child-key-divergence (N5), N3-duplicate-element-id (N3), A3-class-name-drift (A3), N4-value-data-type-mismatch (N4), A3-class-name-drift (A3), N4-value-data-type-mismatch (N4), A3-class-name-drift (A3), N4-value-data-type-mismatch (N4), C1-repository-placeholder (C1) |
| annexA-example5 | Annex A, Example 5 | json-expanded | no | fail | — | N6-trailing-comma (N6), A5-language-tag-structure (A5) |
| annexA-example6 | Annex A, Example 6 | json-expanded | yes | fail | 359 B · QR v14-M | A5-language-tag-unassigned (A5) |
| annexB-example1 | Annex B, Example 1 | xml | yes | fail | 385 B · QR v15-M | A1-granularity-casing (A1), A2-status-casing (A2), A6-schema-version-placeholder (A6), C4-content-spec-placeholder (C4) |
| annexB-example2 | Annex B, Example 2 | xml | yes | pass | 224 B · QR v11-M | — |
| annexB-example3 | Annex B, Example 3 | xml | yes | pass | 85 B · QR v6-M | — |
| annexB-example4 | Annex B, Example 4 | xml | yes | pass | 120 B · QR v7-M | — |
| annexB-example5 | Annex B, Example 5 | xml | yes | pass | 53 B · QR v4-M | — |
| annexB-example6 | Annex B, Example 6 | xml | yes | pass | 125 B · QR v8-M | — |
| annexB-example7 | Annex B, Example 7 | xml | yes | pass | 209 B · QR v10-M | — |
| annexB-example8 | Annex B, Example 8 | xml | yes | pass | 164 B · QR v9-M | — |

## 4. Findings detail

### cl5-5.2.4-header — 5.2.4 — fail

Source: `references/internal-paid-standards/sources/en-18223-2026/sections-en/05-technical-interoperability.adoc (payload lines 68-83)`

- `A1-granularity-casing` (error, path `$.granularity`) **[AUDIT A1]**: granularity 'Model' violates the normative lowercase enumeration ['model', 'batch', 'item'] (EN 18223 §4.1.2.2)
- `A2-status-casing` (error, path `$.dppStatus`) **[AUDIT A2]**: dppStatus 'Active' violates the lowercase enumeration ['active', 'inactive', 'archived', 'invalid'] (EN 18223 §4.1.2.1)
- `A6-schema-version-placeholder` (error, path `$.dppSchemaVersion`) **[AUDIT A6]**: dppSchemaVersion 'ENXXX:v1.0' does not match the required grammar ^EN[0-9]{3,6}:v[0-9]+\.[0-9]+(\.[0-9]+)?$ (placeholders like 'ENXXX:v1.0' or draft self-references are not versions)
- `C4-content-spec-placeholder` (info, path `$.contentSpecificationIds`) **[AUDIT C4]**: contentSpecificationIds values are placeholders (['prEN1234_xyz', 'prEN5678_abc']); identifier space, allocator and validation undefined (AUDIT C4).

  Verbatim:

  > ["prEN1234_xyz", "prEN5678_abc"]


### annexA-example1 — Annex A, Example 1 — fail

Source: `references/internal-paid-standards/sources/en-18223-2026/sections-en/aa-annex-a.adoc (payload lines 19-66)`

- `A3-class-name-drift` (error, path `$.elements[0].elements[0].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Verbatim:

  > "objectType": "SingleValuedDataElement"

- `A3-class-name-drift` (error, path `$.elements[0].elements[1].elements[0].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Verbatim:

  > "objectType": "SingleValuedDataElement"

- `A3-class-name-drift` (error, path `$.elements[0].elements[1].elements[1].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Verbatim:

  > "objectType": "SingleValuedDataElement"

- `A3-class-name-drift` (error, path `$.elements[0].elements[1].elements[2].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Verbatim:

  > "objectType": "SingleValuedDataElement"

- `C1-repository-placeholder` (info, path `$.dictionaryReference`) **[AUDIT C1]**: dictionaryReference host 'dictionary1.eu' is a placeholder; the semantic repository required by 4.3 is unspecified (AUDIT C1).

  Verbatim:

  > "dictionaryReference": "https://dictionary1.eu/maxPressure"


### annexA-example2 — Annex A, Example 2 — fail

Source: `references/internal-paid-standards/sources/en-18223-2026/sections-en/aa-annex-a.adoc (payload lines 77-95)`

- `N1-example-not-valid-json` (error, path `$`) **[AUDIT N1]**: Annex A Example 2 is not well-formed JSON as printed: the outer object opens '{' and a second object literal opens on the next line; the outer brace is never closed; 'elements' arrays contain a literal ellipsis character (U+2026) as placeholder content (finding N1). Parse error: Expecting property name enclosed in double quotes (line 2, column 5).

  Verbatim:

  > {
  >     {
  > …
  > "elements": […]


### annexA-example3 — Annex A, Example 3 — fail

Source: `references/internal-paid-standards/sources/en-18223-2026/sections-en/aa-annex-a.adoc (payload lines 108-125)`

- `A3-class-name-drift` (error, path `$.elements[0].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Verbatim:

  > "objectType": "SingleValuedDataElement"

- `N2-dictionary-reference-malformed-uri` (error, path `$.elements[0].dictionaryReference`) **[AUDIT N2]**: dictionaryReference 'https:/dictionary1/maximumPressure' omits the '//' authority separator after the scheme; Annex A Example 1 prints 'https://dictionary1.eu/maxPressure' (finding N2).

  Verbatim:

  > "dictionaryReference": "https:/dictionary1/maximumPressure"

- `A3-class-name-drift` (error, path `$.elements[1].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Verbatim:

  > "objectType": "SingleValuedDataElement"

- `N2-dictionary-reference-malformed-uri` (error, path `$.elements[1].dictionaryReference`) **[AUDIT N2]**: dictionaryReference 'https:/dictionary1/recycledContentPercentage' omits the '//' authority separator after the scheme; Annex A Example 1 prints 'https://dictionary1.eu/maxPressure' (finding N2).

  Verbatim:

  > "dictionaryReference": "https:/dictionary1/recycledContentPercentage"


### annexA-example4 — Annex A, Example 4 — fail

Source: `references/internal-paid-standards/sources/en-18223-2026/sections-en/aa-annex-a.adoc (payload lines 138-170)`

- `N5-multivalued-child-key-divergence` (error, path `$.elements[0].value`) **[AUDIT N5]**: MultiValuedDataElement children serialized under 'value'; Annex A Example 1 serializes the same class's children under 'elements'; Table 4 (4.1.2.6) models them as '[DataElement]' entries (finding N5).

  Verbatim:

  > "value": [ { "elementId": "efficiencyRating1", … } ]

- `N3-duplicate-element-id` (error, path `$.elements[0].value[2].elementId`) **[AUDIT N3]**: elementId 'efficiencyRating2' is used by two siblings (value[1] and value[2]); Table 2 (4.1.2.3): 'The relative identifier of the DataElement shall be unique within its location (i.e. in the DataElementCollection or MultiValuedDataElement)' (finding N3).

  Verbatim:

  > "elementId": "efficiencyRating2"

- `A3-class-name-drift` (error, path `$.elements[0].value[0].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Verbatim:

  > "objectType": "SingleValuedDataElement"

- `N4-value-data-type-mismatch` (error, path `$.elements[0].value[0].value`) **[AUDIT N4]**: valueDataType 'xsd:float' with value serialized as a JSON string '0.95'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Verbatim:

  > "value": "0.95"

- `A3-class-name-drift` (error, path `$.elements[0].value[1].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Verbatim:

  > "objectType": "SingleValuedDataElement"

- `N4-value-data-type-mismatch` (error, path `$.elements[0].value[1].value`) **[AUDIT N4]**: valueDataType 'xsd:float' with value serialized as a JSON string '0.92'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Verbatim:

  > "value": "0.92"

- `A3-class-name-drift` (error, path `$.elements[0].value[2].objectType`) **[AUDIT A3]**: objectType 'SingleValuedDataElement' is the table/example spelling; the 4.1.2.1 prose spelling is 'SingleValueDataElement' (AUDIT A3, marked verify). EN 18223 5.2.6: '*SingleValuedDataElements* (4.1.2.5) are serialized as JSON «key-value pair». In case the *SingleValueDataElements* is contained in *MultiValueDataElement*, the key-value pair may be simplified to a value of a native data type.' — both spellings in one sentence; 4.1.2.1 prose prints 'SingleValueDataElement'.

  Verbatim:

  > "objectType": "SingleValuedDataElement"

- `N4-value-data-type-mismatch` (error, path `$.elements[0].value[2].value`) **[AUDIT N4]**: valueDataType 'xsd:float' with value serialized as a JSON string '0.88'; Table 7 (5.2.3) maps xsd:float to 'A JSON Number'; the compressed form of the same data (5.2.5) prints JSON numbers (finding N4).

  Verbatim:

  > "value": "0.88"

- `C1-repository-placeholder` (info, path `$.dictionaryReference`) **[AUDIT C1]**: dictionaryReference host 'dictionary1.eu' is a placeholder; the semantic repository required by 4.3 is unspecified (AUDIT C1).

  Verbatim:

  > "dictionaryReference": "https://dictionary1.eu/maxPressure"


### annexA-example5 — Annex A, Example 5 — fail

Source: `references/internal-paid-standards/sources/en-18223-2026/sections-en/aa-annex-a.adoc (payload lines 183-195)`

- `N6-trailing-comma` (error, path `$`) **[AUDIT N6]**: Annex A Example 5 is not well-formed JSON: trailing comma after the final member (finding N6). Parse error: Expecting property name enclosed in double quotes (line 11, column 5).

  Verbatim:

  >       "contentType": "application/pdf",
  >       "url": "https://data.example.com/manuals/thermostat-pro_v2.1.pdf",

- `A5-language-tag-structure` (error, path `$.language`) **[AUDIT A5]**: language tag 'en' is a bare two-letter primary subtag; Table 5 (4.1.2.7) / Table 6 (4.1.2.8.2) specify 'two (2) characters language code as in ISO 639:2023 … and two (2) characters country code as in EN ISO 3166-1:2020' (example 'en-GB') (AUDIT A5).

  Verbatim:

  > "language": "en"


### annexA-example6 — Annex A, Example 6 — fail

Source: `references/internal-paid-standards/sources/en-18223-2026/sections-en/aa-annex-a.adoc (payload lines 208-230)`

- `A5-language-tag-unassigned` (error, path `$.elements[0].value[1].language`) **[AUDIT A5]**: language tag 'gr': primary subtag 'gr' is not an assigned ISO 639-1 code (Greek is 'el', not 'gr') (AUDIT A5).

  Verbatim:

  > "language": "gr"


### annexB-example1 — Annex B, Example 1 — fail

Source: `references/internal-paid-standards/sources/en-18223-2026/sections-en/ab-annex-b.adoc (payload lines 15-34)`

- `A1-granularity-casing` (error, path `$.granularity`) **[AUDIT A1]**: granularity 'Model' violates the normative lowercase enumeration ['model', 'batch', 'item'] (EN 18223 §4.1.2.2)
- `A2-status-casing` (error, path `$.dppStatus`) **[AUDIT A2]**: dppStatus 'Active' violates the lowercase enumeration ['active', 'inactive', 'archived', 'invalid'] (EN 18223 §4.1.2.1)
- `A6-schema-version-placeholder` (error, path `$.dppSchemaVersion`) **[AUDIT A6]**: dppSchemaVersion 'prEN18223:v1.0' does not match the required grammar ^EN[0-9]{3,6}:v[0-9]+\.[0-9]+(\.[0-9]+)?$ (placeholders like 'ENXXX:v1.0' or draft self-references are not versions)
- `C4-content-spec-placeholder` (info, path `$.contentSpecificationIds`) **[AUDIT C4]**: contentSpecificationIds values are placeholders (['prEN1234_xyz', 'prEN5678_abc']); identifier space, allocator and validation undefined (AUDIT C4).

  Verbatim:

  > ["prEN1234_xyz", "prEN5678_abc"]


## 5. New findings register (N1–N6)

Defects discovered by this run that the AUDIT.md register does not yet record. Each is a cited fact from the EN's own text.

### N1 — `N1-example-not-valid-json`

- Clause: Annex A, Example 2
- Defect: misnested/unclosed braces and literal ellipsis array placeholders
- Class: internal inconsistency
- Normative rule violated: 5.2.1 ('The serialization of data with standardized data structures shall follow the model provided in Clause 4'); ISO/IEC 21778 syntax
- Verbatim citation:

  ```
  {
      {
        "elementId": "collectionEconomicOperator",
        "objectType": "DataElementCollection",
        "dictionaryReference": "https://organizationDictionary.eu/organization",
        "elements": […]
      },
  …
      }
  (the outer '{' opens a second '{' object literal as its first member and is never closed)
  ```

### N2 — `N2-dictionary-reference-malformed-uri`

- Clause: Annex A, Example 3
- Defect: dictionaryReference URLs omit the '//' authority separator after the scheme
- Class: internal inconsistency
- Normative rule violated: Table 2 (4.1.2.3): dictionaryReference is 'The reference to the unique identifier of the data point specification defined in the repository/data dictionary'; RFC 3986 authority component
- Verbatim citation:

  ```
  "dictionaryReference": "https:/dictionary1/maximumPressure",
  "dictionaryReference": "https:/dictionary1/recycledContentPercentage",
  (sibling Annex A Example 1 prints "https://dictionary1.eu/maxPressure")
  ```

### N3 — `N3-duplicate-element-id`

- Clause: Annex A, Example 4
- Defect: elementId 'efficiencyRating2' used by two siblings (the idShort-equivalent key is not unique within its location)
- Class: internal inconsistency
- Normative rule violated: Table 2 (4.1.2.3): 'The relative identifier of the DataElement shall be unique within its location (i.e. in the DataElementCollection or MultiValuedDataElement)'
- Verbatim citation:

  ```
  "elementId": "efficiencyRating1", … "value": "0.95"
  "elementId": "efficiencyRating2", … "value": "0.92"
  "elementId": "efficiencyRating2", … "value": "0.88"
  (third child reuses the second child's elementId)
  ```

### N4 — `N4-value-data-type-mismatch`

- Clause: Annex A, Example 4
- Defect: values serialized as JSON strings while valueDataType declares xsd:float; the compressed form of the same data prints JSON numbers
- Class: internal inconsistency
- Normative rule violated: Table 7 (5.2.3): 'xsd:double, xsd:float | Number | A JSON Number.'
- Verbatim citation:

  ```
  "valueDataType": "xsd:float",
  "value": "0.95"
  (clause 5.2.5 compressed form of the same values: 0.95, 0.92, 0.88 as JSON numbers)
  ```

### N5 — `N5-multivalued-child-key-divergence`

- Clause: Annex A, Example 4 vs Example 1
- Defect: two structurally different expanded serializations of one class: MultiValuedDataElement children under 'value' (Example 4) vs under 'elements' (Example 1)
- Class: internal inconsistency
- Normative rule violated: Table 4 (4.1.2.6) models the children as '[DataElement]' entries, not as 'value' (which Table 3 (4.1.2.5) defines as the SingleValuedDataElement value slot)
- Verbatim citation:

  ```
  Example 4: "objectType": "MultiValuedDataElement", … "value": [ { "elementId": "efficiencyRating1", … } ]
  Example 1: "objectType": "MultiValuedDataElement", … "elements": [ { "elementId": "efficiencyRating1", … } ]
  ```

### N6 — `N6-trailing-comma`

- Clause: Annex A, Example 5
- Defect: trailing comma after the final member makes the object invalid JSON
- Class: internal inconsistency
- Normative rule violated: ISO/IEC 21778 (JSON) syntax
- Verbatim citation:

  ```
  "contentType": "application/pdf",
  "url": "https://data.example.com/manuals/thermostat-pro_v2.1.pdf",
      }
  ```

## 6. Probes

AUDIT-attested forms exercised directly. The Metanorma conversion layer prints the Annex B Ex.1 timestamp with ASCII hyphens, so the A4 en-dash form attested for the source PDF is verified by probe.

### P-A4 — AUDIT A4 — Annex B Ex.1 en-dash timestamp form (source PDF)

- Input: `{"lastUpdated": "2025–08–22T03:12:00Z"}`
- Rejected: yes — codes: A4-timestamp-not-iso8601

> AUDIT.md A4: 'lastUpdated printed as 2025–08–22T03:12:00Z — en-dashes, i.e. an invalid ISO 8601 timestamp in the very example that teaches the format; the same doc normatively cites ISO 8601-1'. The Metanorma conversion used for this extraction prints the fixture with ASCII hyphens (2025-08-22T03:12:00Z), so the A4 form is exercised here as a probe on the attested PDF spelling.

### P-B2 — AUDIT B2 — IDTA 02099-1 'lastUpdate' drift spelling

- Input: `{"lastUpdate": "2025-08-22T03:12:00Z"}`
- Rejected: yes — codes: A0-key-casing-drift

> AUDIT.md B2: 'Attribute lastUpdated (EN) vs lastUpdate (IDTA's implementation of the EN); casing drift throughout (Model/Item/Active vs model/item/active)'. Exercises the PA2 mapping's drift detection.

## 7. Profile adaptations

Each divergence between the EU compressed/expanded forms and the neutral core, handled by `unidpp/adapters/en18223.py`.

- **PA1 — JSON line-comment stripping**: ISO/IEC 21778 (JSON) defines no comments, but the clause 5.2 compressed examples print '//***DPP HEADER***', '// optional', type annotations and '// … rest of the DPP data' inside the payload. The adapter strips '//' line comments (string-literal aware) before parsing.
- **PA2 — lastUpdate ↔ lastUpdated key mapping** (AUDIT B2): EN 18223 Table 1 (4.1.2.1) names the attribute 'lastUpdated'; IDTA 02099-1 (the EN's implementation) prints 'lastUpdate'. The adapter accepts both spellings and maps the drift form onto the normative 'lastUpdated'; when the drift form appears it is reported (code A0-key-casing-drift).
- **PA3 — granularity / dppStatus value-case normalization** (AUDIT A1, A2): The adapter normalizes 'Model' → 'model' (4.1.2.2 enumeration) and 'Active' → 'active' (4.1.2.1 example values) before enum/schema checks; the casing exactly as printed is retained and reported separately (A1 / A2).
- **PA4 — compressed → expanded promotion** (AUDIT C7): The compressed form (5.2) keys data by elementId with metadata omitted; the expanded form (Annex A) carries elementId / objectType / dictionaryReference / valueDataType / value. The adapter promotes compressed payloads: elementId from the JSON key, objectType inferred from the value shape per the 4.1.2 class definitions. EN 18223 specifies the two serializations by example only and defines no transformation algorithm (AUDIT C7).
- **PA5 — positional elementId synthesis for anonymous array items** (AUDIT C7): 5.2.7: 'When a data element is an item in a JSON array … it does not have an explicit key. It is identified by its position (or index) within the array.' Promotion synthesizes '<parent>[i]' elementIds for anonymous items; the EN defines no expanded counterpart for them.
- **PA6 — MultiValuedDataElement child-key tolerance**: Annex A Example 1 nests the children of a MultiValuedDataElement under 'elements' while Annex A Example 4 nests them under 'value'. The element-tree schema accepts both keys; the divergence itself is reported as finding N5.
- **PA7 — XML projection (comment removal + Table 7 inverse typing)**: Annex B XML examples carry '<!-- Begin DPP Header Elements -->' comments (dropped) and untyped text nodes. Scalar text is typed by the inverse of Table 7 (5.2.3): 'true'/'false' → boolean, numeric literals → number, otherwise string.
- **PA8 — fragment tolerance**: The 5.2 data-element examples are fragments ('//...DPP HEADER...' placeholder, no surrounding document); they omit elementId context by construction. Required-elementId checks are disabled for fragment fixtures.
- **PA9 — URI identifiers → neutral-core ProductIdentifier**: uniqueProductIdentifier (URI-formatted per EN 18219:2026) maps to ProductIdentifier(scheme='uri', state='live') — the wire schema's registry extension point — with granularity normalized per PA3 (EN 18223 model/batch/item ⊂ neutral core model/type/batch/lot/item). The result is validated with unidpp.model.validate_identifier.
