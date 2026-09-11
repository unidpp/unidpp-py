"""The F1 claim test, run by a foreign verifier (FW-2).

Verifies a suite-published frozen view under the verifier's OWN
pinned anchors, entirely offline: every signature in the bundle is
checked (Ed25519, RFC 8032), every input matches its spine
commitment, inclusion proofs verify against the spine root, and the
lens re-execution reproduces the issuer-side payload
byte-identically.

Usage: python -m unidpp.harness.f1 <frozen-view.json> <anchors.json>
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from . import vectors
from .ed25519 import verify as ed25519_verify

SEGMENT_POLICY = b"UNIDPP-SIGNATIF/SEGMENT-POLICY"
SPINE_ROOT = b"UNIDPP-SIGNATIF/SPINE-ROOT"
SOVEREIGN = b"UNIDPP-SIGNATIF/SOVEREIGN-ATTESTATION"
QUORUM = b"UNIDPP-SIGNATIF/QUORUM"
S13_MESSAGE = b"UNIDPP-SIGNATIF/S13-MESSAGE"
SUITE_CODE = {"ed25519": 6}


class Failure(Exception):
    pass


def _key_id(public: bytes, suite: str = "ed25519") -> str:
    digest = hashlib.sha256(bytes([SUITE_CODE[suite]]) + public).hexdigest()
    return "k-" + digest[:16]


def _anchor_for(anchors: dict, node: str, key_id: str) -> bytes:
    entry = anchors.get(node)
    if entry is None:
        raise Failure(f"anchor for node `{node}` is not pinned by this verifier")
    public = bytes.fromhex(entry["public_hex"])
    if _key_id(public, entry.get("suite", "ed25519")) != key_id:
        raise Failure(f"key id mismatch for node `{node}`")
    return public


def _check_sig(public: bytes, domain: bytes, payload: bytes, signature) -> None:
    sig = bytes(signature)
    if not ed25519_verify(public, domain + b"\x00" + payload, sig):
        raise Failure("signature does not verify")


def verify_f1(view: dict, anchors: dict) -> dict:
    """The F1 claim: the view verifies air-gapped under the pinned
    anchors. Raises Failure with the reason otherwise."""
    bundle = view["bundle"]

    for policy in bundle["policies"]:
        canonical = vectors.policy_canonical(policy["policy"])
        public = _anchor_for(anchors, policy["policy"]["authority"], policy["signature"]["key_id"])
        _check_sig(public, SEGMENT_POLICY, canonical, policy["signature"]["signature"])

    spine = bundle["spine"]["spine"]
    root = vectors.spine_root(spine["commitments"])
    if root != tuple(spine["root"]) and root != bytes(spine["root"]):
        raise Failure("spine root does not re-derive from its commitments")
    public = _anchor_for(
        anchors, bundle["spine"]["custodian"], bundle["spine"]["signature"]["key_id"]
    )
    _check_sig(public, SPINE_ROOT, vectors.spine_digest(spine["version"], spine["commitments"]),
               bundle["spine"]["signature"]["signature"])

    for proof in bundle["proofs"]:
        if not vectors.proof_verifies(proof, bytes(spine["root"])):
            raise Failure(f"inclusion proof for `{proof['segment_id']}` fails the root")

    for attestation in bundle["attestations"]:
        statement = attestation["statement"]
        canonical = vectors.statement_canonical(statement)
        public = _anchor_for(anchors, attestation["service"], attestation["signature"]["key_id"])
        _check_sig(public, SOVEREIGN, canonical, attestation["signature"]["signature"])
        quorum = attestation.get("quorum")
        if quorum is not None:
            body = vectors.canonical_fields([quorum["quorum"].encode()])
            body += vectors.le_u32(quorum["threshold"]) + canonical
            for member in quorum["signatures"]:
                public = _member_public(anchors, member["key_id"])
                _check_sig(public, QUORUM, body, member["signature"])

    for entry in bundle["journal"]["entries"]:
        if "request" in entry:
            signed = entry["request"]
            public = _anchor_for(anchors, signed["requester"], signed["signature"]["key_id"])
            _check_sig(public, S13_MESSAGE, vectors.request_canonical(signed["request"]),
                       signed["signature"]["signature"])
        elif "response" in entry:
            signed = entry["response"]
            public = _anchor_for(
                anchors, signed["response"]["custodian"], signed["signature"]["key_id"]
            )
            _check_sig(public, S13_MESSAGE, vectors.response_canonical(signed["response"]),
                       signed["signature"]["signature"])

    for i in view["inputs"]:
        commitment = vectors.commit_state(bytes(i["bytes"]))
        expected = vectors.as_bytes(spine["commitments"][i["segment"]])
        if commitment != expected:
            raise Failure(f"input `{i['name']}` does not match its spine commitment")

    if vectors.battery_lens(view["inputs"]) != bytes(view["payload"]):
        raise Failure("lens re-execution does not reproduce the issuer-side payload")

    return {
        "policies": len(bundle["policies"]),
        "proofs": len(bundle["proofs"]),
        "attestations": len(bundle["attestations"]),
        "journal": len(bundle["journal"]["entries"]),
    }


def _member_public(anchors: dict, key_id: str) -> bytes:
    for node, entry in anchors.items():
        public = bytes.fromhex(entry["public_hex"])
        if _key_id(public, entry.get("suite", "ed25519")) == key_id:
            return public
    raise Failure(f"quorum member key {key_id} is not pinned by this verifier")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python -m unidpp.harness.f1 <frozen-view.json> <anchors.json>", file=sys.stderr)
        return 2
    view = json.loads(Path(argv[1]).read_text())
    anchors = json.loads(Path(argv[2]).read_text())
    try:
        counts = verify_f1(view, anchors)
    except Failure as reason:
        print(f"F1: FAIL — {reason}")
        return 1
    print(f"F1: PASS — frozen view verified air-gapped by a foreign implementation")
    print(
        f"     policies {counts['policies']} · proofs {counts['proofs']} · "
        f"attestations {counts['attestations']} · journal entries {counts['journal']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
