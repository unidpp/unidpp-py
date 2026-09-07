"""EU-profile conformance: EN 18223:2026 example corpus runs through the
UniDPP validators with the expected outcomes, findings and adaptations."""

import json
from pathlib import Path

import pytest

from unidpp.adapters.en18223 import (
    NEW_FINDINGS_REGISTER,
    PROFILE_ADAPTATIONS,
    correct_typography,
    parse_en18223_json,
    project_xml,
    promote_compressed,
    run_eu_profile_suite,
    strip_json_comments,
    validate_profile_fixture,
)

FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "conformance"
    / "eu-profile"
    / "fixtures"
    / "en-18223"
)


@pytest.fixture(scope="module")
def index():
    return json.loads((FIXTURES / "INDEX.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def results(index):
    out = {}
    for entry in index["fixtures"]:
        raw = (FIXTURES / "raw" / entry["file"]).read_text(encoding="utf-8")
        corrected = (FIXTURES / "corrected" / entry["file"]).read_text(encoding="utf-8")
        out[entry["id"]] = validate_profile_fixture(entry, raw, corrected)
    return out


@pytest.fixture(scope="module")
def report():
    return run_eu_profile_suite(FIXTURES)


class TestCorpus:
    def test_every_example_payload_is_extracted(self, index):
        assert len(index["fixtures"]) == 22
        kinds = [e["kind"] for e in index["fixtures"]]
        assert kinds.count("json-compressed") == 8
        assert kinds.count("json-expanded") == 6
        assert kinds.count("xml") == 8

    def test_raw_fixtures_are_verbatim_substrings_of_the_adoc_sources(self, index):
        adoc_root = Path(index["sourceRoot"])
        for entry in index["fixtures"]:
            src = (adoc_root / entry["source"]).read_text(encoding="utf-8")
            raw = (FIXTURES / "raw" / entry["file"]).read_text(encoding="utf-8")
            assert raw in src, entry["file"]

    def test_corrected_copies_are_the_typography_only_correction_of_raw(self, index):
        for entry in index["fixtures"]:
            raw = (FIXTURES / "raw" / entry["file"]).read_text(encoding="utf-8")
            corrected = (FIXTURES / "corrected" / entry["file"]).read_text(encoding="utf-8")
            assert corrected == correct_typography(raw), entry["file"]


class TestTypographyCorrection:
    def test_curly_quotes_normalized(self):
        assert correct_typography("“a ‘b’ c”") == '"a \'b\' c"'

    def test_en_dash_in_timestamp_normalized(self):
        assert (
            correct_typography('"lastUpdated": "2025–08–22T03:12:00Z"')
            == '"lastUpdated": "2025-08-22T03:12:00Z"'
        )

    def test_en_dash_outside_timestamps_untouched(self):
        assert correct_typography("a–b—c") == "a–b—c"


class TestParsing:
    def test_json_comments_stripped_but_strings_preserved(self):
        stripped = strip_json_comments('{\n // note\n "a": "https://x//y"\n}')
        doc, exc = parse_en18223_json('{\n // note\n "a": "https://x//y"\n}')
        assert exc is None
        assert doc == {"a": "https://x//y"}
        assert "// note" not in stripped

    def test_clause_5_header_parses_after_comment_stripping(self):
        text = (FIXTURES / "raw" / "cl5-5.2.4-header.json").read_text(encoding="utf-8")
        doc, exc = parse_en18223_json(text)
        assert exc is None
        assert doc["granularity"] == "Model"

    def test_annex_a_example_2_is_not_valid_json(self):
        text = (FIXTURES / "raw" / "annexA-example2.json").read_text(encoding="utf-8")
        doc, exc = parse_en18223_json(text)
        assert doc is None and exc is not None

    def test_annex_a_example_5_is_not_valid_json(self):
        text = (FIXTURES / "raw" / "annexA-example5.json").read_text(encoding="utf-8")
        doc, exc = parse_en18223_json(text)
        assert doc is None and exc is not None

    def test_xml_examples_project(self):
        text = (FIXTURES / "raw" / "annexB-example1.xml").read_text(encoding="utf-8")
        doc, exc = project_xml(text)
        assert exc is None
        assert doc["granularity"] == "Model"
        assert doc["dppSchemaVersion"] == "prEN18223:v1.0"
        assert doc["contentSpecificationIds"] == ["prEN1234_xyz", "prEN5678_abc"]
        assert doc["_dataElements"] == {}

    def test_xml_scalar_typing_follows_table_7_inverse(self):
        doc, _ = project_xml(
            "<r xmlns:d='urn:d'><d:a>true</d:a><d:b>25.5</d:b><d:c>x</d:c></r>"
        )
        # non-dpp children land in the data elements, typed per Table 7
        assert doc["_dataElements"] == {"a": True, "b": 25.5, "c": "x"}


class TestPromotion:
    def test_compressed_collection_promotes_to_expanded_tree(self):
        tree = promote_compressed(
            {
                "performanceMetrics": {
                    "maxPressure": 750.0,
                    "efficiencyRatings": [0.95, 0.92, 0.88],
                }
            },
            fragment=True,
        )
        perf = tree["elements"][0]
        assert perf["objectType"] == "DataElementCollection"
        kinds = {c["objectType"] for c in perf["elements"]}
        assert kinds == {"SingleValueDataElement", "MultiValuedDataElement"}
        # PA5: anonymous array items get positional elementIds
        ratings = next(c for c in perf["elements"] if c["objectType"] == "MultiValuedDataElement")
        assert ratings["value"] == [0.95, 0.92, 0.88]

    def test_compressed_related_resource_promotes(self):
        tree = promote_compressed(
            {"resourceTitle": "T", "contentType": "application/pdf", "url": "https://x", "language": "en-GB"},
            fragment=True,
        )
        assert tree["elements"][0]["objectType"] == "RelatedResource"

    def test_promotion_uses_the_prose_canonical_spelling(self):
        tree = promote_compressed({"a": 1}, fragment=True)
        assert tree["elements"][0]["objectType"] == "SingleValueDataElement"


class TestOutcomes:
    def test_self_consistent_examples_pass(self, results):
        for fid in (
            "cl5-5.2.5-dataelementcollection",
            "cl5-5.2.6-singlevalued-standalone",
            "cl5-5.2.6-singlevalued-in-complex",
            "cl5-5.2.7-multivalued-native",
            "cl5-5.2.7-multivalued-objects",
            "cl5-5.2.8-relatedresource",
            "cl5-5.2.9-multilanguage",
        ):
            assert results[fid].outcome == "pass", fid
            assert results[fid].findings == [], fid

    def test_annex_b_data_examples_pass(self, results):
        for n in range(2, 9):
            fid = f"annexB-example{n}"
            assert results[fid].outcome == "pass", fid

    def test_header_examples_fail_with_audit_casing_and_version_findings(self, results):
        for fid in ("cl5-5.2.4-header", "annexB-example1"):
            codes = {f.code for f in results[fid].findings}
            assert {
                "A1-granularity-casing",
                "A2-status-casing",
                "A6-schema-version-placeholder",
            } <= codes, fid

    def test_annex_a_all_examples_carry_findings(self, results):
        for n in range(1, 7):
            fid = f"annexA-example{n}"
            assert results[fid].outcome == "fail", fid

    def test_duplicate_element_id_detected_in_annex_a_example_4(self, results):
        codes = [f.code for f in results["annexA-example4"].findings]
        assert codes.count("N3-duplicate-element-id") == 1
        dup = next(f for f in results["annexA-example4"].findings if f.code == "N3-duplicate-element-id")
        assert "efficiencyRating2" in dup.message
        assert "4.1.2.3" in dup.message

    def test_value_type_mismatch_detected_three_times(self, results):
        codes = [f.code for f in results["annexA-example4"].findings]
        assert codes.count("N4-value-data-type-mismatch") == 3

    def test_child_key_divergence_detected(self, results):
        codes = {f.code for f in results["annexA-example4"].findings}
        assert "N5-multivalued-child-key-divergence" in codes

    def test_malformed_json_classified(self, results):
        assert {f.code for f in results["annexA-example2"].findings} == {
            "N1-example-not-valid-json"
        }
        codes = {f.code for f in results["annexA-example5"].findings}
        assert "N6-trailing-comma" in codes
        assert "A5-language-tag-structure" in codes  # bare "en" via textual scan

    def test_malformed_uri_detected_in_annex_a_example_3(self, results):
        codes = [f.code for f in results["annexA-example3"].findings]
        assert codes.count("N2-dictionary-reference-malformed-uri") == 2

    def test_gr_language_tag_detected(self, results):
        f = next(
            f
            for f in results["annexA-example6"].findings
            if f.code == "A5-language-tag-unassigned"
        )
        assert "'gr'" in f.message and "el" in f.message

    def test_a3_drift_only_where_the_en_prints_the_table_spelling(self, results):
        for fid in ("cl5-5.2.5-dataelementcollection", "annexB-example2"):
            assert not any(
                f.code == "A3-class-name-drift" for f in results[fid].findings
            ), fid
        for n in (1, 3, 4):
            fid = f"annexA-example{n}"
            assert any(f.code == "A3-class-name-drift" for f in results[fid].findings), fid

    def test_info_severity_vacancy_references_do_not_fail_a_fixture(self, results):
        fid = "annexA-example1"
        assert results[fid].outcome == "fail"  # A3 errors
        assert any(f.severity == "info" and f.audit_ref == "C1" for f in results[fid].findings)


class TestSuite:
    def test_totals(self, report):
        t = report["totals"]
        assert t["fixtures"] == 22
        assert t["passed"] == 14
        assert t["failed"] == 8

    def test_findings_by_audit_id(self, report):
        by_id = report["totals"]["findingsByAuditId"]
        assert by_id["A1"] == 2
        assert by_id["A2"] == 2
        assert by_id["A3"] == 9
        assert by_id["A5"] == 2
        assert by_id["A6"] == 2
        assert by_id["A4"] == 1  # probe P-A4
        assert by_id["B2"] == 1  # probe P-B2

    def test_probes_reject_the_attested_forms(self, report):
        probes = {p["id"]: p for p in report["probes"]}
        assert probes["P-A4"]["rejected"]
        assert "A4-timestamp-not-iso8601" in probes["P-A4"]["codes"]
        assert probes["P-B2"]["rejected"]
        assert "A0-key-casing-drift" in probes["P-B2"]["codes"]

    def test_every_finding_carries_an_audit_ref_or_is_a_profile_schema_code(self, report):
        for r in report["results"]:
            for f in r["findings"]:
                assert f["auditRef"] is not None or f["code"].startswith("profile-"), (
                    r["fixture"],
                    f,
                )

    def test_new_findings_have_verbatim_citations(self):
        for n in NEW_FINDINGS_REGISTER:
            assert n["citation"].strip()
            assert n["id"].startswith("N")
            assert n["rule"]

    def test_adaptations_are_documented(self):
        ids = [pa["id"] for pa in PROFILE_ADAPTATIONS]
        assert ids == [f"PA{i}" for i in range(1, 10)]

    def test_fixture_integrity_is_enforced(self, tmp_path):
        # a corrected copy that is not the typography-only correction of raw
        # is a harness error
        root = tmp_path / "fx"
        (root / "raw").mkdir(parents=True)
        (root / "corrected").mkdir(parents=True)
        (root / "INDEX.json").write_text(
            json.dumps(
                {
                    "fixtures": [
                        {
                            "id": "x",
                            "file": "x.json",
                            "kind": "json-compressed",
                            "clause": "c",
                            "title": "t",
                            "source": "s.adoc",
                            "lines": "1-2",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (root / "raw" / "x.json").write_text('{"a": "b"}', encoding="utf-8")
        (root / "corrected" / "x.json").write_text('{"a": "c"}', encoding="utf-8")
        with pytest.raises(ValueError):
            run_eu_profile_suite(root)
