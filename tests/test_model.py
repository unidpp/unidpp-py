"""Model semantics: identifiers, trust markers, revocation readings,
capability classes, visibility, traversal, schemas."""

import pytest

from unidpp import model as M
from unidpp.fixtures import build_car, build_laptop

ID = {
    "scheme": "iso-15459",
    "value": "urn:iso:std:iso-iec:15459:unidpp:inst:1",
    "granularity": "item",
    "state": "live",
}


class TestIdentifier:
    def test_accepts_well_formed_identifier(self):
        assert M.validate_identifier(ID).valid

    def test_rejects_bad_state(self):
        assert not M.validate_identifier({**ID, "state": "zombie"}).valid

    def test_rejects_empty_value(self):
        assert not M.validate_identifier({**ID, "value": ""}).valid

    def test_dormant_is_first_class(self):
        pid = M.ProductIdentifier(scheme="gs1", value="(01)0", granularity="lot", state="dormant")
        assert M.same_identity(pid, M.ProductIdentifier("gs1", "(01)0", "item", "live"))

    def test_construction_validates_granularity(self):
        with pytest.raises(M.ModelError):
            M.ProductIdentifier(scheme="gs1", value="x", granularity="pallet", state="live")


class TestTrustMarkers:
    def test_orders_trust_markers(self):
        assert M.marker_at_least("third-party-attested", "self-declared")
        assert not M.marker_at_least("self-declared", "log-anchored")

    def test_signature_voided_prospective_protects_evidentiary(self):
        prospective = M.RevocationRecord(
            key_id="k1",
            reason="key-compromise",
            declared_at="2027-01-10T00:00:00Z",
            window_start="2027-01-10T00:00:00Z",
        )
        # Signed before the compromise was declared: evidentiary protects it.
        assert not M.signature_voided(prospective, "2026-12-01T00:00:00Z", "evidentiary")
        assert not M.signature_voided(prospective, "2026-12-01T00:00:00Z", "current-state")
        assert M.signature_voided(prospective, "2027-02-01T00:00:00Z", "current-state")
        assert not M.signature_voided(prospective, "2027-02-01T00:00:00Z", "cryptographic")

    def test_signature_voided_fraud_ab_initio(self):
        retroactive = M.RevocationRecord(
            key_id="k1",
            reason="fraudulent-issuance",
            declared_at="2027-01-10T00:00:00Z",
            window_start="2026-01-01T00:00:00Z",
        )
        # Fraud voids ab initio: current-state voids even old signatures.
        assert M.signature_voided(retroactive, "2026-06-01T00:00:00Z", "current-state")
        # Evidentiary protects the diligent verifier who signed pre-declaration.
        assert not M.signature_voided(retroactive, "2026-06-01T00:00:00Z", "evidentiary")
        assert M.signature_voided(retroactive, "2027-02-01T00:00:00Z", "evidentiary")
        assert not M.signature_voided(retroactive, "2026-06-01T00:00:00Z", "cryptographic")


class TestCapabilityClasses:
    def test_s0_is_testimony_only(self):
        assert M.CLASS_CAPABILITY["S0"].truth_modes == ["attest-sampled"]
        assert not M.freshness_satisfiable("PT1H", "S0")
        assert M.freshness_satisfiable("unknown", "S0")
        assert M.freshness_satisfiable("PT1H", "S3")
        assert M.freshness_satisfiable("P7D", "S2")

    def test_class_table(self):
        assert M.CLASS_CAPABILITY["S2"].max_freshness == "P365D"
        assert M.CLASS_CAPABILITY["S3"].max_freshness == "PT1H"
        assert M.CLASS_CAPABILITY["S3"].truth_modes[-1] == "both-with-precedence"

    def test_compare_durations(self):
        assert M.compare_durations("PT1H", "PT30M") == 1
        assert M.compare_durations("P1D", "PT24H") == 0
        assert M.compare_durations("P365D", "P400D") == -1

    def test_bad_duration_raises(self):
        with pytest.raises(M.ModelError):
            M.parse_duration("one hour")


