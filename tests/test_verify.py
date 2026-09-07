"""Verification pipeline: readings, freshness verdicts, coverage reports,
crypto slots with the ECDSA-None degrade placeholder and a real HMAC slot."""

from unidpp.model import (
    CriticalSafety,
    LogCommitment,
    ProductIdentifier,
    RevocationRecord,
    TierAPack,
    TierAProfileRef,
    Validity,
)
from unidpp.verify import (
    CryptoSlots,
    EcdsaNoneSlot,
    HmacSha256Slot,
    PublicKeyMaterial,
    VerifyOptions,
    assess_freshness,
    default_slots,
    hmac_key,
    sign_framing,
    signed_payload,
    verify_tier_a_pack,
)

ID = ProductIdentifier("iso-15459", "urn:iso:std:iso-iec:15459:unidpp:inst:1", "item", "live")
SECRET = b"conformance-secret-0"
MATERIAL = "urn:unidpp:key:test-1"
NOW = "2027-06-01T12:00:00Z"


def _make_pack(**overrides):
    log = LogCommitment(commitment="a" * 64, height=3, as_of="2027-06-01T00:00:00Z")
    pack = TierAPack(
        subject_id=ID,
        passport_id=ID,
        resolver_uri="https://resolver.unidpp.org/",
        operator_id="urn:unidpp:actor:oem-nordwave",
        status="active",
        critical_safety=CriticalSafety(recall=False),
        validity=Validity("2026-01-01T00:00:00Z", "2036-01-01T00:00:00Z"),
        profiles=[TierAProfileRef("urn:unidpp:profile:eu-espr-electronics", "1.3.0")],
        log_commitment=log,
        signatures=[],
    )
    for k, v in overrides.items():
        setattr(pack, k, v)
    return pack


def _signed_pack(**overrides):
    pack = _make_pack()
    payload = signed_payload(pack)
    key = hmac_key(SECRET, MATERIAL)
    framing = sign_framing(payload, key, MATERIAL, "2027-05-01T00:00:00Z")
    pack.signatures = [framing]
    for k, v in overrides.items():
        setattr(pack, k, v)
    return pack


def _hmac_options(**overrides):
    opts = VerifyOptions(
        anchors={MATERIAL: PublicKeyMaterial("opaque", material=MATERIAL)},
        slots=CryptoSlots() if "slots" in overrides else None,
        now=NOW,
    )
    if "slots" not in overrides:
        slots = CryptoSlots()
        slots.register(HmacSha256Slot({MATERIAL: SECRET}))
        opts.slots = slots
    for k, v in overrides.items():
        setattr(opts, k, v)
    return opts


class TestHmacVerification:
    def test_pass_with_real_mac_verification(self):
        verdict = verify_tier_a_pack(_signed_pack(), _hmac_options(required_freshness="P30D"))
        assert verdict.outcome == "pass"
        assert verdict.freshness == "fresh"
        assert verdict.coverage.signatures_verified == 1
        assert verdict.achieved_marker == "self-declared"

    def test_tampered_payload_fails(self):
        pack = _signed_pack()
        pack.operator_id = "urn:unidpp:actor:someone-else"
        verdict = verify_tier_a_pack(pack, _hmac_options())
        assert verdict.outcome == "fail"
        assert any(f.code == "signature-invalid" for f in verdict.findings)

    def test_unanchored_key_fails(self):
        verdict = verify_tier_a_pack(_signed_pack(), _hmac_options(anchors={}))
        assert verdict.outcome == "fail"
        assert any(f.code == "key-unanchored" for f in verdict.findings)
        assert verdict.coverage.anchor_coverage == 0.0


class TestDegradeModel:
    def test_ecdsa_none_placeholder_reports_unsupported(self):
        pack = _signed_pack()
        payload = signed_payload(pack)
        key = hmac_key(SECRET, MATERIAL, suite="ecdsa-p256-sha256")
        pack.signatures = [sign_framing(payload, key, "k-ecdsa", "2027-05-01T00:00:00Z")]
        slots = CryptoSlots()
        slots.register(EcdsaNoneSlot())
        verdict = verify_tier_a_pack(
            pack,
            _hmac_options(slots=slots, anchors={"k-ecdsa": PublicKeyMaterial("spki", bytes_=b"\x04\x01")}),
        )
        # Degrade, never silently pass, never fake an ECDSA verification.
        assert verdict.outcome == "degraded"
        assert verdict.coverage.signatures_unsupported == 1
        assert any(f.code == "suite-unsupported" for f in verdict.findings)
        assert verdict.coverage.signatures_verified == 0

    def test_unregistered_suite_degrades(self):
        pack = _signed_pack()
        payload = signed_payload(pack)
        key = hmac_key(SECRET, MATERIAL, suite="ml-dsa-65")
        pack.signatures = [sign_framing(payload, key, MATERIAL, "2027-05-01T00:00:00Z")]
        verdict = verify_tier_a_pack(pack, _hmac_options())
        assert verdict.outcome == "degraded"
        assert verdict.coverage.signatures_unsupported == 1

    def test_default_slots_is_placeholder_only(self):
        slots = default_slots()
        assert slots.suits("ecdsa-p256-sha256")
        assert isinstance(slots.get("ecdsa-p256-sha256"), EcdsaNoneSlot)
        assert not slots.suits("testmac-sha256")


