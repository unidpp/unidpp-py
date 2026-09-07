"""Carrier budget conformance: ISO/IEC 18004 QR capacity tables (T-26).

The `carrier` conformance check (TODO.impl/74). Pure functions over data —
no IO; the caller owns fixtures and reports.

Provenance of the tables and the grammar (checked and ported verbatim):

- The QR byte-mode data-capacity tables are ported from the CLI's core:
  ``unidpp-core/crates/tier_a/src/qr.rs`` (the module the CLI's pack
  command budgets against; ``unidpp-cli/src/packfile.rs`` parses the
  budget token). They are the ISO/IEC 18004 data-capacity tables, byte
  mode, per symbol version 1..=40 and error-correction level L/M/Q/H —
  the same numbers EN 18220-class carriers are budgeted against.
- The budget grammar ``qr-v<version>-<ec>`` is a port of
  ``unidpp-cli/src/packfile.rs::parse_budget`` (case-insensitive,
  version 1..=40, ec one of L/M/Q/H).
- The framework spec, clause 10.4 (carrier budgets): the smallest
  version that holds the payload at the configured EC level is
  selected; an over-budget payload is rejected with an explicit error
  and never silently truncated; the default configuration is EC level
  M with maximum version 40 (the CLI's ``DEFAULT_BUDGET``).
- The plan's EN 18220 carrier-class reading spans QR v10-M (floor) to
  v40-H (ceiling); recorded as ``EN18220_QR_CLASS_SPAN`` for reference.
  The check itself accepts any declared class within the ported table.

Serialized size: ``serialized_size`` measures the canonical JSON
serialization (RFC 8785-lite, ``unidpp.canonical``) — the deterministic
compact form. For an EN 18223 payload this is the compressed (clause
5.2) form's byte size; for a neutral-core fixture it is the canonical
wire form. (The Rust CLI budgets its own tagged byte encoding with
projected signature lengths; both budget against these same capacity
tables — the py mirror measures canonical JSON, its wire form.)

Note: the TS SDK's ``CARRIER_BUDGETS`` (mirrored in
``unidpp.model.CARRIER_BUDGETS``) are approximate legacy values that
disagree with ISO/IEC 18004 for v15/v25 (1098/1853 vs 520/1273 at L);
the ported tables here are the authoritative budget source, per the
task brief ("use the same capacity tables the CLI implements").

Carrier budgets bind Tier-A carrier-embedded packs, not served Tier-B
documents: for documents without a declared carrier class the check
records a measurement only (size and the smallest QR class that would
hold it); a payload that exceeds its *declared* class is flagged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from . import model as M
from .canonical import canonical_json

__all__ = [
    "CARRIER_CODES",
    "DEFAULT_BUDGET",
    "EC_LEVELS",
    "EN18220_QR_CLASS_SPAN",
    "QR_BYTE_CAPACITY",
    "CarrierBudgetError",
    "CarrierMeasurement",
    "byte_capacity",
    "check_payload",
    "measure",
    "min_version_for",
    "parse_budget",
    "render",
    "serialized_size",
]

#: ISO/IEC 18004 byte-mode data capacity, version 1..=40 per EC level
#: (ported verbatim from unidpp-core/crates/tier_a/src/qr.rs).
QR_BYTE_CAPACITY: dict[str, tuple[int, ...]] = {
    "L": (
        17, 32, 53, 78, 106, 134, 154, 192, 230, 271,
        321, 367, 425, 458, 520, 586, 644, 718, 792, 858,
        929, 1003, 1091, 1171, 1273, 1367, 1465, 1528, 1628, 1732,
        1840, 1952, 2068, 2188, 2303, 2431, 2563, 2699, 2809, 2953,
    ),
    "M": (
        14, 26, 42, 62, 84, 106, 122, 152, 180, 213,
        251, 287, 331, 362, 412, 450, 504, 560, 624, 666,
        711, 779, 857, 911, 997, 1059, 1125, 1190, 1264, 1370,
        1452, 1538, 1628, 1722, 1809, 1911, 1989, 2099, 2213, 2331,
    ),
    "Q": (
        11, 20, 32, 46, 60, 74, 86, 108, 130, 151,
        177, 203, 241, 258, 292, 322, 364, 394, 442, 482,
        509, 565, 611, 661, 715, 751, 805, 868, 908, 982,
        1030, 1112, 1168, 1228, 1283, 1351, 1423, 1499, 1579, 1663,
    ),
    "H": (
        7, 14, 24, 34, 44, 58, 64, 84, 98, 119,
        137, 155, 177, 194, 220, 250, 280, 310, 338, 382,
        403, 439, 461, 511, 535, 593, 625, 658, 698, 742,
        790, 842, 898, 958, 983, 1051, 1093, 1139, 1219, 1273,
    ),
}

EC_LEVELS: tuple[str, ...] = ("L", "M", "Q", "H")

#: The CLI's default carrier budget (unidpp-cli packfile.rs DEFAULT_BUDGET).
DEFAULT_BUDGET = "qr-v40-M"

#: The plan's EN 18220 carrier-class span (floor … ceiling), for reference.
EN18220_QR_CLASS_SPAN: tuple[str, str] = ("qr-v10-M", "qr-v40-H")

#: Finding codes emitted by this check.
CARRIER_CODES: tuple[str, ...] = (
    "C1-carrier-over-budget",
    "C2-carrier-budget-malformed",
)

_BUDGET_RE = re.compile(r"^qr-v(\d{1,2})-([lmqh])$")


class CarrierBudgetError(ValueError):
    """Raised for a malformed carrier budget token."""


def byte_capacity(version: int, ec: str) -> int:
    """Byte-mode capacity of QR ``version`` (1..=40) at EC level ``ec``."""
    table = QR_BYTE_CAPACITY.get(ec.upper())
    if table is None:
        raise CarrierBudgetError(f"unknown EC level {ec!r} (expected L/M/Q/H)")
    if not 1 <= version <= 40:
        raise CarrierBudgetError(f"QR version {version} out of range 1..=40")
    return table[version - 1]


def min_version_for(size: int, ec: str) -> int | None:
    """Smallest QR version (1..=40) that holds ``size`` bytes at ``ec``."""
    table = QR_BYTE_CAPACITY.get(ec.upper())
    if table is None:
        raise CarrierBudgetError(f"unknown EC level {ec!r} (expected L/M/Q/H)")
    for version, capacity in enumerate(table, start=1):
        if capacity >= size:
            return version
    return None


def parse_budget(token: str) -> tuple[str, int]:
    """Parse a ``qr-v<version>-<ec>`` budget token → (ec, version).

    Port of the CLI grammar: case-insensitive, version 1..=40, EC level
    one of L/M/Q/H. Raises :class:`CarrierBudgetError` on bad tokens.
    """
    normalized = token.strip().lower()
    m = _BUDGET_RE.match(normalized)
    if m is None:
        raise CarrierBudgetError(
            f"bad budget {token!r} (expected the qr-v15-M form: qr-v<version>-<ec>)"
        )
    version = int(m.group(1))
    ec = m.group(2).upper()
    if not 1 <= version <= 40:
        raise CarrierBudgetError(f"bad budget {token!r}: QR version must be 1..=40")
    return ec, version


def _plain(value: Any) -> Any:
    """Convert model objects (to_dict carriers) to plain JSON-able data."""
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def serialized_size(payload: Any) -> int:
    """Canonical-JSON serialized size of the payload, in bytes.

    RFC 8785-lite (sorted keys, no whitespace) via ``unidpp.canonical`` —
    the deterministic compact serialization (the EN 18223 clause-5.2
    compressed form's byte size).
    """
    return len(canonical_json(_plain(payload)).encode("utf-8"))


@dataclass(frozen=True)
class CarrierMeasurement:
    """Carrier-budget observation for the report column."""

    size_bytes: int
    min_qr_by_ec: dict[str, int | None]
    declared: str | None = None
    declared_capacity: int | None = None
    fits_declared: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sizeBytes": self.size_bytes,
            "minQrByEc": dict(self.min_qr_by_ec),
            "declared": self.declared,
            "declaredCapacity": self.declared_capacity,
            "fitsDeclared": self.fits_declared,
        }


def measure(payload: Any, declared: str | None = None) -> CarrierMeasurement:
    """Measure a payload against the capacity tables (observation only)."""
    size = serialized_size(payload)
    by_ec = {ec: min_version_for(size, ec) for ec in EC_LEVELS}
    measurement = CarrierMeasurement(size_bytes=size, min_qr_by_ec=by_ec)
    if declared is None:
        return measurement
    ec, version = parse_budget(declared)
    capacity = byte_capacity(version, ec)
    return CarrierMeasurement(
        size_bytes=size,
        min_qr_by_ec=by_ec,
        declared=declared,
        declared_capacity=capacity,
        fits_declared=size <= capacity,
    )


def check_payload(payload: Any, declared: str) -> list[M.Finding]:
    """Check a payload against its declared carrier class.

    An over-budget payload fails loudly with the computed size versus
    the capacity (framework spec 10.4 e: explicit error, never silent
    truncation). A payload with no declared class produces no findings —
    the measurement alone is recorded by :func:`measure`.
    """
    try:
        ec, version = parse_budget(declared)
    except CarrierBudgetError as exc:
        return [
            M.Finding(
                severity="error",
                code="C2-carrier-budget-malformed",
                message=str(exc),
            )
        ]
    capacity = byte_capacity(version, ec)
    size = serialized_size(payload)
    if size > capacity:
        return [
            M.Finding(
                severity="error",
                code="C1-carrier-over-budget",
                message=(
                    f"serialized payload is {size} bytes; declared carrier "
                    f"class {declared} holds {capacity} bytes "
                    f"(ISO/IEC 18004 byte-mode capacity, v{version}-{ec}) — "
                    "over budget; shrink the resolver URI or drop signature "
                    "suites, never truncate silently"
                ),
            )
        ]
    return []


def render(measurement: dict[str, Any] | None) -> str:
    """Render a measurement dict as the report's carrier column text."""
    if measurement is None:
        return "—"
    size = measurement["sizeBytes"]
    token = measurement.get("declared")
    if token is not None:
        capacity = measurement.get("declaredCapacity")
        fits = measurement.get("fitsDeclared")
        verdict = "fits" if fits else "OVER"
        return f"{size} B vs {capacity} B · {token} ({verdict})"
    min_m = (measurement.get("minQrByEc") or {}).get("M")
    if min_m is None:
        return f"{size} B · exceeds QR v40-M"
    return f"{size} B · QR v{min_m}-M"
