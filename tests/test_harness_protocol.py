"""The foreign harness's third leg: the inter-scheme protocol
subset, against the suite's own vectors.

The second-implementation rule (the framework's proof discipline)
names three legs: the grammar (Annex B), the frozen view (F1), and
a subset of the inter-scheme protocol. The first two are proven
elsewhere in this suite; these tests prove the third, from the
suite-pinned vectors:

- a recorded verification route re-derives byte-identically
  (canonical bytes and digest) and replays its coverage entries
  from the trace alone;
- a signed interop declaration re-derives its canonical bytes, and
  the declarer's Ed25519 signature verifies over the
  INTEROP-DECLARATION domain framing — no reference code, no trust
  graph (that reading is the suite's).

Written from Annex B and the clause text alone. A divergence from
the reference fixtures fails loudly — that is the
cross-implementation contract being proven.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from unidpp.harness import protocol, vectors

REPO = Path(__file__).resolve().parent.parent
CORE = Path(os.environ.get("UNIDPP_CORE", REPO.parent / "unidpp-core"))
S13_FIXTURES = CORE / "crates" / "s13" / "fixtures" / "canonical"
SIGNATIF_FIXTURES = REPO / "tests" / "harness" / "canonical"


def _fixture(base: Path, name: str) -> dict:
    path = base / name
    if not path.exists():
        pytest.skip(f"fixture {path} not present (set UNIDPP_CORE)")
    return vectors.load_fixture(path)


def test_route_vector_reproduces():
    fixture = _fixture(S13_FIXTURES, "verification-route.json")
    route = fixture["route"]
    assert (
        vectors.route_canonical(route).hex() == fixture["canonical_hex"]
    ), "the route's canonical bytes diverged from the suite's"
    assert (
        hashlib.sha256(vectors.route_canonical(route)).hexdigest()
        == fixture["digest_hex"]
    ), "the route's digest diverged from the suite's"


def test_route_replay_re_derives_the_coverage_report():
    route = _fixture(S13_FIXTURES, "verification-route.json")["route"]
    report = _fixture(S13_FIXTURES, "coverage-report.json")["report"]
    replayed = protocol.route_replay(route)
    assert replayed == report["entries"], (
        "replaying the recorded route must re-derive the coverage "
        "report's entries exactly — the trace IS the derivation"
    )
    # The stated gaps ride the trace, never the report: the class a
    # gap names is absent from the entries.
    gapped = {s["data_class"] for s in route["steps"] if s["step"] == "gap"}
    assert gapped and gapped.isdisjoint(
        {e["class"] for e in replayed}
    ), "a gapped class must not appear as covered"


def test_declaration_vector_reproduces_and_verifies():
    fixture = _fixture(SIGNATIF_FIXTURES, "interop-declaration.json")
    declaration = fixture["declaration"]
    assert (
        protocol.declaration_canonical(declaration).hex()
        == fixture["canonical_hex"]
    ), "the declaration's canonical bytes diverged from the suite's"
    assert (
        hashlib.sha256(protocol.declaration_canonical(declaration)).hexdigest()
        == fixture["digest_hex"]
    ), "the declaration's digest diverged from the suite's"
    # The cryptographic form: the declarer's Ed25519 over the domain
    # framing — verified here without any trust graph.
    protocol.verify_declaration(
        declaration, bytes.fromhex(fixture["declarer_public_hex"])
    )


def test_declaration_signature_check_refuses_tampering():
    fixture = _fixture(SIGNATIF_FIXTURES, "interop-declaration.json")
    declaration = fixture["declaration"]
    tampered = dict(declaration)
    tampered["version"] = declaration["version"] + 1
    with pytest.raises(protocol.ProtocolFailure):
        protocol.verify_declaration(
            tampered, bytes.fromhex(fixture["declarer_public_hex"])
        )
    # A posture edit under the same signature: refused, the class
    # named by the divergence in the canonical bytes.
    edited = dict(declaration)
    edited["postures"] = [
        dict(p, level="l5") if p["data_class"] == "*" else p
        for p in declaration["postures"]
    ]
    with pytest.raises(protocol.ProtocolFailure):
        protocol.verify_declaration(
            edited, bytes.fromhex(fixture["declarer_public_hex"])
        )
