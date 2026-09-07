"""Carrier conformance: ISO/IEC 18004 QR capacity tables ported from the
CLI, the budget grammar, canonical serialized sizes, and the carrier
fixtures — a payload known to fit QR v15-M passes; an oversized payload
is flagged with the computed size versus the capacity; the reports carry
the carrier column."""

from pathlib import Path

import pytest

from unidpp import carrier
from unidpp.carrier import (
    CarrierBudgetError,
    byte_capacity,
    check_payload,
    measure,
    min_version_for,
    parse_budget,
    render,
    serialized_size,
)
from unidpp.conformance import CHECK_REGISTRY, carrier_fixtures, run_conformance

COMPETITORS = Path(__file__).resolve().parents[1] / "conformance" / "competitors"
EU_FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "conformance"
    / "eu-profile"
    / "fixtures"
    / "en-18223"
)


class TestPortedCapacityTables:
    def test_known_capacities_match_the_cli_tables(self):
        # Spot values from unidpp-core/crates/tier_a/src/qr.rs tests.
        assert byte_capacity(1, "L") == 17
        assert byte_capacity(1, "H") == 7
        assert byte_capacity(10, "M") == 213
        assert byte_capacity(40, "L") == 2953
        assert byte_capacity(40, "M") == 2331
        assert byte_capacity(40, "H") == 1273

    def test_the_en18220_class_span_is_covered(self):
        # v10-M floor through v40-H ceiling (the plan's EN 18220 span).
        lo, hi = carrier.EN18220_QR_CLASS_SPAN
        assert byte_capacity(10, "M") == 213
        assert byte_capacity(40, "H") == 1273
        assert parse_budget(lo) == ("M", 10)
        assert parse_budget(hi) == ("H", 40)
        assert len(carrier.QR_BYTE_CAPACITY["M"]) == 40

    def test_out_of_range_arguments_raise(self):
        with pytest.raises(CarrierBudgetError):
            byte_capacity(0, "M")
        with pytest.raises(CarrierBudgetError):
            byte_capacity(41, "M")
        with pytest.raises(CarrierBudgetError):
            byte_capacity(15, "X")

    def test_min_version_for(self):
        assert min_version_for(17, "L") == 1
        assert min_version_for(18, "L") == 2
        assert min_version_for(412, "M") == 15  # v15-M holds 412
        assert min_version_for(413, "M") == 16
        assert min_version_for(2953, "L") == 40
        assert min_version_for(2954, "L") is None


class TestBudgetGrammar:
    def test_valid_tokens_parse_case_insensitively(self):
        assert parse_budget("qr-v15-M") == ("M", 15)
        assert parse_budget("QR-V3-h") == ("H", 3)
        assert parse_budget(" qr-v40-m ") == ("M", 40)

    def test_invalid_tokens_rejected(self):
        for bad in ("qr-v0-M", "qr-v41-M", "qr-v15-X", "qr-vX-M", "qr-v15", "v15-M"):
            with pytest.raises(CarrierBudgetError):
                parse_budget(bad)


class TestSerializedSize:
    def test_canonical_size_is_the_compact_form(self):
        assert serialized_size({"a": 1}) == len(b'{"a":1}')
        assert serialized_size({"b": 2, "a": 1}) == len(b'{"a":1,"b":2}')

    def test_model_objects_are_measured_in_wire_form(self):
        from unidpp.model import ProductIdentifier

        pid = ProductIdentifier("ma", "MA.1", "item", "live")
        assert serialized_size(pid) == serialized_size(pid.to_dict())


class TestCheckPayload:
    def test_fixture_known_to_fit_qr_v15_m_passes(self):
        fixtures = {f.name: f for f in carrier_fixtures()}
        fits = fixtures["dpp-fits-qr-v15-m"]
        findings = check_payload(fits.data["payload"], fits.data["declaredCarrier"])
        assert findings == []
        m = measure(fits.data["payload"], declared=fits.data["declaredCarrier"])
        assert m.fits_declared is True
        assert 363 <= m.size_bytes <= 412  # inside the v15-M band, beyond v14-M
        assert m.min_qr_by_ec["M"] == 15

    def test_oversized_payload_flagged_with_size_versus_capacity(self):
        fixtures = {f.name: f for f in carrier_fixtures()}
        over = fixtures["dpp-over-qr-v15-m"]
        findings = check_payload(over.data["payload"], over.data["declaredCarrier"])
        assert [f.code for f in findings] == ["C1-carrier-over-budget"]
        message = findings[0].message
        assert f"{serialized_size(over.data['payload'])} bytes" in message
        assert "holds 412 bytes" in message
        assert "never truncate" in message

    def test_malformed_budget_token_flagged(self):
        findings = check_payload({"a": 1}, "qr-v15-X")
        assert [f.code for f in findings] == ["C2-carrier-budget-malformed"]

    def test_undeclared_payload_produces_no_findings(self):
        # Without a declared class the check measures only — never flags.
        assert CHECK_REGISTRY["carrier-budget"].fn({"payload": {"a": "x" * 5000}}) == []


