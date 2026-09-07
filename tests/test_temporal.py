"""Temporal conformance: the DPP temporal profile (ISO 8601-1:2019 incl.
Amd 1:2022 disambiguation) validates every timestamp field with precise
paths — valid timestamps pass, the AUDIT A4 en-dash form fails, and the
profile rules (calendar ranges, timezone discipline, end-of-day,
decimal sign, precision) each trip with a distinct code."""

from unidpp.conformance import CHECK_REGISTRY, negative_fixtures_a1_a6
from unidpp.temporal import (
    count_timestamp_fields,
    validate_document,
    validate_timestamp,
)


def codes_for(value: str, field: str = "lastUpdated") -> list[str]:
    finding = validate_timestamp(value, field)
    return [] if finding is None else [finding.code]


class TestValidTimestampsPass:
    def test_utc_z_designator_passes(self):
        assert validate_timestamp("2025-08-22T03:12:00Z", "lastUpdated") is None

    def test_lowercase_designators_pass(self):
        assert validate_timestamp("2025-08-22T03:12:00z", "lastUpdated") is None

    def test_numeric_offset_is_a_determinate_instant(self):
        assert validate_timestamp("2025-08-22T05:12:00+02:00", "validFrom") is None

    def test_fractional_seconds_dot_passes(self):
        for value in (
            "2026-06-17T23:20:58.5Z",
            "2026-06-17T23:20:58.0000000Z",  # the .NET round-trip form
        ):
            assert validate_timestamp(value, "lastUpdated") is None, value

    def test_leap_day_in_leap_year_passes(self):
        assert validate_timestamp("2024-02-29T00:00:00Z", "issuedAt") is None


class TestAuditA4Reproduced:
    def test_en_dash_separators_fail_with_precise_path(self):
        findings = validate_document({"lastUpdated": "2025–08–22T03:12:00Z"})
        assert len(findings) == 1
        assert findings[0].code == "T1-separator-typography"
        assert findings[0].path == "$.lastUpdated"
        assert "AUDIT A4" in findings[0].message
        assert "ISO 8601-1" in findings[0].message

    def test_audit_a4_negative_fixture_reproduces_the_finding(self):
        """The EN corpus A-family timestamp finding, reproduced by the
        temporal check over the AUDIT A4 fixture document."""
        a4 = next(
            fx for fx in negative_fixtures_a1_a6() if fx["fixture"] == "AUDIT-A4"
        )
        findings = validate_document(a4["document"])
        assert [f.code for f in findings] == ["T1-separator-typography"]
        assert findings[0].path == "$.lastUpdated"

    def test_nested_event_timestamp_carries_indexed_path(self):
        doc = {
            "events": [
                {"occurredAt": "2026-08-03T09:15:00Z"},
                {"occurredAt": "2026–08–03T09:15:01Z"},
            ]
        }
        findings = validate_document(doc)
        assert [f.path for f in findings] == ["$.events[1].occurredAt"]


