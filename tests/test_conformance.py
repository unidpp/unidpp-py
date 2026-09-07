"""Conformance suite: positive corpus passes, AUDIT A1-A6 negative
fixtures fail with precise findings, reports are written."""

import json

from unidpp.conformance import (
    CHECK_REGISTRY,
    negative_fixtures_a1_a6,
    run_conformance,
    validate_en18223_document,
    write_json_report,
    write_markdown_report,
)


class TestNegativeCorpus:
    def test_every_audit_fixture_fails_with_expected_code(self):
        by_code = {
            (fx["fixture"], fx["expectCode"]): validate_en18223_document(fx["document"])
            for fx in negative_fixtures_a1_a6()
        }
        for (name, expected), issues in by_code.items():
            assert issues, f"{name} produced no findings"
            assert any(i.keyword == expected for i in issues), (
                f"{name}: expected {expected}, got {[i.keyword for i in issues]}"
            )

    def test_a1_granularity_model_casing(self):
        issues = validate_en18223_document({"granularity": "Model"})
        assert any(i.keyword == "A1-granularity-casing" for i in issues)
        assert "§4.1.2.2" in issues[0].message

    def test_a2_dpp_status_active_casing(self):
        issues = validate_en18223_document({"dppStatus": "Active"})
        assert any(i.keyword == "A2-status-casing" for i in issues)

    def test_a3_class_name_drift(self):
        issues = validate_en18223_document(
            {"dataElements": [{"class": "SingleValuedDataElement"}]}
        )
        assert any(i.keyword == "A3-class-name-drift" for i in issues)
        # The prose spelling is accepted.
        assert not validate_en18223_document(
            {"dataElements": [{"class": "SingleValueDataElement"}]}
        )

    def test_a4_en_dash_timestamp(self):
        issues = validate_en18223_document({"lastUpdated": "2025–08–22T03:12:00Z"})
        assert any(i.keyword == "A4-timestamp-not-iso8601" for i in issues)
        assert "en/em dashes" in issues[0].message
        # The corrected ASCII form passes.
        assert not validate_en18223_document({"lastUpdated": "2025-08-22T03:12:00Z"})

    def test_a5_gr_language_tag(self):
        issues = validate_en18223_document({"language": "gr"})
        assert any(i.keyword == "A5-language-tag-unassigned" for i in issues)
        assert "el" in issues[0].message
        assert not validate_en18223_document({"language": "el"})
        assert not validate_en18223_document({"language": "zh-Hans"})

    def test_a6_placeholder_schema_version(self):
        for bad in ("ENXXX:v1.0", "prEN18223:v1.0"):
            issues = validate_en18223_document({"dppSchemaVersion": bad})
            assert any(i.keyword == "A6-schema-version-placeholder" for i in issues), bad
        assert not validate_en18223_document({"dppSchemaVersion": "EN18223:v1.0"})

    def test_key_casing_drift_lastupdate(self):
        issues = validate_en18223_document({"lastUpdate": "2025-08-22T03:12:00Z"})
        assert any(i.keyword == "A0-key-casing-drift" for i in issues)

    def test_clean_document_produces_no_findings(self):
        assert validate_en18223_document(
            {
                "granularity": "item",
                "dppStatus": "active",
                "lastUpdated": "2025-08-22T03:12:00Z",
                "language": "el",
                "dppSchemaVersion": "EN18223:v1.0",
                "dataElements": [{"class": "SingleValueDataElement"}],
            }
        ) == []


class TestRunner:
    def test_registry_has_the_four_checks(self):
        assert set(CHECK_REGISTRY) == {
            "positive-corpus",
            "audit-negative",
            "temporal-conformance",
            "carrier-budget",
        }

    def test_run_conformance_all_pass(self):
        report = run_conformance()
        assert report["failed"] == 0
        assert report["passed"] == report["total"]
        # 3 positive + 7 negative (A1-A6 + key-drift) + 2 carrier fixtures
        assert report["total"] == 12

    def test_negative_results_carry_expected_code(self):
        report = run_conformance()
        negatives = [r for r in report["results"] if r["kind"] == "negative"]
        assert len(negatives) == 7
        for r in negatives:
            assert r["outcome"] == "pass"  # the fixture *tripped as designed*
            codes = [f["code"] for f in r["findings"]]
            assert r["expectedCode"] in codes

    def test_reports_written(self, tmp_path):
        report = run_conformance()
        jp = write_json_report(report, tmp_path / "r" / "conformance-report.json")
        mp = write_markdown_report(report, tmp_path / "r" / "conformance-report.md")
        loaded = json.loads(jp.read_text(encoding="utf-8"))
        assert loaded["passed"] == report["passed"]
        md = mp.read_text(encoding="utf-8")
        assert "AUDIT-A1" in md and "A1-granularity-casing" in md
        assert "| AUDIT-A4 | negative | pass |" in md