class TestRunnerIntegration:
    def test_check_registered_in_the_registry(self):
        assert "carrier-budget" in CHECK_REGISTRY
        assert "ISO/IEC 18004" in CHECK_REGISTRY["carrier-budget"].title

    def test_runner_carrier_fixtures_run_and_pass(self):
        report = run_conformance()
        carrier_results = [r for r in report["results"] if r["kind"] == "carrier"]
        assert [r["fixture"] for r in carrier_results] == [
            "dpp-fits-qr-v15-m",
            "dpp-over-qr-v15-m",
        ]
        assert all(r["outcome"] == "pass" for r in carrier_results)
        fits, over = (r["carrier"] for r in carrier_results)
        assert fits["declared"] == "qr-v15-M" and fits["fitsDeclared"] is True
        assert over["declared"] == "qr-v15-M" and over["fitsDeclared"] is False
        assert over["declaredCapacity"] == 412

    def test_report_shows_the_carrier_column(self, tmp_path):
        import unidpp.conformance as C

        report = run_conformance()
        md = C.write_markdown_report(report, tmp_path / "r.md").read_text()
        assert "| Fixture | Kind | Outcome | Temporal | Carrier |" in md
        assert "406 B vs 412 B · qr-v15-M (fits)" in md
        assert "(OVER)" in md
        assert "| AUDIT-A4 | negative | pass |" in md  # existing rows intact

    def test_measurements_cover_every_result(self):
        report = run_conformance()
        for r in report["results"]:
            assert r["carrier"]["sizeBytes"] > 0
            assert set(r["carrier"]["minQrByEc"]) == {"L", "M", "Q", "H"}


class TestReportIntegration:
    @pytest.mark.skipif(
        not (EU_FIXTURES / "INDEX.json").exists(),
        reason="EN 18223 example corpus not present "
        "(licensed extraction, not distributed with the repository)",
    )
    def test_eu_profile_report_carries_the_carrier_column(self):
        from unidpp.adapters.en18223 import run_eu_profile_suite

        report = run_eu_profile_suite(EU_FIXTURES)
        by_id = {r["fixture"]: r for r in report["results"]}
        # The EN's own Annex A Example 3 lands in the QR v15-M band.
        ex3 = by_id["annexA-example3"]
        assert ex3["carrier"]["sizeBytes"] == 371
        assert ex3["carrier"]["minQrByEc"]["M"] == 15
        # Unparseable fixtures carry no measurement.
        assert by_id["annexA-example2"]["carrier"] is None

    def test_competitor_report_carries_carrier_observations(self):
        from scripts.competitor_report import run_competitor_suite

        report = run_competitor_suite(COMPETITORS)
        results = [r for v in report["vendors"] for r in v["results"]]
        by_fixture = {r["fixture"]: r for r in results}
        drill = by_fixture["drill-api-compressed"]
        assert drill["carrier"]["sizeBytes"] == 2917  # exceeds QR v40-M? no: 2331
        assert drill["carrier"]["minQrByEc"]["M"] is None  # 2917 > 2331
        # The AAS artifact is measured too (size only, no findings).
        aas = by_fixture["battery-passport.json"]
        assert aas["carrier"]["sizeBytes"] > 0
        assert len(aas["findings"]) == 1  # still only the coverage observation

    def test_render_column_formats(self):
        assert render(None) == "—"
        text = render(measure({"a": "x" * 380}, declared="qr-v15-M").to_dict())
        assert text == "388 B vs 412 B · qr-v15-M (fits)"
        over = render(measure({"a": "x" * 5000}, declared="qr-v15-M").to_dict())
        assert "OVER" in over
        big = render(measure({"a": "x" * 5000}).to_dict())
        assert big.endswith("exceeds QR v40-M")
