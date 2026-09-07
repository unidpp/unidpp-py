"""Verification pipeline harness (I13 degradation ladder + I9 verdicts).

Mirror of ``@unidpp/verify`` (crypto.ts + signer.ts + tierA.ts), stdlib
only: ``hashlib``/``hmac`` replace WebCrypto, and ECDSA is provided as a
deliberate *None placeholder* that reports "unsupported" per the
multi-suite degrade model (jurisdictional suites are profile-bound, not
platform-bound; a missing binding degrades the verdict, it never silently
passes). A real HMAC-SHA-256 slot ships for deterministic conformance runs
— it performs actual MAC verification, it is not a mock.
"""

from __future__ import annotations

import hmac
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from .canonical import canonical_json, from_base64, sha256_hex, to_base64
from .model import (
    CoverageReport,
    Finding,
    RevocationRecord,
    SignatureFraming,
    TierAPack,
    Verdict,
    combine_outcome,
    marker_at_least,
    outcome_for_freshness,
    signature_voided,
    validate_tier_a_pack,
)

__all__ = [
    "PublicKeyMaterial",
    "SignatureInput",
    "CryptoSlot",
    "EcdsaNoneSlot",
    "HmacSha256Slot",
    "CryptoSlots",
    "default_slots",
    "SignerKey",
    "hmac_key",
    "sign_framing",
    "signed_payload",
    "assess_freshness",
    "duration_to_ms",
    "verify_tier_a_pack",
    "now_iso",
]


# ---------------------------------------------------------------------------
# Crypto slots (crypto.ts)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PublicKeyMaterial:
    """Raw public key as carried in pre-cached trust anchors."""

    format: str  # "spki" | "opaque"
    bytes_: bytes | None = None
    material: str | None = None  # opaque anchor id


@dataclass(frozen=True)
class SignatureInput:
    suite: str
    payload: bytes
    signature: bytes
    public_key: PublicKeyMaterial


class CryptoSlot(ABC):
    """Pluggable crypto slot (I9 multi-suite).

    A slot whose ``supported`` is False is a placeholder: it advertises its
    suites so framings route to it, but every verification reports
    *unsupported* — the verdict degrades (warning), never silently passes.
    """

    supported: bool = True

    @property
    @abstractmethod
    def suites(self) -> tuple[str, ...]: ...

    @abstractmethod
    def verify(self, framing: SignatureInput) -> bool: ...

    def reason(self) -> str | None:
        return None


class EcdsaNoneSlot(CryptoSlot):
    """ECDSA placeholder: no stdlib ECDSA verify exists, so report unsupported.

    Registering a real ECDSA binding (``cryptography`` package, sm2/ml-dsa
    via external bindings) is a profile decision — exactly the degrade
    model: no crypto slot for the suite ⇒ warning + degraded verdict.
    """

    supported = False

    @property
    def suites(self) -> tuple[str, ...]:
        return ("ecdsa-p256-sha256", "ecdsa-p384-sha384")

    def verify(self, framing: SignatureInput) -> bool:
        return False

    def reason(self) -> str | None:
        return (
            "ECDSA verification not linked in the stdlib-only core; "
            "register a profile-bound suite binding"
        )


class HmacSha256Slot(CryptoSlot):
    """HMAC-SHA-256 slot for tests and deterministic conformance runs.

    A real symmetric verifier demonstrating slot pluggability — the anchor
    material is the opaque key id; this slot holds the matching secret and
    performs an actual MAC comparison.
    """

    def __init__(self, keys: Mapping[str, bytes]):
        self._keys = dict(keys)

    @property
    def suites(self) -> tuple[str, ...]:
        return ("testmac-sha256",)

    def verify(self, framing: SignatureInput) -> bool:
        if framing.suite not in self.suites:
            return False
        if framing.public_key.format != "opaque":
            return False
        secret = self._keys.get(framing.public_key.material or "")
        if secret is None:
            return False
        mac = hmac.new(secret, framing.payload, "sha256").digest()
        return hmac.compare_digest(mac, framing.signature)


class CryptoSlots:
    """Slot registry: profile acceptance policies check ``suits(suite)``."""

    def __init__(self) -> None:
        self._slots: dict[str, CryptoSlot] = {}

    def register(self, slot: CryptoSlot) -> None:
        for suite in slot.suites:
            self._slots[suite] = slot

    def suits(self, suite: str) -> bool:
        return suite in self._slots

    def get(self, suite: str) -> CryptoSlot | None:
        return self._slots.get(suite)


def default_slots() -> CryptoSlots:
    """Default registry: ECDSA placeholder only — degrades, never fakes."""
    slots = CryptoSlots()
    slots.register(EcdsaNoneSlot())
    return slots


# ---------------------------------------------------------------------------
# Signers (signer.ts)
# ---------------------------------------------------------------------------


