"""The mapping discipline as data (the foreign harness's F3 leg).

Written from the mapping clause (Part 7) and Annex B alone, no
reference code: a foreign implementation holds cross-register
mapping items as data, derives their canonical bytes, applies
tier-1 chains with its own transform code, refuses a tier-2
correspondence inside a deterministic application, and renders
tier-3 pairs as distinct items with no correspondence asserted.

The suite-side vector these functions must reproduce lives in the
family checkout: ``unidpp-core/crates/semantics/fixtures/canonical/
mapping-chain.json``.
"""

from __future__ import annotations

import hashlib

from .framing import canonical_fields, le_u64


class MappingFailure(Exception):
    """A mapping discipline refusal — stated, never guessed."""


def mapping_item_canonical(item: dict) -> bytes:
    """The item's canonical form: source, target, version, the tier
    token and its fields (tier 1: the transform reference; tier 2:
    the scope sorted, the residual, the attester; tier 3: the
    note)."""
    kind = item["kind"]
    parts = [
        item["source"].encode(),
        item["target"].encode(),
        le_u64(item["version"]),
    ]
    tier = kind["tier"]
    if tier == "deterministic":
        parts.extend([b"tier-1", kind["transform"].encode()])
    elif tier == "correspondence":
        parts.append(b"tier-2")
        for scope in sorted(kind["scope"]):
            parts.append(scope.encode())
        parts.extend([kind["residual"].encode(), kind["attester"].encode()])
    elif tier == "no-mapping":
        parts.extend([b"tier-3", kind["note"].encode()])
    else:
        raise MappingFailure(f"unknown mapping tier `{tier}`")
    return canonical_fields(parts)


def mapping_item_digest(item: dict) -> bytes:
    return hashlib.sha256(mapping_item_canonical(item)).digest()


def apply_deterministic(chain: dict, value: str, transform) -> str:
    """Apply a chain of tier-1 mappings: each hop names a transform
    by reference; the caller supplies the local transform code. A
    tier-2 hop inside a deterministic application is REFUSED —
    correspondences are not transforms — and the refusal names the
    hop. A tier-3 hop never composes into a chain at all."""
    current = value
    for hop in chain["hops"]:
        kind = hop["kind"]
        if kind["tier"] != "deterministic":
            raise MappingFailure(
                f"a `{kind['tier']}` hop ({hop['source']} → {hop['target']}) "
                "cannot apply deterministically: correspondences are not "
                "transforms"
            )
        current = transform(current, kind["transform"])
    return current


def versions(chain: dict) -> list[tuple[str, int]]:
    """Every constituent mapping version, recorded: the chain's
    provenance travels with it."""
    return [(f"{h['source']}→{h['target']}", h["version"]) for h in chain["hops"]]
