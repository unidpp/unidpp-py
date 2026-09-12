"""The inter-scheme protocol subset (the foreign harness's third
leg).

The second-implementation rule names three legs: the grammar
(Annex B), the frozen view (F1), and a subset of the inter-scheme
protocol. This module is the third leg, written from Annex B and
the clause text alone, no reference code: a foreign implementation
reads a signed interop declaration (verifying the declarer's
Ed25519 signature over the domain-framed canonical bytes), and
replays a recorded verification route (re-deriving the coverage
report's entries from the trace alone).

The suite-side vectors these functions must reproduce live in the
family checkout: ``unidpp-signatif/fixtures/canonical/
interop-declaration.json`` (copied to this repo's
``tests/harness/canonical/``) and ``unidpp-core/crates/s13/
fixtures/canonical/verification-route.json``.
"""

from __future__ import annotations

from .ed25519 import verify as ed25519_verify
from .framing import canonical_fields, domain_frame, le_u64

DECLARATION_DOMAIN = b"UNIDPP-SIGNATIF/INTEROP-DECLARATION"

# The harmonization ladder (SI-5): the wire token is the kebab-case
# level name; the canonical form carries the ordinal.
LEVEL_ORDINALS = {
    "l0": 0,
    "l1": 1,
    "l2": 2,
    "l3": 3,
    "l4": 4,
    "l5": 5,
}


class ProtocolFailure(Exception):
    """A form or signature check refused — stated, never guessed."""


def declaration_canonical(declaration: dict) -> bytes:
    """The canonical, signable form of an interop declaration:
    declarer, counterpart, version, each posture (class, level
    ordinal, recognition token, sorted transport tokens,
    escalation, reciprocity), window — postures in sorted class
    order."""
    postures = sorted(declaration["postures"], key=lambda p: p["data_class"])
    parts = [
        declaration["declarer"].encode(),
        declaration["counterpart"].encode(),
        le_u64(declaration["version"]),
    ]
    for posture in postures:
        parts.append(posture["data_class"].encode())
        parts.append(bytes([LEVEL_ORDINALS[posture["level"]]]))
        parts.append(posture["recognition"].encode())
        for transport in sorted(posture["transports"]):
            parts.append(transport.encode())
        parts.append((posture.get("escalation") or "").encode())
        parts.append((posture.get("reciprocity") or "").encode())
    parts.append(declaration["valid_from"].encode())
    parts.append((declaration.get("valid_to") or "").encode())
    return canonical_fields(parts)


def verify_declaration(declaration: dict, declarer_public: bytes) -> None:
    """Verify the declaration's signature: Ed25519 over the
    INTEROP-DECLARATION domain framing of the canonical bytes. The
    trust-graph reading (whose anchor this key is) belongs to the
    suite's trust service — the foreign harness verifies the
    cryptographic form."""
    slot = declaration["signature"]
    if slot.get("suite") != "ed25519":
        raise ProtocolFailure(
            f"unsupported declaration suite `{slot.get('suite')}` "
            "(the foreign subset reads ed25519)"
        )
    signature = bytes(slot["signature"])
    payload = domain_frame(
        DECLARATION_DOMAIN, declaration_canonical(declaration)
    )
    if not ed25519_verify(declarer_public, payload, signature):
        raise ProtocolFailure("the declaration's signature does not verify")


def route_replay(route: dict) -> list[dict]:
    """Replay a recorded verification route: the coverage entries
    re-derive from the Classify steps alone (the trace IS the
    report's derivation — SI-11)."""
    entries = []
    for step in route["steps"]:
        if step["step"] == "classify":
            entries.append(step["entry"])
        elif step["step"] == "gap":
            # A stated gap is part of the trace, never an entry: the
            # class it could not cover is absent from the report,
            # with the reason riding the route.
            continue
    return entries
