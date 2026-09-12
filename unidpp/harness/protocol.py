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

import hashlib

from .ed25519 import verify as ed25519_verify
from .framing import canonical_fields, domain_frame, le_u64

from . import vectors

DECLARATION_DOMAIN = b"UNIDPP-SIGNATIF/INTEROP-DECLARATION"
S13_MESSAGE_DOMAIN = b"UNIDPP-SIGNATIF/S13-MESSAGE"

# The reveal-class to outcome mapping (the S13 clause's core rule):
# a verifier in the policy's verifier set is answered per the
# segment's reveal class; anything else is a stated denial.
REVEAL_OUTCOMES = {
    "Open": ("permit", lambda policy, req: []),
    "PairingGated": ("permit-paired", lambda policy, req: [req["verifier"]]),
    "OriginSealed": (
        "attestation-offer",
        lambda policy, req: [f"{policy['authority']}-attestation"],
    ),
    "Escrowed": (
        "escalation",
        lambda policy, req: [f"{policy['authority']}-escrow"],
    ),
}

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

def _verify_slot(slot: dict, domain: bytes, payload: bytes, public: bytes, what: str) -> None:
    if slot.get("suite") != "ed25519":
        raise ProtocolFailure(
            f"unsupported {what} suite `{slot.get('suite')}` "
            "(the foreign subset reads ed25519)"
        )
    if not ed25519_verify(public, domain_frame(domain, payload), bytes(slot["signature"])):
        raise ProtocolFailure(f"the {what}'s signature does not verify")


def evaluate_s13(request: dict, policy: dict, custodian: str) -> dict:
    """The S13 policy evaluation, ported from the clause: the
    outcome derives from the governing policy (verifier membership,
    then the reveal class), the response cites the policy's id and
    version, and the request's digest binds the answer to its
    question."""
    allowed = (
        request["verifier"] in policy["verifiers"]
        or "any-verifier" in policy["verifiers"]
    )
    if not allowed:
        outcome = {
            "outcome": "deny",
            "reason": (
                f"verifier `{request['verifier']}` is not in policy "
                f"`{policy['policy_id']}`'s verifier set"
            ),
        }
    else:
        token, payload_of = REVEAL_OUTCOMES[policy["reveal"]]
        fields = payload_of(policy, request)
        outcome = {"outcome": token}
        if fields:
            key = {
                "permit-paired": "paired_with",
                "attestation-offer": "attestation_service",
                "escalation": "escrow_quorum",
            }[token]
            outcome[key] = fields[0]
    return {
        "request_digest": list(
            hashlib.sha256(vectors.request_canonical(request)).digest()
        ),
        "outcome": outcome,
        "governing_policy": policy["policy_id"],
        "governing_policy_version": policy["version"],
        "custodian": custodian,
    }


def verify_s13_request(signed_request: dict, requester_public: bytes) -> None:
    """Verify the verifier's signed request in the S13-MESSAGE
    domain (the graph reading — whose key this is — stays the
    suite's)."""
    _verify_slot(
        signed_request["signature"],
        S13_MESSAGE_DOMAIN,
        vectors.request_canonical(signed_request["request"]),
        requester_public,
        "S13 request",
    )


def verify_s13_response(signed_response: dict, responder_public: bytes) -> None:
    """Verify the custodian's signed response in the S13-MESSAGE
    domain."""
    _verify_slot(
        signed_response["signature"],
        S13_MESSAGE_DOMAIN,
        vectors.response_canonical(signed_response["response"]),
        responder_public,
        "S13 response",
    )


def sign_s13_request(request: dict, seed: bytes) -> dict:
    """Issue a verifier-signed request as a foreign implementation:
    RFC 8032 Ed25519 over the S13-MESSAGE domain framing of the
    request's canonical bytes. Deterministic — the same seed and
    request reproduce the same signature, which is what makes the
    reference verifier accept it."""
    from .ed25519 import sign as ed25519_sign

    public, signature = ed25519_sign(
        seed, domain_frame(S13_MESSAGE_DOMAIN, vectors.request_canonical(request))
    )
    return {
        "request": request,
        "requester": "foreign-verifier",
        "signature": {
            "suite": "ed25519",
            "key_id": "foreign",
            "signature": list(signature),
        },
    }, public
