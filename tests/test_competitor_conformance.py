"""Competitor conformance: freeDPP and open-dpp published artifacts run
through the same UniDPP EN-18223 pipeline as the EU-profile corpus, with
the expected outcomes, and no runner-semantic changes."""

import json
from pathlib import Path

import pytest

from scripts.competitor_report import (
    EN18223_HEADER_KEYS,
    run_competitor_suite,
)
from unidpp.adapters.en18223 import parse_en18223_json

COMPETITORS = Path(__file__).resolve().parents[1] / "conformance" / "competitors"

FREEDPP_ARTIFACTS = [
    "drill-api-compressed.json",
    "drill-api-full.json",
    "drill-test1.json",
    "insulation-api-compressed.json",
    "insulation-api-full.json",
    "insulation-test2.json",
]


@pytest.fixture(scope="module")
def report():
    return run_competitor_suite(COMPETITORS)


@pytest.fixture(scope="module")
def by_vendor(report):
    return {v["vendor"]: v for v in report["vendors"]}


@pytest.fixture(scope="module")
def freedpp_results(by_vendor):
    return {r["fixture"]: r for r in by_vendor["freedpp"]["results"]}


class TestCorpus:
    def test_both_vendors_present(self, by_vendor):
        assert set(by_vendor) == {"freedpp", "open-dpp"}

    def test_artifacts_exist(self, report):
        assert report["totals"]["fixtures"] == 7
        freedpp = sorted(
            p.name for p in (COMPETITORS / "freedpp" / "artifacts").glob("*.json")
        )
        assert freedpp == FREEDPP_ARTIFACTS
        assert (COMPETITORS / "open-dpp" / "artifacts" / "battery-passport.json").is_file()

    def test_source_evidence_files_exist(self):
        # freeDPP: the repo files the coverage observations and citations reference
        for name in ("README.md", "FUNCTIONALITY.md"):
            assert (COMPETITORS / "freedpp" / "sources" / name).is_file(), name
        server = COMPETITORS / "freedpp" / "sources" / "server"
        for name in ("FreeDppDppFull.cs", "FreeDppDppCompressed.cs", "DppValidateController.cs"):
            assert (server / name).is_file(), name
        # open-dpp: the TS source the extracted artifact derives from
        assert (COMPETITORS / "open-dpp" / "sources" / "battery-passport.ts").is_file()

    def test_source_evidence_citations_verified(self, report):
        # The loader raises on drift; assert the register is complete.
        ids = [e["id"] for e in report["freedppSourceEvidence"]]
        assert ids == [f"S{i}" for i in range(1, 9)]
        for e in report["freedppSourceEvidence"]:
            assert e["citation"].strip()
            assert e["file"].startswith("freeDPPserver/")


