"""DPP temporal profile: ISO 8601-1 conformance for every timestamp field.

The `temporal` conformance check (TODO.impl/73, T-25). Pure functions over
data — no IO; the caller (the conformance runner or the EU-profile adapter)
owns fixtures and reports.

Source of the profile rules (checked and documented):

- EN 18223:2026 Table 1 (4.1.2.1): ``lastUpdated`` is a "String formatted
  as Timestamp UTC-based according to ISO 8601-1:2019"; the normative
  references clause cites ISO 8601-1:2019 *"as impacted by
  ISO 8601-1:2019/A1:2022"* — the disambiguation amendment.
- UniDPP framework spec, clause 7 (event model): ``occurredAt`` is "a UTC
  timestamp per ISO 8601-1 (local time is a presentation concern)".
- The Amd 1:2022 disambiguation rules are applied as the profile's
  resolution of the ambiguities ISO 8601-1 leaves open — each rule below
  names the ambiguity it resolves: separators (HYPHEN-MINUS and COLON
  only; en/em dashes are typography, not separators), the decimal sign
  ('.', not ','), the end-of-day special case (24:00:00 is rejected in
  favour of the next day's 00:00:00 — one instant, one representation),
  and the 'T'/'Z' designators.
- The calconnect/iso-8601-test-suite repository
  (~/src/calconnect/iso-8601-test-suite) was checked for importable
  validators per the task brief: it is a Ruby harness
  (``lib/test_suite/*.rb``) driving language adapters over a
  newline-delimited JSON stdio protocol (``adapters/TEMPLATE.rb``);
  ``adapters/python/datetime.py`` is the adapter that puts the *CPython
  stdlib* under test — it is not a reusable profile validator, and the
  Ruby harness is not importable from Python. The DPP temporal profile
  is therefore implemented directly here, with the test suite's rule
  corpus (month 13 invalid, day 00 invalid, hour 24 end-of-day only,
  leading zeros mandatory, 5-digit years rejected without expansion
  agreement) as the rule reference.

Profile rules (one finding per value; first trip wins):

- ``T1-separator-typography`` — non-ASCII separator characters (en/em
  dash, minus sign U+2212, typographic quotes). This reproduces the
  AUDIT.md A4 finding family (the EN's own Annex B example prints
  ``2025–08–22T03:12:00Z``).
- ``T2-not-extended-date-time`` — not an extended-format calendar
  date-time (the model's wire schemas declare ``format: date-time``;
  basic format, week dates, ordinal dates, a space in place of the 'T'
  designator, an offset without the ':' separator, or any other shape
  fails here).
- ``T3-basic-format`` — a well-formed *basic*-format representation
  (digits without separators); valid ISO 8601-1, but the DPP profile
  fixes the extended format (Amd 1 separator disambiguation).
- ``T4-reduced-precision`` — a date without time, or a time without
  seconds: the DPP profile requires second precision so every
  commitment-ordered instant is determinate.
- ``T5-calendar-out-of-range`` — month 1–12, day 1–days-in-month
  (leap-year aware), hour ≤ 23, minute ≤ 59, second ≤ 59. Leap-second
  ``:60`` is valid ISO 8601-1 on actual leap-second dates but is
  rejected here: the framework model's parser fixes deterministic
  seconds 0–59.
- ``T6-end-of-day-2400`` — the ISO 8601-1/Amd 1 end-of-day form
  ``24:00:00``: rejected; the profile requires the next day's
  ``00:00:00`` (one instant, one representation).
- ``T7-timezone-missing`` — no zone designator. "UTC-based" (EN 18223
  Table 1) and "a UTC timestamp" (framework spec, clause 7) exclude
  local time; server-local values without a designator trip here (the
  freeDPP ``DateTime.Now`` artifacts).
- ``T8-decimal-comma`` — ',' as the fractional-seconds decimal sign:
  valid ISO 8601-1, but the profile fixes '.' (Amd 1 disambiguation;
  RFC 3339 interoperability).

Accepted: uppercase or lowercase 'T'/'Z' designators (the model's wire
validator accepts both cases), numeric UTC offsets ``±hh:mm`` (a
determinate instant — normalized to UTC by the core parser; the
canonical display form is 'Z').
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

__all__ = [
    "TIMESTAMP_FIELDS",
    "TemporalFinding",
    "count_timestamp_fields",
    "validate_document",
    "validate_timestamp",
]

#: Keys that always denote a timestamp when they carry a string value.
TIMESTAMP_FIELDS: tuple[str, ...] = (
    "lastUpdated",  # EN 18223 Table 1 (4.1.2.1)
    "lastUpdate",  # the IDTA drift spelling (PA2)
    "validFrom",
    "validUntil",
    "issuedAt",
    "occurredAt",  # framework spec clause 7
    "asOf",
    "notBefore",  # Tier-A validity
    "notAfter",
    "signedAt",  # signature framings
    "declaredAt",  # revocation records
)

#: Generic key names that denote a timestamp only when the value is
#: date-shaped — guards against payload values such as status-change
#: ``from``/``until`` state strings.
_CONDITIONAL_FIELDS = ("from", "until")  # effective windows / link intervals

_DATE_SHAPED_RE = re.compile(r"^\s*\d{4}")

_EXTENDED_RE = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"(?:[Tt](?P<hour>\d{2}):(?P<minute>\d{2})"
    r"(?::(?P<second>\d{2})(?P<fraction>[.,]\d+)?)?)?"
    r"(?P<zone>[Zz]|[+-]\d{2}:\d{2})?$"
)
_BASIC_RE = re.compile(
    r"^\d{8}T\d{2}\d{2}(\d{2})?([.,]\d+)?([Zz]|[+-]\d{2}\d{2})?$|^\d{8}$"
)

_TYPOGRAPHY_CHARS = "–—−‘’“”"

_TABLE_1_CITATION = (
    "EN 18223 Table 1 (4.1.2.1): 'String formatted as Timestamp UTC-based "
    "according to ISO 8601-1:2019' (as impacted by ISO 8601-1:2019/A1:2022)"
)


@dataclass(frozen=True)
class TemporalFinding:
    """One temporal-profile violation with a precise JSONPath location."""

    path: str
    field: str
    value: str
    code: str
    message: str


def validate_timestamp(value: str, field: str) -> TemporalFinding | None:
    """Validate one timestamp value against the DPP temporal profile.

    Returns the first rule violation, or None when the value conforms.
    """
    if any(c in value for c in _TYPOGRAPHY_CHARS):
        return TemporalFinding(
            path="",
            field=field,
            value=value,
            code="T1-separator-typography",
            message=(
                f"{value!r} uses non-ASCII separator characters (en/em dash "
                "or typographic quotes); ISO 8601-1 separators are "
                "HYPHEN-MINUS '-' and COLON ':' only (AUDIT A4; "
                + _TABLE_1_CITATION
                + ")"
            ),
        )

    m = _EXTENDED_RE.match(value)
    if m is None:
        if _BASIC_RE.match(value):
            return TemporalFinding(
                path="",
                field=field,
                value=value,
                code="T3-basic-format",
                message=(
                    f"{value!r} is a basic-format representation (no "
                    "separators); the DPP profile fixes the extended format "
                    "YYYY-MM-DDThh:mm:ss with ':' and '-' separators "
                    "(Amd 1 disambiguation; the wire schemas declare "
                    "format: date-time)"
                ),
            )
        detail = ""
        if " " in value:
            detail = "; a space is not the time designator — use 'T'"
        elif re.search(r"[+-]\d{4}$", value):
            detail = "; an offset without the ':' separator is basic format"
        elif re.match(r"^\d{4}-?W", value) or re.match(r"^\d{4}-\d{3}", value):
            detail = (
                "; week and ordinal dates are not part of the DPP profile — "
                "use the calendar date"
            )
        return TemporalFinding(
            path="",
            field=field,
            value=value,
            code="T2-not-extended-date-time",
            message=(
                f"{value!r} is not an extended-format ISO 8601-1 calendar "
                "date-time of the form YYYY-MM-DDThh:mm:ss[.f](Z|±hh:mm)"
                + detail
                + " (" + _TABLE_1_CITATION + ")"
            ),
        )

    if m.group("hour") is None:
        return TemporalFinding(
            path="",
            field=field,
            value=value,
            code="T4-reduced-precision",
            message=(
                f"{value!r} is a date without a time of day; the DPP profile "
                "requires full second precision so every instant is "
                "determinate (the wire schemas declare format: date-time)"
            ),
        )
    if m.group("second") is None:
        return TemporalFinding(
            path="",
            field=field,
            value=value,
            code="T4-reduced-precision",
            message=(
                f"{value!r} carries minute precision only; the DPP profile "
                "requires full second precision so every instant is "
                "determinate (the wire schemas declare format: date-time)"
            ),
        )

    year, month, day = int(m.group("year")), int(m.group("month")), int(m.group("day"))
    hour, minute, second = (
        int(m.group("hour")),
        int(m.group("minute")),
        int(m.group("second")),
    )

    if hour == 24:
        if minute == 0 and second == 0:
            return TemporalFinding(
                path="",
                field=field,
                value=value,
                code="T6-end-of-day-2400",
                message=(
                    f"{value!r} uses the ISO 8601-1/Amd 1 end-of-day form "
                    "24:00:00; the DPP profile rejects it as an ambiguous "
                    "double representation of an instant — express the next "
                    "day's 00:00:00 instead (Amd 1 disambiguation)"
                ),
            )
        return _range_finding(field, value, "hour", 24, "0–23")

    if not 1 <= month <= 12:
        return _range_finding(field, value, "month", month, "01–12")
    days_in_month = calendar.monthrange(year, month)[1]
    if not 1 <= day <= days_in_month:
        detail = (
            " (leap-year rule: February has 29 days only in leap years)"
            if month == 2 and day == 29
            else ""
        )
        return TemporalFinding(
            path="",
            field=field,
            value=value,
            code="T5-calendar-out-of-range",
            message=(
                f"{value!r}: day {day:02d} is out of range for {year:04d}-"
                f"{month:02d} (1–{days_in_month}){detail}"
            ),
        )
    if hour > 23:
        return _range_finding(field, value, "hour", hour, "00–23")
    if minute > 59:
        return _range_finding(field, value, "minute", minute, "00–59")
    if second > 59:
        note = (
            " — leap-second :60 is valid ISO 8601-1 on actual leap-second "
            "dates but the framework model fixes deterministic seconds 0–59"
            if second == 60
            else ""
        )
        return TemporalFinding(
            path="",
            field=field,
            value=value,
            code="T5-calendar-out-of-range",
            message=f"{value!r}: second {second:02d} is out of range (00–59){note}",
        )

    fraction = m.group("fraction")
    if fraction is not None and fraction.startswith(","):
        return TemporalFinding(
            path="",
            field=field,
            value=value,
            code="T8-decimal-comma",
            message=(
                f"{value!r} uses ',' as the fractional-seconds decimal "
                "sign; the DPP profile fixes '.' (Amd 1 disambiguation; "
                "RFC 3339 interoperability)"
            ),
        )

    if m.group("zone") is None:
        return TemporalFinding(
            path="",
            field=field,
            value=value,
            code="T7-timezone-missing",
            message=(
                f"{value!r} carries no timezone designator; timestamps are "
                "UTC-based — use 'Z' or a numeric offset ±hh:mm (local time "
                "is a presentation concern; " + _TABLE_1_CITATION + ")"
            ),
        )

    return None


def _range_finding(
    field: str, value: str, component: str, actual: int, allowed: str
) -> TemporalFinding:
    return TemporalFinding(
        path="",
        field=field,
        value=value,
        code="T5-calendar-out-of-range",
        message=(
            f"{value!r}: {component} {actual} is out of range ({allowed})"
        ),
    )


def _walk_timestamps(node: Any, path: str = "$"):
    """Yield (path, key, value) for every timestamp field in the tree.

    Model objects (dataclasses carrying ``to_dict``) are walked in their
    wire form, so fixtures holding manifests, events and links are
    examined without a conversion step in the caller.
    """
    if hasattr(node, "to_dict"):
        node = node.to_dict()
    if isinstance(node, Mapping):
        for key, value in node.items():
            child = f"{path}.{key}"
            if isinstance(value, str):
                if key in TIMESTAMP_FIELDS or (
                    key in _CONDITIONAL_FIELDS and _DATE_SHAPED_RE.match(value)
                ):
                    yield child, key, value
            else:
                yield from _walk_timestamps(value, child)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _walk_timestamps(item, f"{path}[{i}]")


def count_timestamp_fields(node: Any) -> int:
    """How many timestamp fields the document carries (report column)."""
    return sum(1 for _ in _walk_timestamps(node))


def validate_document(node: Any) -> list[TemporalFinding]:
    """Validate every timestamp field in a fixture or foreign artifact."""
    findings: list[TemporalFinding] = []
    for path, key, value in _walk_timestamps(node):
        finding = validate_timestamp(value, key)
        if finding is not None:
            findings.append(
                TemporalFinding(
                    path=path,
                    field=finding.field,
                    value=finding.value,
                    code=finding.code,
                    message=finding.message,
                )
            )
    return findings
