"""Golden-vector derivations, from Annex B alone.

Each function re-derives a fixture's canonical bytes / digests from
the fixture's own object JSON, following the field orders stated in
the specification. Any divergence from the reference fixtures fails
loudly — that is the cross-implementation contract being tested.
"""

from __future__ import annotations

import json
from pathlib import Path

from .framing import (
    SEGMENT_COMMITMENT,
    SPINE_DIGEST,
    SPINE_LEAF,
    SPINE_NODE,
    canonical_fields,
    hash_in,
    le_u32,
    le_u64,
    sha256,
    _part,
)

REVEAL_TOKENS = {
    "Open": "open",
    "PairingGated": "pairing-gated",
    "OriginSealed": "origin-sealed",
    "Escrowed": "escrowed",
}
# ClaimClass and EvidenceKind serialize kebab-case on the wire, so the
# token IS the JSON value; the maps keep the derivation explicit.
CLAIM_TOKENS = {
    "conformity": "conformity",
    "commitment-hash": "commitment-hash",
    "freshness": "freshness",
}
EVIDENCE_TOKENS = {
    "verified-direct": "verified-direct",
    "attested-by-authority": "attested-by-authority",
    "explicitly-unavailable": "explicitly-unavailable",
}


def commit_state(state: bytes) -> bytes:
    return hash_in(SEGMENT_COMMITMENT, [state])

def as_bytes(value) -> bytes:
    """Wire forms carry hashes either hex-encoded or as byte arrays;
    accept both."""
    if isinstance(value, str):
        return bytes.fromhex(value)
    return bytes(value)



def policy_canonical(policy: dict) -> bytes:
    """Per Annex B: fixed field order; role and suite lists are
    sorted, deduplicated, and joined with the unit separator
    (U+001F); optional fields absent means omitted."""
    def canon_list(values: list) -> bytes:
        return b"\x1f".join(sorted(set(v.encode() for v in values)))

    parts = [
        policy["policy_id"].encode(),
        le_u64(policy["version"]),
        policy["authority"].encode(),
        REVEAL_TOKENS[policy["reveal"]].encode(),
        policy["valid_from"].encode(),
        canon_list(policy["readers"]),
        canon_list(policy["verifiers"]),
        canon_list(policy["writers"]),
        canon_list(policy["suites"]),
    ]
    if policy.get("valid_to") is not None:
        parts.append(policy["valid_to"].encode())
    if policy.get("superseded_by") is not None:
        parts.append(le_u64(policy["superseded_by"]))
    return canonical_fields(parts)


def _hpair(l: bytes, r: bytes) -> bytes:
    return hash_in(SPINE_NODE, [min(l, r), max(l, r)])


def spine_root(commitments: dict) -> bytes:
    ids = sorted(commitments)
    level = [
        hash_in(SPINE_LEAF, [i.encode(), as_bytes(commitments[i])]) for i in ids
    ]
    if not level:
        return b"\x00" * 32
    while len(level) > 1:
        level = [
            _hpair(level[i], level[i + 1] if i + 1 < len(level) else level[i])
            for i in range(0, len(level), 2)
        ]
    return level[0]


def spine_digest(version: int, commitments: dict) -> bytes:
    buf = le_u64(version) + spine_root(commitments)
    for i in sorted(commitments):
        c = as_bytes(commitments[i])
        buf += le_u32(len(i.encode())) + i.encode() + c
    return hash_in(SPINE_DIGEST, [buf])


def proof_verifies(proof: dict, root: bytes) -> bool:
    node = hash_in(SPINE_LEAF, [proof["segment_id"].encode(), bytes(proof["commitment"])])
    for sib in proof["siblings"]:
        sib = bytes(sib)
        node = _hpair(node, sib)
    return node == root


def request_canonical(request: dict) -> bytes:
    return canonical_fields(
        [
            request["verifier"].encode(),
            request["subject"].encode(),
            request["profile"].encode(),
            request["segment"].encode(),
            request["at"].encode(),
        ]
    )


def response_canonical(response: dict) -> bytes:
    outcome = response["outcome"]
    token = outcome["outcome"]
    payload: dict = {k: v for k, v in outcome.items() if k != "outcome"}
    return canonical_fields(
        [
            bytes(response["request_digest"]),
            token.encode(),
            *[v.encode() for v in payload.values()],
            response["governing_policy"].encode(),
            le_u64(response["governing_policy_version"]),
            response["custodian"].encode(),
        ]
    )


