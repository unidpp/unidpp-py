"""Canonical serialization + digests.

Mirror of ``@unidpp/model`` ``canonical.ts`` (I4 commitment hashing, S6
anchoring). Logs anchor commitments (hashes), never facts — log operators
cannot correlate edges. Stdlib-only (``hashlib``/``base64``); no WebCrypto.

Canonical JSON is "RFC 8785-lite", exactly as in the TS reference: sorted
keys, no whitespace, strings emitted as JSON strings (non-ASCII kept raw),
numbers via their shortest round-trip form, non-finite numbers rejected.

Known deviation from the TS reference (documented, benign for the corpus):
JavaScript ``String(number)`` and Python ``repr(number)`` agree on integers
and on most floats but differ on some exponent forms (e.g. ``1e21`` vs
``1e+21``). The UniDPP corpus puts quantities in integers or strings, so the
canonical bytes here match the TS SDK for every value the fixtures,
verifiers and conformance runners exercise. Full ES6/JCS number
serialization is intentionally out of scope for the stdlib-only core.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
from typing import Any

__all__ = [
    "canonical_json",
    "commitment",
    "from_base64",
    "sha256_hex",
    "to_base64",
    "to_hex",
]


def _format_number(value: float) -> str:
    if math.isfinite(value) is False:
        raise ValueError(f"non-finite number: {value!r}")
    if value == int(value) and abs(value) < 1e16:
        return str(int(value))
    return repr(value)


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):  # pragma: no cover - handled above
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _format_number(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_serialize(v) for v in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys())
        parts = [
            json.dumps(k, ensure_ascii=False) + ":" + _serialize(value[k])
            for k in keys
        ]
        return "{" + ",".join(parts) + "}"
    raise TypeError(f"cannot canonicalize: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """RFC 8785-lite canonical JSON: sorted keys, no whitespace."""
    return _serialize(value)


def sha256_hex(data: str | bytes) -> str:
    """SHA-256 digest as lowercase hex."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return to_hex(hashlib.sha256(data).digest())


def to_hex(data: bytes) -> str:
    return "".join(f"{b:02x}" for b in data)


def to_base64(data: bytes) -> str:
    """RFC 4648 base64 (mirrors the pure-JS implementation in canonical.ts)."""
    return base64.b64encode(data).decode("ascii")


def from_base64(text: str) -> bytes:
    """Strict-ish base64 decode; raises on invalid characters."""
    cleaned = text.rstrip("=")
    if not cleaned:
        return b""
    remainder = len(cleaned) % 4
    if remainder == 1:
        raise ValueError(f"invalid base64 length: {len(text)}")
    pad = (-len(cleaned)) % 4
    try:
        return base64.b64decode(cleaned + "=" * pad, validate=True)
    except Exception as exc:
        raise ValueError(f"invalid base64: {exc}") from exc


def commitment(value: Any, salt: str = "") -> str:
    """Commitment over canonical JSON with a salt (S6 salt discipline).

    Mirrors ``canonical.ts``: ``sha256_hex(salt + ":" + canonicalJson(value))``.
    """
    return sha256_hex(f"{salt}:{canonical_json(value)}")