@dataclass
class SignerKey:
    suite: str
    _sign: Any  # callable[[bytes], bytes]
    _anchor: PublicKeyMaterial

    def to_anchor(self) -> PublicKeyMaterial:
        return self._anchor

    def sign(self, data: bytes) -> bytes:
        return self._sign(data)


def hmac_key(secret: bytes, material: str, suite: str = "testmac-sha256") -> SignerKey:
    """Deterministic HMAC-SHA-256 signer (tests + conformance runs)."""

    def sign(data: bytes) -> bytes:
        return hmac.new(secret, data, "sha256").digest()

    return SignerKey(suite=suite, _sign=sign, _anchor=PublicKeyMaterial("opaque", material=material))


def sign_framing(payload: bytes, key: SignerKey, key_id: str, signed_at: str) -> SignatureFraming:
    value = key.sign(payload)
    return SignatureFraming(
        suite=key.suite, key_id=key_id, signed_at=signed_at, value=to_base64(value)
    )


def signed_payload(pack: TierAPack | Mapping[str, Any]) -> bytes:
    """The signed payload: canonical pack with the signature set removed.

    Framings sign the bare pack, so any number of framings (multi-suite
    co-signature model) cover byte-identical content.
    """
    bare = dict(pack.to_dict() if isinstance(pack, TierAPack) else pack)
    bare["signatures"] = []
    return canonical_json(bare).encode("utf-8")


# ---------------------------------------------------------------------------
# Freshness (tierA.ts)
# ---------------------------------------------------------------------------

_DURATION_MS_RE = re.compile(
    r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?)?$"
)


def duration_to_ms(duration: str) -> float:
    m = _DURATION_MS_RE.match(duration or "")
    if m is None:
        return float("nan")
    days = float(m.group(1) or 0)
    hours = float(m.group(2) or 0)
    minutes = float(m.group(3) or 0)
    seconds = float(m.group(4) or 0)
    return ((days * 24 + hours) * 60 + minutes) * 60 * 1000 + seconds * 1000


def _parse_iso(ts: str) -> float | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return None


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def assess_freshness(as_of: str, required: str | None, now: str) -> str:
    """Freshness of the pack's log commitment relative to ``now``."""
    if required is None:
        return "unknown"
    t_now, t_as_of = _parse_iso(now), _parse_iso(as_of)
    if t_now is None or t_as_of is None:
        return "unknown"
    age_ms = (t_now - t_as_of) * 1000
    budget_ms = duration_to_ms(required)
    if budget_ms != budget_ms:  # NaN
        return "unknown"
    return "fresh" if age_ms <= budget_ms else "stale"


# ---------------------------------------------------------------------------
# The Tier-A verification pipeline (tierA.ts)
# ---------------------------------------------------------------------------


@dataclass
class VerifyOptions:
    anchors: dict[str, PublicKeyMaterial]
    slots: CryptoSlots | None = None
    reading: str = "current-state"
    revocations: list[RevocationRecord] = field(default_factory=list)
    tainted_passport_ids: list[str] = field(default_factory=list)
    required_freshness: str | None = None
    minimum_marker: str = "unsigned"
    now: str | None = None


