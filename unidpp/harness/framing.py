"""The foreign harness — Annex B canonicalization in pure Python.

A second-language implementation of the canonical encoding (spec
Annex B), written from the specification: the framing rule, the
domain tags, and the per-object field orders. It exists to prove the
cross-implementation contract (CN-1): an implementation we did not
write reproduces the reference fixtures' digests exactly.

Stdlib only (``hashlib``); every derivation mirrors Annex B, not the
Rust code.
"""

from __future__ import annotations

import hashlib
import struct

SEGMENT_COMMITMENT = b"UNIDPP-GRID/SEGMENT-COMMITMENT"
SPINE_LEAF = b"UNIDPP-GRID/SPINE-LEAF"
SPINE_NODE = b"UNIDPP-GRID/SPINE-NODE"
SPINE_DIGEST = b"UNIDPP-GRID/SPINE-DIGEST"

__all__ = [
    "SEGMENT_COMMITMENT",
    "SPINE_DIGEST",
    "SPINE_LEAF",
    "SPINE_NODE",
    "canonical_fields",
    "domain_frame",
    "hash_in",
    "sha256",
]


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _part(part: bytes) -> bytes:
    """One canonical field: u32 little-endian length prefix + bytes."""
    return struct.pack("<I", len(part)) + part


def canonical_fields(parts: list[bytes]) -> bytes:
    """The canonical form: fields in declared order, each length-prefixed."""
    return b"".join(_part(p) for p in parts)


def domain_frame(tag: bytes, payload: bytes) -> bytes:
    """The one framing rule: ``tag || 0x00 || payload``."""
    return tag + b"\x00" + payload


def hash_in(domain: bytes, parts: list[bytes]) -> bytes:
    """Hash in a domain: sha256 over the domain-framed canonical parts."""
    return sha256(domain_frame(domain, canonical_fields(parts)))


def le_u64(value: int) -> bytes:
    return struct.pack("<Q", value)


def le_u32(value: int) -> bytes:
    return struct.pack("<I", value)
