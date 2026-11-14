"""The Tier-A carrier codec's gates: the corpus carrier decodes to
exactly the fixture's fields, the round trip re-encodes
byte-identically, and the signing body reconstructs as the carrier's
prefix — the bytes every slot's signature covers."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from unidpp.tier_a import decode_tier_a, decode_tier_a_hex, encode_tier_a, tier_a_signing_body

REPO = Path(__file__).resolve().parent.parent
CORE = Path(os.environ.get("UNIDPP_CORE", REPO.parent / "unidpp-core"))
FIXTURE = CORE / "crates" / "tier_a" / "fixtures" / "canonical" / "pack.json"


def _fixture() -> dict:
    if not FIXTURE.exists():
        pytest.skip(f"fixture {FIXTURE} not present (set UNIDPP_CORE)")
    import json

    return json.loads(FIXTURE.read_text())


def _decoded() -> dict:
    fixture = _fixture()
    payload = decode_tier_a_hex(fixture["hex"])
    # The codec speaks snake_case dicts; the fixture's signatures
    # carry hex, ours bytes — compare the structural fields.
    for field in (
        "product_id",
        "resolver_uri",
        "passport_id",
        "eo_id",
        "status",
        "safety",
        "as_of",
    ):
        assert payload[field] == fixture["decoded"][field]
    assert payload["validity"] == fixture["decoded"]["validity"]
    assert payload["log_head"] == fixture["decoded"]["log_head"]
    expected = fixture["decoded"]["signatures"]
    assert len(payload["signatures"]) == len(expected)
    for got, want in zip(payload["signatures"], expected):
        assert got["suite"] == want["suite"]
        assert got["key_id"] == want["key_id"]
        assert got["signature"] is not None
        assert got["signature"].hex() == want["signature_hex"]
    return payload


def test_the_corpus_carrier_decodes_to_the_fixture():
    _decoded()


def test_the_round_trip_reencodes_byte_identically():
    fixture = _fixture()
    payload = decode_tier_a_hex(fixture["hex"])
    assert encode_tier_a(payload) == bytes.fromhex(fixture["hex"])


def test_the_signing_body_is_the_carriers_prefix():
    fixture = _fixture()
    carrier = bytes.fromhex(fixture["hex"])
    payload = decode_tier_a_hex(fixture["hex"])
    body = tier_a_signing_body(payload)
    # The body is exactly the re-encode with the signature block
    # emptied, the carrier carries it as its prefix, and the slots
    # follow it.
    assert body == encode_tier_a({**payload, "signatures": []})
    # The body ends with the EMPTY signature-count block (0x0B 0x00);
    # the carrier's block carries the real count in that byte, so the
    # shared prefix stops one byte short of the body's end.
    assert carrier.startswith(body[:-1])
    assert carrier[len(body) - 2] == 0x0B
    assert carrier[len(body) - 1] == len(payload["signatures"])
