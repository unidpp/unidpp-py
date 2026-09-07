"""Commitment-chain mechanics: integrity, tamper detection, fork rejection,
salted blind edges, mass balance."""

import pytest

from unidpp.canonical import canonical_json, commitment, sha256_hex
from unidpp.eventlog import (
    Actor,
    AppendOnlyError,
    DomainEvent,
    append_event,
    blind_edge_commitment,
    log_head,
    mass_balance,
    verify_chain,
)
from unidpp.fixtures import build_car, build_laptop

SUBJECT = "urn:iso:std:iso-iec:15459:unidpp:inst:84120099012345"


def _stamp_event(eid: str, when: str) -> DomainEvent:
    return DomainEvent(
        event_id=eid,
        type="inspection.stamp",
        subject=SUBJECT,
        occurred_at=when,
        actor=Actor("urn:unidpp:actor:verifier-1", "verifier"),
        payload={
            "lensId": "urn:unidpp:profile:jp-meti-pse",
            "lensVersion": "2026.2",
            "mode": "live",
            "verdictSummary": "pass",
        },
        trust_marker="self-declared",
        prev_commitment="",
    )


class TestChainIntegrity:
    def test_verifies_laptop_chain(self):
        laptop = build_laptop()
        assert verify_chain(laptop.events)

    def test_car_and_battery_logs_verify(self):
        car = build_car()
        assert verify_chain(car.car["events"])
        assert verify_chain(car.battery["events"])

    def test_detects_tampering(self):
        laptop = build_laptop()
        tampered = [
            DomainEvent(
                event_id=e.event_id,
                type=e.type,
                subject=e.subject,
                occurred_at=e.occurred_at,
                actor=e.actor,
                payload=(dict(e.payload) if i != 2 else {**e.payload, "conveyance": "gift"}),
                trust_marker=e.trust_marker,
                prev_commitment=e.prev_commitment,
                commitment=e.commitment,
            )
            for i, e in enumerate(laptop.events)
        ]
        assert not verify_chain(tampered)

    def test_appends_with_stamped_chain(self):
        laptop = build_laptop()
        head = log_head(laptop.events)
        assert head["height"] == 5
        assert len(head["commitment"]) == 64
        import re

        assert re.fullmatch(r"[0-9a-f]{64}", head["commitment"])

        extended = append_event(laptop.events, _stamp_event("evt-lap-006", "2027-03-01T00:00:00Z"))
        assert verify_chain(extended)
        assert log_head(extended)["height"] == 6

    def test_rejects_conflicting_prev_commitment(self):
        laptop = build_laptop()
        bad = _stamp_event("evt-lap-007", "2027-03-01T00:00:00Z")
        bad.prev_commitment = "f" * 64
        with pytest.raises(AppendOnlyError, match="append-only"):
            append_event(laptop.events, bad)

    def test_genesis_has_empty_prev(self):
        log = append_event([], _stamp_event("e1", "2027-01-01T00:00:00Z"))
        assert log[0].prev_commitment == ""
        assert verify_chain(log)

    def test_salted_log_is_a_different_chain(self):
        log = []
        log = append_event(log, _stamp_event("e1", "2027-01-01T00:00:00Z"), salt="pepper")
        assert verify_chain(log, salt="pepper")
        assert not verify_chain(log, salt="")


class TestCommitments:
    def test_commitment_is_sha256_over_canonical_json(self):
        value = {"b": 1, "a": [True, None, "x"]}
        assert commitment(value, "s") == sha256_hex("s:" + canonical_json(value))

    def test_canonical_json_sorts_keys_and_strips_whitespace(self):
        assert canonical_json({"z": 1, "a": {"y": [1, 2]}}) == '{"a":{"y":[1,2]},"z":1}'

    def test_canonical_json_keeps_non_ascii_raw(self):
        assert canonical_json({"k": "é"}) == '{"k":"é"}'

    def test_non_finite_numbers_rejected(self):
        with pytest.raises(ValueError):
            canonical_json(float("nan"))


class TestBlindEdges:
    def test_battery_parent_commitment_is_salted(self):
        car = build_car()
        link = car.links[0]
        expected = commitment(
            {
                "parent": "urn:iso:std:iso-iec:15459:unidpp:passport:car-wvwzzz1jzxw000841",
                "slot": "traction-battery-1",
            },
            "salt-bp52-000841",
        )
        assert link.parent_commitment == expected
        # The unsalted commitment differs: no log operator can correlate.
        assert link.parent_commitment != commitment(
            {
                "parent": "urn:iso:std:iso-iec:15459:unidpp:passport:car-wvwzzz1jzxw000841",
                "slot": "traction-battery-1",
            }
        )

    def test_blind_edge_commitment_helper(self):
        c1 = blind_edge_commitment("urn:x:parent", "slot-1", "salt")
        c2 = blind_edge_commitment("urn:x:parent", "slot-1", "salt")
        c3 = blind_edge_commitment("urn:x:parent", "slot-1", "other-salt")
        assert c1 == c2 and c1 != c3


class TestMassBalance:
    def test_split_conserves_mass(self):
        result = mass_balance(
            inputs=[{"passportId": "urn:x:battery", "quantity": 53.0}],
            outputs=[
                {"passportId": "urn:x:cells", "quantity": 40.0, "unit": "kg"},
                {"passportId": "urn:x:casing", "quantity": 8.0, "unit": "kg"},
                {"passportId": "urn:x:electronics", "quantity": 5.0, "unit": "kg"},
            ],
        )
        assert result.balanced
        assert result.loss == 0.0

    def test_combine_conserves_with_loss(self):
        result = mass_balance(
            inputs=[
                {"passportId": "urn:x:cells", "quantity": 40.0, "unit": "kg"},
                {"passportId": "urn:x:casing", "quantity": 8.0, "unit": "kg"},
            ],
            outputs=[{"passportId": "urn:x:module", "quantity": 48.0, "unit": "kg"}],
        )
        assert result.balanced and result.loss == 0.0

    def test_violation_detected(self):
        result = mass_balance(
            inputs=[{"passportId": "urn:x:battery", "quantity": 53.0}],
            outputs=[{"passportId": "urn:x:gold", "quantity": 54.0, "unit": "kg"}],
        )
        assert not result.balanced
        assert result.loss < 0

    def test_mismatched_units_raise(self):
        from unidpp.model import ModelError

        with pytest.raises(ModelError):
            mass_balance(
                inputs=[{"passportId": "urn:x:a", "quantity": 1.0, "unit": "kg"}],
                outputs=[{"passportId": "urn:x:b", "quantity": 1.0, "unit": "EA"}],
            )