class TestRelationships:
    def test_visibility_classes_gate_audiences(self):
        blind = M.PassportLink(
            type="installation",
            from_="urn:x:child",
            to="urn:x:parent",
            direction="up",
            interval_from="2026-01-01T00:00:00Z",
            visibility=M.VisibilityClause("blind"),
        )
        restricted = M.PassportLink(
            type="association",
            from_="urn:x:a",
            to="urn:x:b",
            direction="symmetric",
            interval_from="2026-01-01T00:00:00Z",
            visibility=M.VisibilityClause("restricted", audiences=["repairer"]),
        )
        assert not M.is_visible_to(blind, "repairer")
        assert M.is_visible_to(restricted, "repairer")
        assert not M.is_visible_to(restricted, "consumer")

    def test_downstream_traversal_covers_recall_routing(self):
        car = build_car()
        down = M.downstream_of(
            car.links,
            "urn:iso:std:iso-iec:15459:unidpp:passport:car-wvwzzz1jzxw000841",
        )
        assert "urn:iso:std:iso-iec:15459:unidpp:passport:battery-pack-bp52-000841" in down

    def test_r5_is_not_an_edge_type(self):
        assert "profile-of" not in M.RELATIONSHIP_TYPES
        assert set(M.RELATIONSHIP_TYPES) == {
            "association",
            "derivation",
            "installation",
            "type-lineage",
            "custody",
            "membership",
        }


class TestSchemas:
    def test_laptop_manifest_validates(self):
        laptop = build_laptop()
        assert M.validate_manifest(laptop.manifest).valid

    def test_car_manifests_validate_parent_and_battery_child(self):
        car = build_car()
        assert M.validate_manifest(car.car["manifest"]).valid
        assert M.validate_manifest(car.battery["manifest"]).valid
        for link in car.links:
            assert M.validate_link(link).valid

    def test_events_validate_against_event_schema(self):
        laptop = build_laptop()
        for event in laptop.events:
            assert M.validate_event(event).valid

    def test_rejects_manifest_with_bad_commitment_pattern(self):
        laptop = build_laptop()
        broken = laptop.manifest.to_dict()
        broken["eventLog"]["commitment"] = "not-a-hash"
        result = M.validate_manifest(broken)
        assert not result.valid
        assert any(i.keyword == "pattern" for i in result.issues)

    def test_validates_a_tier_a_pack(self):
        pack = {
            "kind": "unidpp.tier-a",
            "version": "1",
            "subjectId": ID,
            "passportId": ID,
            "resolverUri": "https://resolver.unidpp.org/",
            "operatorId": "urn:unidpp:actor:oem-nordwave",
            "status": "active",
            "criticalSafety": {"recall": False},
            "validity": {
                "notBefore": "2026-01-01T00:00:00Z",
                "notAfter": "2036-01-01T00:00:00Z",
            },
            "profiles": [
                {"profileId": "urn:unidpp:profile:eu-espr-electronics", "version": "1.3.0"}
            ],
            "logCommitment": {
                "commitment": "a" * 64,
                "height": 3,
                "asOf": "2026-08-03T09:15:00Z",
            },
            "signatures": [
                {
                    "suite": "ecdsa-p256-sha256",
                    "keyId": "k1",
                    "signedAt": "2026-08-03T09:15:00Z",
                    "value": "AA==",
                }
            ],
        }
        assert M.validate_tier_a_pack(pack).valid

    def test_rejects_tier_a_pack_with_no_signatures(self):
        pack = {
            "kind": "unidpp.tier-a",
            "version": "1",
            "subjectId": ID,
            "passportId": ID,
            "resolverUri": "https://resolver.unidpp.org/",
            "operatorId": "urn:unidpp:actor:oem",
            "status": "active",
            "criticalSafety": {"recall": False},
            "validity": {
                "notBefore": "2026-01-01T00:00:00Z",
                "notAfter": "2036-01-01T00:00:00Z",
            },
            "profiles": [{"profileId": "urn:p", "version": "1"}],
            "logCommitment": {"commitment": "a" * 64, "height": 3, "asOf": "2026-08-03T09:15:00Z"},
            "signatures": [],
        }
        assert not M.validate_tier_a_pack(pack).valid


class TestVerdictSemantics:
    def test_outcome_for_freshness(self):
        assert M.outcome_for_freshness("fresh") == "pass"
        assert M.outcome_for_freshness("stale") == "degraded"
        assert M.outcome_for_freshness("unknown") == "pass"

    def test_combine_outcome(self):
        assert M.combine_outcome(["pass", "degraded"]) == "degraded"
        assert M.combine_outcome(["pass", "fail"]) == "fail"
        assert M.combine_outcome([]) == "pass"

    def test_coverage_ratio(self):
        r = M.CoverageReport(checks=4, passed=3)
        assert M.coverage_ratio(r) == 0.75
        assert M.coverage_ratio(M.CoverageReport()) == 1


class TestCarrierBudgets:
    def test_fits_carrier_unknown_raises(self):
        laptop = build_laptop()
        with pytest.raises(M.ModelError):
            from unidpp.model import fits_carrier

            fits_carrier(object(), "qr-hologram")