class TestProfileRules:
    def test_basic_format_rejected(self):
        assert codes_for("20250822T031200Z") == ["T3-basic-format"]
        assert codes_for("20250822") == ["T3-basic-format"]

    def test_reduced_precision_rejected(self):
        assert codes_for("2025-08-22") == ["T4-reduced-precision"]
        assert codes_for("2025-08-22T03:12Z") == ["T4-reduced-precision"]

    def test_calendar_ranges_rejected(self):
        assert codes_for("2025-13-22T03:12:00Z") == ["T5-calendar-out-of-range"]
        assert codes_for("2025-00-22T03:12:00Z") == ["T5-calendar-out-of-range"]
        assert codes_for("2025-08-00T03:12:00Z") == ["T5-calendar-out-of-range"]
        assert codes_for("2025-08-32T03:12:00Z") == ["T5-calendar-out-of-range"]
        assert codes_for("2025-08-22T25:12:00Z") == ["T5-calendar-out-of-range"]
        assert codes_for("2025-08-22T03:60:00Z") == ["T5-calendar-out-of-range"]
        assert codes_for("2025-08-22T03:12:61Z") == ["T5-calendar-out-of-range"]

    def test_february_29_leap_year_rule(self):
        # 2023 is not a leap year; 2024 is.
        assert codes_for("2023-02-29T00:00:00Z") == ["T5-calendar-out-of-range"]
        assert "leap-year" in validate_timestamp("2023-02-29T00:00:00Z", "x").message

    def test_leap_second_rejected_for_determinism(self):
        finding = validate_timestamp("2016-12-31T23:59:60Z", "lastUpdated")
        assert finding.code == "T5-calendar-out-of-range"
        assert "leap-second" in finding.message

    def test_end_of_day_2400_rejected_per_amd1(self):
        finding = validate_timestamp("2025-08-22T24:00:00Z", "validUntil")
        assert finding.code == "T6-end-of-day-2400"
        assert "00:00:00" in finding.message  # the required replacement form
        # 24:30 is out of range outright, not the end-of-day form.
        assert codes_for("2025-08-22T24:30:00Z") == ["T5-calendar-out-of-range"]

    def test_timezone_missing_rejected(self):
        """The freeDPP server-local form: no timezone designator."""
        finding = validate_timestamp("2026-04-01T16:07:24", "lastUpdated")
        assert finding.code == "T7-timezone-missing"
        assert "UTC" in finding.message

    def test_decimal_comma_rejected(self):
        finding = validate_timestamp("2025-08-22T03:12:00,5Z", "lastUpdated")
        assert finding.code == "T8-decimal-comma"

    def test_non_extended_shapes_rejected(self):
        assert codes_for("2025-08-22 03:12:00Z") == ["T2-not-extended-date-time"]
        assert codes_for("2025-08-22T03:12:00+0200") == ["T2-not-extended-date-time"]
        assert codes_for("2025W341T031200Z") == ["T2-not-extended-date-time"]
        assert codes_for("10000-01-01T00:00:00Z") == ["T2-not-extended-date-time"]

    def test_week_date_message_names_the_rule(self):
        finding = validate_timestamp("2025-W34-1T03:12:00Z", "lastUpdated")
        assert finding.code == "T2-not-extended-date-time"
        assert "calendar date" in finding.message


class TestDocumentWalk:
    def test_conditional_keys_only_flag_date_shaped_values(self):
        """status-change payload state strings are not timestamps."""
        doc = {
            "payload": {"from": "active", "until": "suspended"},
        }
        assert validate_document(doc) == []
        assert count_timestamp_fields(doc) == 0

    def test_conditional_keys_flag_date_shaped_values(self):
        doc = {"effective": {"from": "2027-01-01T00:00:00Z", "until": "not-a-date"}}
        findings = validate_document(doc)
        # 'from' is date-shaped and valid; 'until' is not date-shaped — skipped
        assert findings == []
        assert count_timestamp_fields(doc) == 1

    def test_all_timestamp_field_names_are_examined(self):
        doc = {key: "2025-08-22T03:12:00Z" for key in (
            "lastUpdated", "validFrom", "validUntil", "issuedAt",
            "occurredAt", "asOf", "notBefore", "notAfter", "signedAt",
            "declaredAt",
        )}
        assert count_timestamp_fields(doc) == 10
        assert validate_document(doc) == []


class TestRunnerIntegration:
    def test_check_registered_in_the_registry(self):
        assert "temporal-conformance" in CHECK_REGISTRY
        check = CHECK_REGISTRY["temporal-conformance"]
        assert "ISO 8601-1" in check.title

    def test_positive_fixtures_are_temporally_clean(self):
        findings = CHECK_REGISTRY["temporal-conformance"].fn(
            {"lastUpdated": "2025–08–22T03:12:00Z"}
        )
        assert [f.code for f in findings] == ["T1-separator-typography"]
        assert "$.lastUpdated" in findings[0].message  # precise path surfaces
