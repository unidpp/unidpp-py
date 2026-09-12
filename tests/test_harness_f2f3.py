"""The foreign harness at F2 and F3 (the proof track's deferred
legs).

The framework's proof track: "class F1 after phase 2, classes F2
and F3 after phases 2 to 4." The phases that carry S13 and the
mapping discipline are done; these tests prove the two remaining
classes foreign-side, from the suite-pinned vectors and the clause
text alone:

- F2 (S13 protocol participant): a request/response exchange
  completes end to end — the verifier's signed request and the
  custodian's signed, journal-replayable response verify in the
  S13-MESSAGE domain, the outcome DERIVES from the governing
  policy (verifier membership, then the reveal class), and the
  response cites the governing policy's identifier and version.
- F3 (mapping-capable): registered mapping items flow in and out —
  tier-1 mappings transform deterministically between the parties'
  structures, tier-2 correspondences carry declared scope and
  residual, and tier-3 pairs render as distinct items with no
  correspondence asserted.

A divergence from the reference fixtures fails loudly — that is the
cross-implementation contract being proven.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from unidpp.harness import mapping, protocol, vectors
from unidpp.harness.ed25519 import verify as ed25519_verify

REPO = Path(__file__).resolve().parent.parent
CORE = Path(os.environ.get("UNIDPP_CORE", REPO.parent / "unidpp-core"))
S13_FIXTURES = CORE / "crates" / "s13" / "fixtures" / "canonical"
SEMANTICS_FIXTURES = CORE / "crates" / "semantics" / "fixtures" / "canonical"
SIGNATIF_FIXTURES = REPO / "tests" / "harness" / "canonical"


def _fixture(base: Path, name: str) -> dict:
    path = base / name
    if not path.exists():
        pytest.skip(f"fixture {path} not present (set UNIDPP_CORE)")
    return vectors.load_fixture(path)


# --- F2: the S13 protocol participant -------------------------------------


def test_f2_the_signed_exchange_verifies_end_to_end():
    fixture = _fixture(SIGNATIF_FIXTURES, "s13-signed-exchange.json")
    signed_request = fixture["signed_request"]
    signed_response = fixture["signed_response"]

    # The verifier's signed request verifies in the S13-MESSAGE
    # domain (the foreign side checks the cryptography; whose key it
    # is stays the suite's graph reading).
    protocol.verify_s13_request(
        signed_request, bytes.fromhex(fixture["requester_public_hex"])
    )

    # The custodian's signed response verifies, and it is
    # journal-replayable: the canonical bytes are a pure function of
    # the response object.
    canonical = vectors.response_canonical(signed_response["response"])
    protocol.verify_s13_response(
        signed_response, bytes.fromhex(fixture["responder_public_hex"])
    )
    assert vectors.response_canonical(
        signed_response["response"]
    ) == canonical, "the response's canonical form must be deterministic"

    # The response cites the governing policy's identifier and
    # version (the clause's citation requirement).
    policy = fixture["policy"]
    assert (
        signed_response["response"]["governing_policy"] == policy["policy_id"]
    )
    assert (
        signed_response["response"]["governing_policy_version"]
        == policy["version"]
    )


def test_f2_the_outcome_derives_from_the_governing_policy():
    fixture = _fixture(SIGNATIF_FIXTURES, "s13-signed-exchange.json")
    request = fixture["signed_request"]["request"]
    policy = fixture["policy"]
    response = fixture["signed_response"]["response"]

    # The foreign evaluation derives the same outcome — and the
    # whole response object — from the policy alone.
    derived = protocol.evaluate_s13(request, policy, response["custodian"])
    assert derived == response, (
        "the outcome must derive from the governing policy: "
        f"derived {derived} vs the suite's {response}"
    )

    # The adversarial halves: a verifier outside the policy's set is
    # denied with the reason stated; a different reveal class yields
    # its own outcome token.
    outsider = dict(request, verifier="xx-unknown-customs")
    denied = protocol.evaluate_s13(outsider, policy, "weilian-shenzhen")
    assert denied["outcome"]["outcome"] == "deny"
    assert "verifier set" in denied["outcome"]["reason"]

    open_policy = dict(policy, reveal="Open")
    assert (
        protocol.evaluate_s13(request, open_policy, "w")["outcome"]["outcome"]
        == "permit"
    )
    escrow_policy = dict(policy, reveal="Escrowed")
    escalated = protocol.evaluate_s13(request, escrow_policy, "w")
    assert escalated["outcome"]["outcome"] == "escalation"
    assert escalated["outcome"]["escrow_quorum"] == "cn-samr-escrow"


def test_f2_the_foreign_side_issues_signed_requests():
    fixture = _fixture(SIGNATIF_FIXTURES, "s13-signed-exchange.json")
    request = dict(
        fixture["signed_request"]["request"], verifier="foreign-customs"
    )
    signed, public = protocol.sign_s13_request(request, b"\x11" * 32)

    # The issued form verifies under the same domain framing the
    # suite verifies — RFC 8032 determinism is what makes a
    # foreign-issued signature acceptable to the reference
    # verifier.
    payload = vectors.request_canonical(request)
    assert ed25519_verify(
        public,
        b"UNIDPP-SIGNATIF/S13-MESSAGE" + b"\x00" + payload,
        bytes(signed["signature"]["signature"]),
    )
    # And the deterministic re-issue reproduces it byte-for-byte.
    again, public_again = protocol.sign_s13_request(request, b"\x11" * 32)
    assert again == signed and public_again == public

    # A tampered request under the same signature does not verify.
    tampered = dict(signed, request=dict(request, segment="eu-static"))
    with pytest.raises(protocol.ProtocolFailure):
        protocol.verify_s13_request(tampered, public)


# --- F3: mapping-capable ---------------------------------------------------


def test_f3_mapping_vectors_reproduce():
    fixture = _fixture(SEMANTICS_FIXTURES, "mapping-chain.json")
    chain = fixture["chain"]
    assert chain["hops"], "the chain carries its hops"

    assert (
        mapping.mapping_item_canonical(chain["hops"][0]).hex()
        == fixture["hop_a_canonical_hex"]
    )
    assert (
        mapping.mapping_item_canonical(chain["hops"][1]).hex()
        == fixture["hop_b_canonical_hex"]
    )
    assert (
        mapping.mapping_item_canonical(fixture["correspondence"]).hex()
        == fixture["correspondence_canonical_hex"]
    )
    assert (
        mapping.mapping_item_canonical(fixture["divergence"]).hex()
        == fixture["divergence_canonical_hex"]
    )
    # The chain's recorded versions: every constituent hop, in order.
    assert mapping.versions(chain) == [
        tuple(v) for v in fixture["chain_versions"]
    ]


def test_f3_tier1_transforms_deterministically_and_tiers_refuse():
    fixture = _fixture(SEMANTICS_FIXTURES, "mapping-chain.json")
    chain = fixture["chain"]

    seen = []

    def transform(value: str, reference: str) -> str:
        seen.append(reference)
        return f"{value} →[{reference.split('@')[0].rsplit(':', 1)[1]}]"

    applied = mapping.apply_deterministic(chain, "12.5 kg", transform)
    assert applied == "12.5 kg →[eu-cn-mass] →[cn-jp-mass]"
    assert seen == [
        "urn:unidpp:transform:eu-cn-mass@4",
        "urn:unidpp:transform:cn-jp-mass@1",
    ], "the transform is named by reference, applied in chain order"

    # A tier-2 correspondence inside a deterministic application is
    # refused — correspondences are not transforms.
    mixed = dict(
        chain,
        hops=chain["hops"] + [fixture["correspondence"]],
    )
    with pytest.raises(mapping.MappingFailure):
        mapping.apply_deterministic(mixed, "12.5 kg", transform)

    # Tier-3 renders distinct: the divergence record's canonical
    # bytes commit the note, and it asserts no correspondence —
    # applying it is refused the same way (it is not a transform).
    assert fixture["divergence"]["kind"]["tier"] == "no-mapping"
    with pytest.raises(mapping.MappingFailure):
        mapping.apply_deterministic(
            {"hops": [fixture["divergence"]]}, "12.5 kg", transform
        )
