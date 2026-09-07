"""Fixture semantics: as-of applicability queries, dormant identifiers,
capability classes, recall predicates, split/combine scenarios."""

from unidpp.eventlog import Actor, DomainEvent, append_event, verify_chain
from unidpp.fixtures import build_car, build_laptop


class TestLaptopFixture:
    def test_one_neutral_core_two_jurisdiction_profiles(self):
        laptop = build_laptop()
        assert {p.profile_id for p in laptop.profiles} == {
            "urn:unidpp:profile:eu-espr-electronics",
            "urn:unidpp:profile:jp-meti-pse",
        }

    def test_as_of_before_any_binding(self):
        laptop = build_laptop()
        # Before 2026-10-01 neither EU (from 2027-01-01) nor JP (from
        # 2026-10-01) is effective — the dated-applicability query is honest.
        assert laptop.manifest.profiles_at("2026-09-30T23:59:59Z") == []

    def test_as_of_jp_only(self):
        laptop = build_laptop()
        at = "2026-12-01T00:00:00Z"
        bound = laptop.manifest.profiles_at(at)
        assert [b.profile_id for b in bound] == ["urn:unidpp:profile:jp-meti-pse"]

    def test_as_of_both_profiles(self):
        laptop = build_laptop()
        at = "2027-02-11T10:44:00Z"
        bound = laptop.manifest.profiles_at(at)
        assert len(bound) == 2

    def test_dormant_child_is_first_class(self):
        laptop = build_laptop()
        dormant = [c for c in laptop.manifest.children if c.dormant]
        assert len(dormant) == 1
        assert dormant[0].child_id == "urn:unidpp:id:display-lot-d14-2026q3"
        assert dormant[0].binding.recoverability == "absorbing"

    def test_s0_capability(self):
        laptop = build_laptop()
        assert laptop.manifest.capability_class == "S0"

    def test_log_height_matches_fixture(self):
        laptop = build_laptop()
        assert laptop.manifest.event_log.height == 5


class TestCarFixture:
    def test_federation_not_mega_passport(self):
        car = build_car()
        assert car.car["manifest"].passport_id != car.battery["manifest"].passport_id
        # The car's child reference points at the battery passport by identity.
        child = car.car["manifest"].children[0]
        assert child.child_id == car.battery["manifest"].passport_id.value

    def test_battery_dormant_cell_lots(self):
        car = build_car()
        lots = [c for c in car.battery["manifest"].children if c.dormant]
        assert len(lots) == 2
        assert all(c.relationship == "derivation" for c in lots)
        assert all(c.binding.recoverability == "absorbing" for c in lots)

    def test_s2_capability_with_device_milestones(self):
        car = build_car()
        assert car.battery["manifest"].capability_class == "S2"
        milestones = [e for e in car.battery["events"] if e.type == "milestone.record"]
        assert len(milestones) == 1
        assert milestones[0].payload["freshWithin"] == "P30D"

    def test_recall_is_predicate_based(self):
        car = build_car()
        recalls = [e for e in car.battery["events"] if e.type == "recall.campaign"]
        assert recalls[0].payload["predicate"] == (
            "battery.firmware < 2.3.1 and cycle_count > 800"
        )
        assert recalls[0].trust_marker == "log-anchored"

    def test_vin_and_gs1_scheme_bridge(self):
        car = build_car()
        assert car.car["manifest"].subject_id.scheme == "vin"
        assert car.battery["manifest"].subject_id.scheme == "gs1"


class TestSplitCombineScenario:
    """E2E: battery recycling — split into material passports, then combine
    into a new module; mass balance is conserved at every step."""

    def _recycling_log(self):
        log: list[DomainEvent] = []
        log = append_event(
            log,
            DomainEvent(
                event_id="evt-rec-001",
                type="material.decompose",
                subject="urn:unidpp:subject:battery-pack-bp52-000841",
                occurred_at="2029-01-15T08:00:00Z",
                actor=Actor("urn:unidpp:actor:recycler-eu", "recycler"),
                payload={
                    "outputs": [
                        {"passportId": "urn:x:cells-40", "quantity": 40.0, "unit": "kg"},
                        {"passportId": "urn:x:casing-8", "quantity": 8.0, "unit": "kg"},
                        {"passportId": "urn:x:electronics-5", "quantity": 5.0, "unit": "kg"},
                    ],
                    "inputReferences": [
                        {
                            "passportId": "urn:unidpp:passport:battery-pack-bp52-000841",
                            "quantity": 53.0,
                            "stateHash": "a" * 64,
                        }
                    ],
                },
                trust_marker="third-party-attested",
                prev_commitment="",
            ),
        )
        log = append_event(
            log,
            DomainEvent(
                event_id="evt-rec-002",
                type="passport.created",
                subject="urn:x:module-rebuilt",
                occurred_at="2029-02-01T08:00:00Z",
                actor=Actor("urn:unidpp:actor:cellco-eu", "economic-operator"),
                payload={
                    "profileIds": [],
                    "inputReferences": [
                        {"passportId": "urn:x:cells-40", "quantity": 40.0, "stateHash": "b" * 64},
                        {"passportId": "urn:x:casing-8", "quantity": 8.0, "stateHash": "c" * 64},
                    ],
                    "outputQuantities": [
                        {"passportId": "urn:x:module-rebuilt", "quantity": 48.0, "unit": "kg"}
                    ],
                },
                trust_marker="third-party-attested",
                prev_commitment="",
            ),
        )
        return log

    def test_split_conserves(self):
        from unidpp.eventlog import mass_balance

        log = self._recycling_log()
        split = log[0]
        result = mass_balance(split.payload["inputReferences"], split.payload["outputs"])
        assert result.balanced
        assert result.inputs == 53.0 and result.outputs == 53.0

    def test_combine_conserves(self):
        from unidpp.eventlog import mass_balance

        log = self._recycling_log()
        combine = log[1]
        result = mass_balance(
            combine.payload["inputReferences"], combine.payload["outputQuantities"]
        )
        assert result.balanced and result.loss == 0.0

    def test_scenario_chain_verifies(self):
        assert verify_chain(self._recycling_log())