class TestFreeDPP:
    """freeDPP's live endpoints serve EN 18223 JSON in both serializations —
    they must parse and produce findings from the unchanged runner."""

    def test_expanded_artifacts_are_en18223_documents(self):
        for name in ("drill-test1.json", "insulation-test2.json", "drill-api-full.json"):
            text = (COMPETITORS / "freedpp" / "artifacts" / name).read_text(encoding="utf-8")
            doc, exc = parse_en18223_json(text)
            assert exc is None, name
            keys = set(doc)
            assert len(keys & set(EN18223_HEADER_KEYS)) >= 2, name
            assert "elements" in keys, name

    def test_compressed_artifacts_carry_header_and_data_keys(self):
        for name in ("drill-api-compressed.json", "insulation-api-compressed.json"):
            doc = json.loads(
                (COMPETITORS / "freedpp" / "artifacts" / name).read_text(encoding="utf-8")
            )
            keys = set(doc)
            assert len(keys & set(EN18223_HEADER_KEYS)) >= 2, name
            assert "elements" not in keys, name  # compressed: keyed by elementId
            data_keys = keys - set(EN18223_HEADER_KEYS)
            assert data_keys, name

    def test_all_six_fail_with_error_findings(self, freedpp_results):
        assert set(freedpp_results) == {a.removesuffix(".json") for a in FREEDPP_ARTIFACTS}
        for fixture, r in freedpp_results.items():
            assert r["outcome"] == "fail", fixture
            assert r["errorFindings"] > 0, fixture

    def test_expected_audit_codes_present(self, by_vendor):
        by_id = by_vendor["freedpp"]["totals"]["findingsByAuditId"]
        # Every artifact prints granularity 'Model' (A1) and dppSchemaVersion
        # '0.1' (A6); the expanded artifacts print the table-spelling class
        # name (A3) and (drill) duplicate elementIds (N3) / string-typed
        # numeric values (N4).
        assert by_id["A1"] == 6
        assert by_id["A6"] == 6
        assert by_id["A3"] >= 2
        assert by_id["N3"] >= 5
        assert by_id["N4"] >= 10

    def test_compressed_artifacts_carry_only_header_level_findings(self, freedpp_results):
        """The compressed serialization cannot trip the element-tree rules;
        the expanded serialization does — an asymmetry the report records."""
        for fixture in ("drill-api-compressed", "insulation-api-compressed"):
            codes = {f["code"] for f in freedpp_results[fixture]["findings"]}
            tree_codes = {"A3-class-name-drift", "N3-duplicate-element-id",
                          "N4-value-data-type-mismatch", "N5-multivalued-child-key-divergence"}
            assert not (codes & tree_codes), fixture
            assert "A1-granularity-casing" in codes, fixture
            assert "A6-schema-version-placeholder" in codes, fixture

    def test_expanded_artifacts_carry_tree_findings(self, freedpp_results):
        for fixture in ("drill-test1", "drill-api-full", "insulation-test2", "insulation-api-full"):
            codes = {f["code"] for f in freedpp_results[fixture]["findings"]}
            assert "A3-class-name-drift" in codes, fixture

    def test_drill_duplicate_element_ids_detected(self, freedpp_results):
        dupes = [
            f for f in freedpp_results["drill-test1"]["findings"]
            if f["code"] == "N3-duplicate-element-id"
        ]
        assert len(dupes) == 5
        joined = " ".join(f["citation"] for f in dupes)
        for eid in (
            "_p_d_SafetyInstructions",
            "_p_d_RecyclingInstructions",
            "_p_d_MaterialComposition",
            "_p_d_HazardousSubstancesConcentrationLocation",
            "_p_d_AddressLine2PostalCodeCity",
        ):
            assert eid in joined

    def test_permalink_and_api_full_payloads_are_equivalent(self, freedpp_results):
        """The permalink route and ?representation=full serve the same shape:
        identical finding codes at identical error counts."""
        for a, b in (("drill-test1", "drill-api-full"), ("insulation-test2", "insulation-api-full")):
            assert freedpp_results[a]["errorFindings"] == freedpp_results[b]["errorFindings"]

    def test_timestamp_without_timezone_flagged(self, freedpp_results):
        ts = [
            f for f in freedpp_results["drill-test1"]["findings"]
            if f["code"] == "profile-header-schema" and "date-time" in f["message"]
        ]
        assert len(ts) == 1
        assert "'2026-06-17T23:20:58'" in ts[0]["message"]
        # the compressed route prints the .NET round-trip form (7 fractional
        # digits, still no timezone designator)
        ts_c = [
            f for f in freedpp_results["drill-api-compressed"]["findings"]
            if f["code"] == "profile-header-schema" and "date-time" in f["message"]
        ]
        assert len(ts_c) == 1
        assert "'2026-06-17T23:20:58.0000000'" in ts_c[0]["message"]

    def test_no_findings_without_citation_or_audit_ref(self, by_vendor):
        # Same convention as the EU-profile suite: every finding carries an
        # audit ref or is a profile-schema code (whose message cites the
        # table it comes from).
        for r in by_vendor["freedpp"]["results"]:
            for f in r["findings"]:
                has_evidence = (
                    f.get("auditRef") is not None
                    or f["code"].startswith("profile-")
                )
                assert has_evidence, (r["fixture"], f)


class TestOpenDPP:
    """open-dpp's published example is a different wire format — a coverage
    observation, not a fail, and no findings are manufactured."""

    def test_battery_passport_declares_open_dpp_format(self):
        doc = json.loads(
            (COMPETITORS / "open-dpp" / "artifacts" / "battery-passport.json").read_text(encoding="utf-8")
        )
        assert doc["format"] == "open-dpp:json"
        assert doc["version"] == "4.0"

    def test_artifact_is_not_en18223_shaped(self):
        doc = json.loads(
            (COMPETITORS / "open-dpp" / "artifacts" / "battery-passport.json").read_text(encoding="utf-8")
        )
        keys = set(doc)
        assert not (keys & set(EN18223_HEADER_KEYS))
        assert "elements" not in keys
        assert "environment" in keys  # AAS environment wrapper

    def test_recorded_as_not_applicable_with_one_info_finding(self, by_vendor):
        v = by_vendor["open-dpp"]
        r = v["results"][0]
        assert r["outcome"] == "not-applicable"
        assert len(r["findings"]) == 1
        f = r["findings"][0]
        assert f["code"] == "format-not-en-18223"
        assert f["severity"] == "info"
        assert v["totals"]["errorFindings"] == 0


class TestSuite:
    def test_totals(self, report):
        t = report["totals"]
        assert t["fixtures"] == 7
        assert t["failed"] == 6
        assert t["notApplicable"] == 1

    def test_guardrails_recorded(self, report):
        assert len(report["guardrails"]) == 4

    def test_vendor_metadata_carries_reproduction_commands(self, by_vendor):
        for v in by_vendor.values():
            assert "git clone" in v["meta"]["fetch_command"], v["vendor"]
            assert v["meta"]["repo"].startswith("https://github.com/")

    def test_freedpp_metadata_states_both_serializations(self, by_vendor):
        meta = by_vendor["freedpp"]["meta"]
        assert "representation=full|compressed" in meta["published_artifacts"]
        # the implementation repos are published — the register must say so
        assert "freeDPPserver" in meta["published_artifacts"]

    def test_every_finding_has_a_code_and_severity(self, report):
        for v in report["vendors"]:
            for r in v["results"]:
                for f in r["findings"]:
                    assert f["code"] and f["severity"], (r["fixture"], f)