def verify_tier_a_pack(pack: Any, options: VerifyOptions) -> Verdict:
    """Validate a pack's framings against pre-cached trust anchors, check
    validity/freshness, apply revocation semantics per verification reading,
    and produce a verdict with a coverage report. Stale/offline data
    degrades explicitly — never silently passes."""
    now = options.now or now_iso()
    reading = options.reading
    slots = options.slots or default_slots()
    findings: list[Finding] = []

    schema = validate_tier_a_pack(pack)
    if not schema.valid:
        return Verdict(
            reading=reading,
            outcome="fail",
            freshness="unknown",
            coverage=CoverageReport(1, 0),
            findings=[
                Finding("error", "schema", f"{i.path}: {i.message}")
                for i in schema.issues
            ],
            as_of=now,
            achieved_marker="unsigned",
        )

    typed = pack if isinstance(pack, TierAPack) else _coerce_pack(pack)
    payload = signed_payload(typed)

    outcomes: list[str] = []
    passed = 1  # schema check
    checks = 1
    verified = 0
    failed = 0
    unsupported = 0
    anchored_keys = 0
    strongest = "unsigned"

    # Taint is a graph event: fails under every reading.
    if typed.passport_id.value in options.tainted_passport_ids:
        findings.append(
            Finding(
                "error",
                "tainted",
                f"passport {typed.passport_id.value} is tainted",
            )
        )
        outcomes.append("fail")

    # Validity window.
    checks += 1
    if now < typed.validity.not_before or now > typed.validity.not_after:
        findings.append(
            Finding(
                "error",
                "validity-window",
                f"pack outside validity window [{typed.validity.not_before}, {typed.validity.not_after}]",
            )
        )
        outcomes.append("fail")
    else:
        passed += 1

    # Critical safety flag cannot silently degrade: recall packs fail when stale.
    freshness = assess_freshness(
        typed.log_commitment.as_of, options.required_freshness, now
    )
    if typed.critical_safety.recall and freshness == "stale":
        findings.append(
            Finding(
                "error",
                "recall-stale",
                "recall flag present but data is stale — cannot pass",
            )
        )
        outcomes.append("fail")
    outcomes.append(outcome_for_freshness(freshness))
    checks += 1
    if freshness == "fresh":
        passed += 1

    # Signature framings.
    for framing in typed.signatures:
        slot = slots.get(framing.suite)
        key = options.anchors.get(framing.key_id)
        if slot is None:
            unsupported += 1
            findings.append(
                Finding(
                    "warning",
                    "suite-unsupported",
                    f"no crypto slot for suite {framing.suite} (profile-bound suite; register the binding)",
                )
            )
            outcomes.append("degraded")
            continue
        if slot is not None and slot.supported is False:
            unsupported += 1
            reason = slot.reason() or "slot reports unsupported"
            findings.append(
                Finding(
                    "warning",
                    "suite-unsupported",
                    f"suite {framing.suite} unsupported: {reason}",
                )
            )
            outcomes.append("degraded")
            continue
        if key is None:
            failed += 1
            findings.append(
                Finding(
                    "error",
                    "key-unanchored",
                    f"keyId {framing.key_id} not in cached trust anchors",
                )
            )
            outcomes.append("fail")
            continue
        anchored_keys += 1
        checks += 1
        # Revocation semantics per reading.
        voided = any(
            rec.key_id == framing.key_id
            and signature_voided(rec, framing.signed_at, reading)
            for rec in options.revocations
        )
        if voided:
            failed += 1
            findings.append(
                Finding(
                    "error",
                    "signature-voided",
                    f"signature by {framing.key_id} voided under {reading} reading",
                )
            )
            outcomes.append("fail")
            continue
        ok = slot.verify(
            SignatureInput(
                suite=framing.suite,
                payload=payload,
                signature=from_base64(framing.value),
                public_key=key,
            )
        )
        if ok:
            verified += 1
            passed += 1
            marker = "self-declared" if "testmac" in framing.suite else "third-party-attested"
            if strongest == "unsigned" or marker_at_least(marker, strongest):
                strongest = marker
        else:
            failed += 1
            findings.append(
                Finding(
                    "error",
                    "signature-invalid",
                    f"signature by {framing.key_id} ({framing.suite}) failed verification",
                )
            )
            outcomes.append("fail")

    minimum = options.minimum_marker
    trust_coverage = 1 if minimum == "unsigned" else (1 if marker_at_least(strongest, minimum) else 0)
    if trust_coverage == 0:
        findings.append(
            Finding(
                "warning",
                "below-minimum-marker",
                f"achieved {strongest}, below required {minimum}",
            )
        )

    coverage = CoverageReport(
        checks=checks,
        passed=passed,
        signatures_total=len(typed.signatures),
        signatures_verified=verified,
        signatures_failed=failed,
        signatures_unsupported=unsupported,
        anchor_coverage=0 if len(typed.signatures) == 0 else anchored_keys / len(typed.signatures),
        trust_coverage=trust_coverage,
    )

    return Verdict(
        reading=reading,
        outcome=combine_outcome(outcomes),
        freshness=freshness,
        coverage=coverage,
        findings=findings,
        as_of=now,
        achieved_marker=strongest,
    )


def _coerce_pack(pack: Mapping[str, Any]) -> TierAPack:
    from .model import (
        CriticalSafety,
        LogCommitment,
        ProductIdentifier,
        TierAProfileRef,
        Validity,
    )

    def pid(d: Mapping[str, Any]) -> ProductIdentifier:
        return ProductIdentifier(d["scheme"], d["value"], d["granularity"], d["state"])

    cs = pack["criticalSafety"]
    lc = pack["logCommitment"]
    return TierAPack(
        subject_id=pid(pack["subjectId"]),
        passport_id=pid(pack["passportId"]),
        resolver_uri=pack["resolverUri"],
        operator_id=pack["operatorId"],
        status=pack["status"],
        critical_safety=CriticalSafety(cs.get("recall", False), cs.get("campaignRef")),
        validity=Validity(pack["validity"]["notBefore"], pack["validity"]["notAfter"]),
        profiles=[TierAProfileRef(p["profileId"], p["version"]) for p in pack["profiles"]],
        log_commitment=LogCommitment(lc["commitment"], lc["height"], lc["asOf"]),
        signatures=[
            SignatureFraming(s["suite"], s["keyId"], s["signedAt"], s["value"])
            for s in pack["signatures"]
        ],
        kind=pack.get("kind", "unidpp.tier-a"),
        version=pack.get("version", "1"),
    )
