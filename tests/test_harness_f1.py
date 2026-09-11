"""FW-2: the F1 claim test, run by the foreign harness against a
suite-published frozen view (suite-foreign interop; suite-suite
proves nothing about the specification).
"""

from __future__ import annotations

import json
from pathlib import Path

from unidpp.harness import f1

HERE = Path(__file__).parent / "harness" / "canonical"


def _load(name: str):
    path = HERE / name
    if not path.exists():
        raise AssertionError(f"missing harness artifact: {path}")
    return json.loads(path.read_text())


def test_f1_foreign_verification_of_a_suite_frozen_view():
    counts = f1.verify_f1(_load("battery-frozen-view.json"), _load("battery-anchors.json"))
    assert counts["policies"] == 2
    assert counts["proofs"] == 2
    assert counts["attestations"] == 1
    assert counts["journal"] == 2


def test_f1_tampering_fails_loudly():
    view = _load("battery-frozen-view.json")
    anchors = _load("battery-anchors.json")
    # A swapped input byte breaks the spine commitment binding.
    tampered = json.loads(json.dumps(view))
    tampered["inputs"][0]["bytes"][0] ^= 1
    try:
        f1.verify_f1(tampered, anchors)
        raise AssertionError("tampered input accepted")
    except f1.Failure as reason:
        assert "spine commitment" in str(reason)
    # A forged payload breaks the lens re-execution.
    tampered = json.loads(json.dumps(view))
    tampered["payload"] = list(b"battery-view: cell_model=FORGED, conformity=pass")
    try:
        f1.verify_f1(tampered, anchors)
        raise AssertionError("forged payload accepted")
    except f1.Failure as reason:
        assert "re-execution" in str(reason)
    # An unpinned anchor is stated, never silently ignored.
    wrong_anchors = {"someone-else": {"suite": "ed25519", "public_hex": "00" * 32}}
    try:
        f1.verify_f1(view, wrong_anchors)
        raise AssertionError("unpinned anchor accepted")
    except f1.Failure as reason:
        assert "not pinned" in str(reason)