class TestFreshnessAndRecall:
    def test_stale_degrades(self):
        verdict = verify_tier_a_pack(
            _signed_pack(), _hmac_options(required_freshness="PT1H")
        )
        assert verdict.freshness == "stale"
        assert verdict.outcome == "degraded"

    def test_no_requirement_is_unknown_and_passes(self):
        verdict = verify_tier_a_pack(_signed_pack(), _hmac_options())
        assert verdict.freshness == "unknown"
        assert verdict.outcome == "pass"

    def test_recall_plus_stale_fails(self):
        pack = _signed_pack(critical_safety=CriticalSafety(True, "urn:eu:recall:x"))
        verdict = verify_tier_a_pack(pack, _hmac_options(required_freshness="PT1H"))
        assert verdict.outcome == "fail"
        assert any(f.code == "recall-stale" for f in verdict.findings)

    def test_assess_freshness_bounds(self):
        assert assess_freshness("2027-06-01T00:00:00Z", "P1D", NOW) == "fresh"
        assert assess_freshness("2027-05-01T00:00:00Z", "P1D", NOW) == "stale"
        assert assess_freshness("2027-05-01T00:00:00Z", None, NOW) == "unknown"
        assert assess_freshness("garbage", "P1D", NOW) == "unknown"


class TestValidityAndTaint:
    def test_outside_validity_window_fails(self):
        pack = _signed_pack(validity=Validity("2028-01-01T00:00:00Z", "2036-01-01T00:00:00Z"))
        verdict = verify_tier_a_pack(pack, _hmac_options())
        assert verdict.outcome == "fail"
        assert any(f.code == "validity-window" for f in verdict.findings)

    def test_taint_fails_every_reading(self):
        for reading in ("evidentiary", "current-state", "cryptographic"):
            verdict = verify_tier_a_pack(
                _signed_pack(),
                _hmac_options(reading=reading, tainted_passport_ids=[ID.value]),
            )
            assert verdict.outcome == "fail"
            assert any(f.code == "tainted" for f in verdict.findings)


class TestRevocationReadings:
    def _revoked(self):
        return RevocationRecord(
            key_id=MATERIAL,
            reason="fraudulent-issuance",
            declared_at="2027-05-15T00:00:00Z",
            window_start="2026-01-01T00:00:00Z",
        )

    def test_fraud_voids_current_state(self):
        verdict = verify_tier_a_pack(
            _signed_pack(),
            _hmac_options(reading="current-state", revocations=[self._revoked()]),
        )
        assert verdict.outcome == "fail"
        assert any(f.code == "signature-voided" for f in verdict.findings)

    def test_evidentiary_protects_pre_declaration_signature(self):
        # signed 2027-05-01, declared 2027-05-15: a diligent verifier passes.
        verdict = verify_tier_a_pack(
            _signed_pack(),
            _hmac_options(reading="evidentiary", revocations=[self._revoked()]),
        )
        assert verdict.outcome == "pass"

    def test_cryptographic_reading_ignores_retroactivity(self):
        verdict = verify_tier_a_pack(
            _signed_pack(),
            _hmac_options(reading="cryptographic", revocations=[self._revoked()]),
        )
        assert verdict.outcome == "pass"


class TestCoverageReport:
    def test_coverage_counts_and_minimum_marker(self):
        verdict = verify_tier_a_pack(
            _signed_pack(), _hmac_options(minimum_marker="third-party-attested")
        )
        # HMAC framings achieve self-declared only.
        assert verdict.coverage.trust_coverage == 0
        assert any(f.code == "below-minimum-marker" for f in verdict.findings)
        assert verdict.coverage.checks >= 3

    def test_schema_failure_reports_coverage_zero(self):
        pack = _signed_pack()
        broken = pack.to_dict()
        broken.pop("validity")
        verdict = verify_tier_a_pack(broken, _hmac_options())
        assert verdict.outcome == "fail"
        assert verdict.coverage.checks == 1 and verdict.coverage.passed == 0
        assert all(f.code == "schema" for f in verdict.findings)