def report_canonical(report: dict) -> bytes:
    parts = [
        report["subject"].encode(),
        report["profile"].encode(),
        report["verified_at"].encode(),
    ]
    route = report.get("route")
    parts.append(le_u64(1 if route is not None else 0))
    if route is not None:
        parts.append(route_digest(route))
    parts.append(le_u64(len(report["entries"])))
    for e in report["entries"]:
        parts.extend(
            [
                e["class"].encode(),
                e["element_set"].encode(),
                EVIDENCE_TOKENS[e["evidence"]].encode(),
                e["governing_policy"].encode(),
                le_u64(e["governing_policy_version"]),
                e["reading"].encode(),
                e["as_of"].encode(),
            ]
        )
    return canonical_fields(parts)


def route_digest(route: dict) -> bytes:
    return sha256(route_canonical(route))


def route_canonical(route: dict) -> bytes:
    parts = [le_u64(len(route["steps"]))]
    for step in route["steps"]:
        kind = step["step"]
        parts.append(kind.encode())
        if kind == "resolve":
            parts.append(step["subject"].encode())
        elif kind == "transport":
            parts.extend([step["mode"].encode(), step["counterpart"].encode()])
        elif kind == "document":
            parts.extend([step["kind"].encode(), bytes(step["digest"])])
        elif kind == "substitution":
            parts.extend(
                [step["data_class"].encode(), step["service"].encode()]
            )
        elif kind == "classify":
            e = step["entry"]
            parts.extend(
                [
                    e["class"].encode(),
                    e["element_set"].encode(),
                    EVIDENCE_TOKENS[e["evidence"]].encode(),
                    e["governing_policy"].encode(),
                    le_u64(e["governing_policy_version"]),
                    e["reading"].encode(),
                    e["as_of"].encode(),
                ]
            )
        elif kind == "gap":
            parts.extend([step["data_class"].encode(), step["reason"].encode()])
    return canonical_fields(parts)


def statement_canonical(statement: dict) -> bytes:
    return canonical_fields(
        [
            statement["segment"].encode(),
            bytes(statement["state_commitment"]),
            CLAIM_TOKENS[statement["claim"]].encode(),
            statement["value"].encode(),
            statement["as_of"].encode(),
            statement["governing_policy"].encode(),
            le_u64(statement["governing_policy_version"]),
            statement["subject"].encode(),
        ]
    )


def frozen_view_canonical(view: dict) -> bytes:
    parts = [
        view["subject"].encode(),
        descriptor_token(view["descriptor"]).encode(),
        view["lens"]["profile"].encode(),
    ]
    for step in view["lens"]["transforms"]:
        parts.extend([step["reference"].encode(), le_u64(step["version"])])
    for name, segment in view["lens"]["input_segments"]:
        parts.extend([name.encode(), segment.encode()])
    parts.append(bytes(view["payload"]))
    for i in view["inputs"]:
        parts.extend([i["name"].encode(), commit_state(bytes(i["bytes"]))])
    for instruction in view["instructions"]:
        parts.append(instruction.encode())
    parts.append(view["notarized_at"].encode())
    parts.append(spine_digest(view["bundle"]["spine"]["spine"]["version"],
                              view["bundle"]["spine"]["spine"]["commitments"]))
    return canonical_fields(parts)


def descriptor_token(descriptor: dict) -> str:
    return "·".join(
        [
            descriptor["temporal"],
            descriptor["content"],
            descriptor["derivation"],
            descriptor["exchange"],
            descriptor["granularity"],
        ]
    )


def battery_lens(inputs: list) -> bytes:
    """The registered transform ``urn:unidpp:transform:battery-view``
    v1, as implemented by a foreign verifier from its registration:
    select the cell model from the static input; the conformity
    reading rides the attestation in the bundle."""
    static = next(i for i in inputs if i["name"] == "static")
    text = bytes(static["bytes"]).decode()
    cell = next(f for f in text.split(",") if f.startswith("cell_model="))
    return f"battery-view: {cell}, conformity=pass".encode()


def load_fixture(path: Path) -> dict:
    return json.loads(path.read_text())
