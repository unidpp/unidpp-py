"""The mirrored UniDPP model: types + validation.

Semantic mirror of ``@unidpp/model`` (packages/model/src of unidpp-ts),
which itself implements ``isoiecjtc5/PLAN.md``:

- L0 identity (I1, I3): one subject, one identity, never re-minted;
  identifiers are scheme-agnostic; **dormant** identifiers are first-class
  (absorption records at finest available granularity).
- L1 neutral core + L2 profile manifest (stream 11): every regional
  requirement is a registered, versioned *profile* bound by dated
  applicability (effective windows, retroactive flags).
- Capability classes S0–S3 (the silent-object lesson).
- Relationship algebra R1–R7 with installation bindings and visibility
  classes (I5, I12): association / derivation / installation / type-lineage
  / (R5 profile-of is a lens↔core relation, not a passport edge) / custody
  / membership.
- Trust markers, multi-suite signature framings (I9, L4), the revocation
  reason taxonomy with three verification readings, and verdicts with
  coverage reports (I13).

Plain stdlib dataclasses with ``__post_init__`` validation; no pydantic.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = [
    "ACTOR_ROLES",
    "CAPABILITY_CLASSES",
    "CARRIER_BUDGETS",
    "CLASS_CAPABILITY",
    "EDGE_VISIBILITY_CLASSES",
    "EVENT_TYPES",
    "IDENTIFIER_GRANULARITIES",
    "IDENTIFIER_SCHEMES",
    "IDENTIFIER_STATES",
    "MARKER_ORDER",
    "PAIRING_MODES",
    "PASSPORT_STATUSES",
    "RECOVERABILITIES",
    "REGISTRY_ITEM_CLASSES",
    "REGISTRY_ITEM_STATUSES",
    "RELATIONSHIP_TYPES",
    "RETROACTIVE_REASONS",
    "REVOCATION_REASONS",
    "SUITES",
    "TRUST_MARKERS",
    "TRUTH_MODES",
    "VERIFICATION_READINGS",
    "CapabilityProfile",
    "ChildReference",
    "CoverageReport",
    "EffectiveWindow",
    "Finding",
    "Freshness",
    "InstallationBinding",
    "ModelError",
    "PassportLink",
    "PassportManifest",
    "ProductIdentifier",
    "ProfileAxis",
    "ProfileBinding",
    "ProfileDefinition",
    "ProfileResolution",
    "RegistryItem",
    "RegistryItemRef",
    "RevocationRecord",
    "SignatureFraming",
    "TaintRecord",
    "TierAPack",
    "TierId",
    "TriggerPredicate",
    "TrustRequirements",
    "TypeReference",
    "Verdict",
    "VerdictOutcome",
    "VisibilityClause",
    "combine_outcome",
    "compare_durations",
    "coverage_ratio",
    "downstream_of",
    "fits_carrier",
    "freshness_satisfiable",
    "identifier_equals",
    "is_visible_to",
    "item_effective_at",
    "marker_at_least",
    "outcome_for_freshness",
    "pack_size",
    "parse_duration",
    "same_identity",
    "schemas",
    "signature_voided",
    "tier_of",
    "validate_event",
    "validate_identifier",
    "validate_link",
    "validate_manifest",
    "validate_tier_a_pack",
]

Duration = str


class ModelError(ValueError):
    """Raised when a model object fails construction-time validation."""


# ---------------------------------------------------------------------------
# L0 identity (identifier.ts)
# ---------------------------------------------------------------------------

IDENTIFIER_SCHEMES = ("iso-15459", "gs1", "gbt-33993", "handle", "ecode", "ma", "vin")
#: extension point: registry-registered schemes (the wire schema keeps this open)
IDENTIFIER_GRANULARITIES = ("model", "type", "batch", "lot", "item")
IDENTIFIER_STATES = ("dormant", "live", "consumed", "retired")


def _require_str(value: Any, name: str, *, min_length: int = 1) -> str:
    if not isinstance(value, str):
        raise ModelError(f"{name} must be a string, got {type(value).__name__}")
    if len(value) < min_length:
        raise ModelError(f"{name} must not be empty")
    return value


def _require_member(value: Any, allowed: tuple[str, ...], name: str) -> str:
    if value not in allowed:
        raise ModelError(f"{name} must be one of {list(allowed)}, got {value!r}")
    return value


@dataclass
class ProductIdentifier:
    """L0 identity (I1, I3): one subject, one identity, never re-minted."""

    scheme: str
    value: str
    granularity: str
    state: str

    def __post_init__(self) -> None:
        _require_str(self.scheme, "scheme")
        _require_str(self.value, "value")
        _require_member(self.granularity, IDENTIFIER_GRANULARITIES, "granularity")
        _require_member(self.state, IDENTIFIER_STATES, "state")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TypeReference:
    """Identity lattice (PLAN.md "type-configuration lattice")."""

    type_id: ProductIdentifier
    type_version: str
    configuration_vector: list[str] | None = None

    def __post_init__(self) -> None:
        _require_str(self.type_version, "type_version")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "typeId": self.type_id.to_dict(),
            "typeVersion": self.type_version,
        }
        if self.configuration_vector is not None:
            d["configurationVector"] = list(self.configuration_vector)
        return d


def identifier_equals(a: ProductIdentifier, b: ProductIdentifier) -> bool:
    return a.scheme == b.scheme and a.value == b.value


def same_identity(a: ProductIdentifier, b: ProductIdentifier) -> bool:
    # Granularity/state may differ across records of the same minted identity.
    return identifier_equals(a, b)


# ---------------------------------------------------------------------------
# Capability classes (capability.ts)
# ---------------------------------------------------------------------------

CAPABILITY_CLASSES = ("S0", "S1", "S2", "S3")
TRUTH_MODES = ("attest-sampled", "self-committed", "both-with-precedence")

_DURATION_RE = re.compile(
    r"^(-)?P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?"
    r"(?:T(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?)?$"
)


def parse_duration(d: str) -> dict[str, float]:
    m = _DURATION_RE.match(d) if isinstance(d, str) else None
    if not m:
        raise ModelError(f"invalid ISO 8601 duration: {d!r}")
    sign = -1 if m.group(1) else 1
    return {
        "years": float(m.group(2) or 0) * sign,
        "months": float(m.group(3) or 0) * sign,
        "days": float(m.group(4) or 0) * sign,
        "hours": float(m.group(5) or 0) * sign,
        "minutes": float(m.group(6) or 0) * sign,
        "seconds": float(m.group(7) or 0) * sign,
    }


def compare_durations(a: str, b: str) -> int:
    """Lexicographic-ish ISO-8601 duration comparison (PnYnMnDTnHnMnS).

    Mirrors the TS reference exactly: years/months are parsed but excluded
    from the comparison (only days and below are compared).
    """
    pa, pb = parse_duration(a), parse_duration(b)
    sa = pa["seconds"] + pa["minutes"] * 60 + pa["hours"] * 3600 + pa["days"] * 86400
    sb = pb["seconds"] + pb["minutes"] * 60 + pb["hours"] * 3600 + pb["days"] * 86400
    return 0 if sa == sb else (-1 if sa < sb else 1)


@dataclass
class CapabilityProfile:
    capability_class: str
    max_freshness: str | None = None  # ISO 8601 duration; None = unbounded
    truth_modes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_member(self.capability_class, CAPABILITY_CLASSES, "capability_class")
        for mode in self.truth_modes:
            _require_member(mode, TRUTH_MODES, "truth_modes entry")
        if self.max_freshness is not None:
            parse_duration(self.max_freshness)


CLASS_CAPABILITY: dict[str, CapabilityProfile] = {
    "S0": CapabilityProfile("S0", None, ["attest-sampled"]),
    "S1": CapabilityProfile("S1", None, ["attest-sampled"]),
    "S2": CapabilityProfile("S2", "P365D", ["attest-sampled", "self-committed"]),
    "S3": CapabilityProfile(
        "S3", "PT1H", ["attest-sampled", "self-committed", "both-with-precedence"]
    ),
}


def freshness_satisfiable(required: str, klass: str) -> bool:
    """Is a freshness requirement satisfiable for this capability class?

    S0/S1 have no max freshness: only the literal "unknown" requirement is
    satisfiable — demanding live freshness from a silent object is an
    unsatisfiable profile.
    """
    _require_member(klass, CAPABILITY_CLASSES, "klass")
    cap = CLASS_CAPABILITY[klass]
    if cap.max_freshness is None:
        return required == "unknown"
    # A stricter (shorter) requirement than the class can deliver fails.
    return compare_durations(required, cap.max_freshness) <= 0


# ---------------------------------------------------------------------------
# Graded trust (trust.ts)
# ---------------------------------------------------------------------------

TRUST_MARKERS = (
    "unsigned",
    "self-declared",
    "third-party-attested",
    "multi-signed",
    "log-anchored",
)
MARKER_ORDER: tuple[str, ...] = TRUST_MARKERS  # weakest to strongest

SUITES = (
    "ecdsa-p256-sha256",
    "ecdsa-p384-sha384",
    "ed25519",
    "sm2-sm3",
    "ml-dsa-65",
    "testmac-sha256",
)

REVOCATION_REASONS = (
    "key-compromise",  # prospective from detection time
    "cessation",
    "supersession",
    "affiliation-change",
    "misissuance",  # retroactive: void ab initio
    "fraudulent-issuance",  # retroactive: void ab initio
    "authority-compromised",  # retroactive over the stated window
)
RETROACTIVE_REASONS = frozenset(
    {"misissuance", "fraudulent-issuance", "authority-compromised"}
)

VERIFICATION_READINGS = ("evidentiary", "current-state", "cryptographic")


def marker_at_least(marker: str, minimum: str) -> bool:
    return MARKER_ORDER.index(marker) >= MARKER_ORDER.index(minimum)


@dataclass
class SignatureFraming:
    """Multi-suite signature framing (L4): same payload, many signatures."""

    suite: str
    key_id: str
    signed_at: str  # ISO 8601 — load-bearing for evidentiary readings
    value: str  # base64 over the canonical payload

    def __post_init__(self) -> None:
        _require_str(self.suite, "suite")
        _require_str(self.key_id, "keyId")
        _require_str(self.signed_at, "signedAt")
        _require_str(self.value, "value")


@dataclass
class RevocationRecord:
    key_id: str
    reason: str
    declared_at: str
    window_start: str
    window_end: str | None = None

    def __post_init__(self) -> None:
        _require_str(self.key_id, "keyId")
        _require_member(self.reason, REVOCATION_REASONS, "reason")
        _require_str(self.declared_at, "declaredAt")
        _require_str(self.window_start, "window.start")
        if self.window_end is not None:
            _require_str(self.window_end, "window.end")

    @property
    def window(self) -> dict[str, str]:
        w = {"start": self.window_start}
        if self.window_end is not None:
            w["end"] = self.window_end
        return w

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyId": self.key_id,
            "reason": self.reason,
            "declaredAt": self.declared_at,
            "window": self.window,
        }


@dataclass
class TaintRecord:
    """Taint: marking a passport fraudulent is a graph event, not a list entry."""

    passport_id: str
    cause: str
    source_event_id: str | None = None

    def __post_init__(self) -> None:
        _require_str(self.passport_id, "passportId")
        _require_str(self.cause, "cause")


def signature_voided(rec: RevocationRecord, signed_at: str, reading: str) -> bool:
    """Is a signature made at ``signed_at`` void under this revocation record?

    Three readings (PLAN.md distrust doctrine):
    - cryptographic: ignores legal retroactivity entirely (never void here);
    - evidentiary: protects good-faith verifiers — only signatures a diligent
      verifier *should have known* were bad are void;
    - current-state: fraud voids ab initio (from the stated window start).
    """
    _require_member(reading, VERIFICATION_READINGS, "reading")
    in_window = signed_at >= rec.window_start and (
        rec.window_end is None or signed_at <= rec.window_end
    )
    if reading == "cryptographic":
        return False
    if rec.reason not in RETROACTIVE_REASONS:
        # Prospective: protects as-of-T verifications before the event.
        if reading == "evidentiary":
            return False
        return in_window
    if reading == "evidentiary":
        return signed_at >= rec.declared_at
    return in_window or signed_at >= rec.window_start


# ---------------------------------------------------------------------------
# Profile manifest (manifest.ts)
# ---------------------------------------------------------------------------

EDGE_VISIBILITY_CLASSES = ("public", "restricted", "blind", "escrowed")
RECOVERABILITIES = ("restorable", "harvestable", "destructive", "absorbing")
PAIRING_MODES = ("none", "firmware", "key", "module")
PASSPORT_STATUSES = (
    "draft",
    "active",
    "suspended",
    "non-conformant-pending-reevaluation",
    "invalid",
    "archived",
)


@dataclass
class ProfileAxis:
    jurisdiction: str | None = None
    sector: str | None = None
    characteristic: str | None = None


@dataclass
class TriggerPredicate:
    kind: str  # "regulatory" | "voluntary"
    expression: str | None = None
    time_predicate: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("regulatory", "voluntary"):
            raise ModelError(f"trigger kind must be regulatory|voluntary, got {self.kind!r}")


@dataclass
class RegistryItemRef:
    register: str
    item: str
    version: str

    def __post_init__(self) -> None:
        _require_str(self.register, "register")
        _require_str(self.item, "item")
        _require_str(self.version, "version")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrustRequirements:
    suites: list[str]
    trust_list: str
    minimum_marker: str | None = None

    def __post_init__(self) -> None:
        if not self.suites:
            raise ModelError("trust requirements need at least one suite")
        for s in self.suites:
            _require_str(s, "suites entry")
        _require_str(self.trust_list, "trustList")
        if self.minimum_marker is not None:
            _require_member(self.minimum_marker, TRUST_MARKERS, "minimumMarker")


@dataclass
class ProfileResolution:
    confidential: bool = False
    resolution: str = "public"  # none | national | restricted | public
    edge_visibility: str | None = None
    traversal: str = "public"  # none | authorityOnly | roleScoped | public

    def __post_init__(self) -> None:
        if self.resolution not in ("none", "national", "restricted", "public"):
            raise ModelError(f"bad resolution: {self.resolution!r}")
        if self.traversal not in ("none", "authorityOnly", "roleScoped", "public"):
            raise ModelError(f"bad traversal: {self.traversal!r}")
        if self.edge_visibility is not None:
            _require_member(
                self.edge_visibility, EDGE_VISIBILITY_CLASSES, "edgeVisibility"
            )


@dataclass
class EffectiveWindow:
    from_: str
    until: str | None = None
    retroactive: bool = False

    def __post_init__(self) -> None:
        _require_str(self.from_, "from")
        if self.until is not None:
            _require_str(self.until, "until")

    def contains(self, at: str) -> bool:
        """Dated applicability of this binding at instant ``at``."""
        if at < self.from_:
            return False
        return not (self.until is not None and at > self.until)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"from": self.from_}
        if self.until is not None:
            d["until"] = self.until
        if self.retroactive:
            d["retroactive"] = True
        return d


@dataclass
class ProfileDefinition:
    """A profile = registered, versioned object (FERIN/ISO 19135 item)."""

    profile_id: str
    version: str
    owner: str
    axis: ProfileAxis
    data_points: list[RegistryItemRef]
    languages: list[str]
    legal_basis: str | None = None
    trigger: TriggerPredicate | None = None
    transforms: list[RegistryItemRef] | None = None
    trust_requirements: TrustRequirements | None = None
    resolution: ProfileResolution | None = None

    def __post_init__(self) -> None:
        _require_str(self.profile_id, "profileId")
        _require_str(self.version, "version")
        _require_str(self.owner, "owner")
        if not self.languages:
            raise ModelError("profile must declare at least one language")
        for lang in self.languages:
            _require_str(lang, "languages entry")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "profileId": self.profile_id,
            "version": self.version,
            "owner": self.owner,
        }
        if self.legal_basis is not None:
            d["legalBasis"] = self.legal_basis
        d["axis"] = {
            k: v
            for k, v in (
                ("jurisdiction", self.axis.jurisdiction),
                ("sector", self.axis.sector),
                ("characteristic", self.axis.characteristic),
            )
            if v is not None
        }
        if self.trigger is not None:
            d["trigger"] = {
                "kind": self.trigger.kind,
                **({"expression": self.trigger.expression} if self.trigger.expression else {}),
                **({"timePredicate": self.trigger.time_predicate} if self.trigger.time_predicate else {}),
            }
        d["dataPoints"] = [dp.to_dict() for dp in self.data_points]
        if self.transforms is not None:
            d["transforms"] = [t.to_dict() for t in self.transforms]
        d["languages"] = list(self.languages)
        if self.trust_requirements is not None:
            d["trustRequirements"] = {
                "suites": list(self.trust_requirements.suites),
                "trustList": self.trust_requirements.trust_list,
                **(
                    {"minimumMarker": self.trust_requirements.minimum_marker}
                    if self.trust_requirements.minimum_marker
                    else {}
                ),
            }
        if self.resolution is not None:
            d["resolution"] = {
                **({"confidential": self.resolution.confidential} if self.resolution.confidential else {}),
                "resolution": self.resolution.resolution,
                **(
                    {"edgeVisibility": self.resolution.edge_visibility}
                    if self.resolution.edge_visibility
                    else {}
                ),
                "traversal": self.resolution.traversal,
            }
        return d


@dataclass
class ProfileBinding:
    """A profile bound to a passport at a point in time (manifest entry)."""

    profile_id: str
    version: str
    effective: EffectiveWindow
    binding_event_id: str | None = None

    def __post_init__(self) -> None:
        _require_str(self.profile_id, "profileId")
        _require_str(self.version, "version")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "profileId": self.profile_id,
            "version": self.version,
            "effective": self.effective.to_dict(),
        }
        if self.binding_event_id is not None:
            d["bindingEventId"] = self.binding_event_id
        return d


@dataclass
class InstallationBinding:
    method: str  # e.g. "socketed", "soldered", "bolted", "welded"
    recoverability: str

    def __post_init__(self) -> None:
        _require_str(self.method, "method")
        _require_member(self.recoverability, RECOVERABILITIES, "recoverability")


@dataclass
class VisibilityClause:
    """I12 enumeration resistance: edge visibility on every relationship."""

    edge: str
    escrow: str | None = None  # none | trustee
    audiences: list[str] | None = None

    def __post_init__(self) -> None:
        _require_member(self.edge, EDGE_VISIBILITY_CLASSES, "edge")
        if self.escrow is not None and self.escrow not in ("none", "trustee"):
            raise ModelError(f"bad escrow: {self.escrow!r}")


@dataclass
class ChildReference:
    """R3 child reference in the parent manifest (composition by reference)."""

    child_id: str
    relationship: str  # installation | membership | derivation
    visibility: VisibilityClause
    slot_id: str | None = None
    pairing: str | None = None
    binding: InstallationBinding | None = None
    dormant: bool = False  # True when the reference points at a dormant identifier

    def __post_init__(self) -> None:
        _require_str(self.child_id, "childId")
        if self.relationship not in ("installation", "membership", "derivation"):
            raise ModelError(f"bad child relationship: {self.relationship!r}")
        if self.pairing is not None:
            _require_member(self.pairing, PAIRING_MODES, "pairing")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "childId": self.child_id,
            "relationship": self.relationship,
        }
        if self.slot_id is not None:
            d["slotId"] = self.slot_id
        if self.pairing is not None:
            d["pairing"] = self.pairing
        if self.binding is not None:
            d["binding"] = asdict(self.binding)
        d["visibility"] = visibility_to_dict(self.visibility)
        if self.dormant:
            d["dormant"] = True
        return d


def visibility_to_dict(v: VisibilityClause) -> dict[str, Any]:
    d: dict[str, Any] = {"edge": v.edge}
    if v.escrow is not None:
        d["escrow"] = v.escrow
    if v.audiences is not None:
        d["audiences"] = list(v.audiences)
    return d


@dataclass
class EventLogPointer:
    log_uri: str
    commitment: str
    height: int

    def __post_init__(self) -> None:
        _require_str(self.log_uri, "logUri")
        if not re.fullmatch(r"[0-9a-f]{64}", self.commitment or ""):
            raise ModelError("eventLog.commitment must be a 64-char lowercase hex digest")
        if not isinstance(self.height, int) or isinstance(self.height, bool) or self.height < 0:
            raise ModelError("eventLog.height must be a non-negative integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "logUri": self.log_uri,
            "commitment": self.commitment,
            "height": self.height,
        }


@dataclass
class PassportManifest:
    """The neutral-core passport manifest (L1)."""

    passport_id: ProductIdentifier
    subject_id: ProductIdentifier
    status: str
    profiles: list[ProfileBinding]
    children: list[ChildReference]
    event_log: EventLogPointer
    capability_class: str
    as_of: str
    type_ref: TypeReference | None = None

    def __post_init__(self) -> None:
        _require_member(self.status, PASSPORT_STATUSES, "status")
        _require_member(self.capability_class, CAPABILITY_CLASSES, "capabilityClass")
        _require_str(self.as_of, "asOf")

    def profiles_at(self, at: str) -> list[ProfileBinding]:
        """As-of applicability query: bindings effective at instant ``at``."""
        return [b for b in self.profiles if b.effective.contains(at)]

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "passportId": self.passport_id.to_dict(),
            "subjectId": self.subject_id.to_dict(),
        }
        if self.type_ref is not None:
            d["typeRef"] = self.type_ref.to_dict()
        d.update(
            {
                "status": self.status,
                "profiles": [b.to_dict() for b in self.profiles],
                "children": [c.to_dict() for c in self.children],
                "eventLog": self.event_log.to_dict(),
                "capabilityClass": self.capability_class,
                "asOf": self.as_of,
            }
        )
        return d


# ---------------------------------------------------------------------------
# Relationship algebra (links.ts)
# ---------------------------------------------------------------------------

RELATIONSHIP_TYPES = (
    "association",  # R1 loose: navigational only, free add/remove
    "derivation",  # R2 ancestral: input->output transformation edges
    "installation",  # R3 structural: parent<->child, temporal
    "type-lineage",  # R4 identity lattice: type versioning, derived types
    # R5 profile-of is a lens<->core relation — NOT a passport edge.
    "custody",  # R6 social/control: orthogonal to structure
    "membership",  # R7 group nodes: shipments, kits, recall sets
)


@dataclass
class PassportLink:
    type: str
    from_: str
    to: str
    direction: str  # up | down | symmetric
    interval_from: str
    visibility: VisibilityClause
    interval_until: str | None = None
    binding: InstallationBinding | None = None
    slot_id: str | None = None
    pairing: str | None = None
    alteration: list[str] = field(default_factory=list)
    parent_commitment: str | None = None

    def __post_init__(self) -> None:
        _require_member(self.type, RELATIONSHIP_TYPES, "type")
        _require_str(self.from_, "from")
        _require_str(self.to, "to")
        if self.direction not in ("up", "down", "symmetric"):
            raise ModelError(f"bad direction: {self.direction!r}")
        _require_str(self.interval_from, "interval.from")
        if self.pairing is not None:
            _require_member(self.pairing, PAIRING_MODES, "pairing")
        # parentCommitment hex shape is enforced by the wire schema
        # (passport-link.schema.json pattern); the TS fixture carries a
        # decorative placeholder value, so construction stays permissive.

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "type": self.type,
            "from": self.from_,
            "to": self.to,
            "direction": self.direction,
            "interval": {"from": self.interval_from},
        }
        if self.interval_until is not None:
            d["interval"]["until"] = self.interval_until
        if self.binding is not None:
            d["binding"] = asdict(self.binding)
        if self.slot_id is not None:
            d["slotId"] = self.slot_id
        if self.pairing is not None:
            d["pairing"] = self.pairing
        if self.alteration:
            d["alteration"] = list(self.alteration)
        d["visibility"] = visibility_to_dict(self.visibility)
        if self.parent_commitment is not None:
            d["parentCommitment"] = self.parent_commitment
        return d


def is_visible_to(link: PassportLink, audience: str) -> bool:
    v = link.visibility
    if v.edge == "public":
        return True
    if v.edge == "restricted":
        return audience in (v.audiences or [])
    if v.edge == "blind":
        return False  # only a salted commitment exists
    return False  # escrowed: disclosure only by ceremony


def downstream_of(links: list[PassportLink], root: str) -> set[str]:
    """Recall routing over the provenance DAG (trace-down).

    Direction-aware: ``up`` edges point child->parent, ``down`` edges
    parent->child, ``symmetric`` both ways. Predicate-based by design — the
    recall set is never enumerated centrally (I12).
    """
    out: set[str] = set()
    queue = [root]
    while queue:
        current = queue.pop()
        for link in links:
            if link.direction == "up":
                targets = [link.from_] if link.to == current else []
            elif link.direction == "down":
                targets = [link.to] if link.from_ == current else []
            else:
                if link.from_ == current:
                    targets = [link.to]
                elif link.to == current:
                    targets = [link.from_]
                else:
                    targets = []
            for target in targets:
                if target not in out:
                    out.add(target)
                    queue.append(target)
    return out


# ---------------------------------------------------------------------------
# L3 semantic registry (registry.ts)
# ---------------------------------------------------------------------------

REGISTRY_ITEM_STATUSES = (
    "proposal",
    "under-review",
    "valid",
    "superseded",
    "retired",
    "invalid",
)
REGISTRY_ITEM_CLASSES = (
    "data-element",
    "profile",
    "cryptographic-suite",
    "trust-anchor",
    "unit",
    "transform",
    "code-list",
)


@dataclass
class RegistryItem:
    """Simplified ISO 19135 register item (FERIN federated registers)."""

    register: str
    item: str
    version: str
    item_class: str
    status: str
    dates_proposed: str
    definition_uri: str
    definition_media_type: str
    definition_checksum: str
    dates_registered: str | None = None
    dates_superseded: str | None = None
    dates_retired: str | None = None
    superseded_by: RegistryItemRef | None = None

    def __post_init__(self) -> None:
        _require_str(self.register, "register")
        _require_str(self.item, "item")
        _require_str(self.version, "version")
        _require_member(self.item_class, REGISTRY_ITEM_CLASSES, "itemClass")
        _require_member(self.status, REGISTRY_ITEM_STATUSES, "status")
        _require_str(self.dates_proposed, "dates.proposed")
        _require_str(self.definition_uri, "definition.uri")
        if self.definition_media_type not in (
            "application/cddal",
            "application/json",
            "text/xml",
        ):
            raise ModelError(f"bad definition media type: {self.definition_media_type!r}")

    @property
    def dates(self) -> dict[str, str]:
        d = {"proposed": self.dates_proposed}
        if self.dates_registered is not None:
            d["registered"] = self.dates_registered
        if self.dates_superseded is not None:
            d["superseded"] = self.dates_superseded
        if self.dates_retired is not None:
            d["retired"] = self.dates_retired
        return d


def item_effective_at(item: RegistryItem, at: str) -> bool:
    """Is the item usable for a binding effective at time ``at``?"""
    if item.status == "invalid":
        return False
    registered = item.dates_registered or item.dates_proposed
    if at < registered:
        return False
    off = item.dates_superseded or item.dates_retired
    return True if off is None else at < off


# ---------------------------------------------------------------------------
# Tier-A pack (tier.ts) + verdicts (verdict.ts)
# ---------------------------------------------------------------------------

CARRIER_BUDGETS: dict[str, int] = {
    "qr-version-15": 1098,  # low-error QR byte capacity
    "qr-version-25": 1853,
    "qr-version-40": 2953,
    "data-matrix-144x144": 1558,
    "nfc-ntag424": 256,  # conservative NDEF payload budget
}

TierId = str  # "A" | "B" | "C"
Freshness = str  # "fresh" | "stale" | "unknown"
VerdictOutcome = str  # "pass" | "degraded" | "fail"


@dataclass
class CriticalSafety:
    recall: bool
    campaign_ref: str | None = None


@dataclass
class Validity:
    not_before: str
    not_after: str

    def __post_init__(self) -> None:
        _require_str(self.not_before, "notBefore")
        _require_str(self.not_after, "notAfter")


@dataclass
class LogCommitment:
    commitment: str
    height: int
    as_of: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.commitment or ""):
            raise ModelError("logCommitment.commitment must be 64-char lowercase hex")
        if not isinstance(self.height, int) or isinstance(self.height, bool) or self.height < 0:
            raise ModelError("logCommitment.height must be a non-negative integer")
        _require_str(self.as_of, "asOf")


@dataclass
class TierAProfileRef:
    profile_id: str
    version: str

    def __post_init__(self) -> None:
        _require_str(self.profile_id, "profileId")
        _require_str(self.version, "version")


@dataclass
class TierAPack:
    """Tier-A pack (I13): carrier-embedded minimum viable passport."""

    subject_id: ProductIdentifier
    passport_id: ProductIdentifier
    resolver_uri: str
    operator_id: str
    status: str
    critical_safety: CriticalSafety
    validity: Validity
    profiles: list[TierAProfileRef]
    log_commitment: LogCommitment
    signatures: list[SignatureFraming]
    kind: str = "unidpp.tier-a"
    version: str = "1"

    def __post_init__(self) -> None:
        if self.kind != "unidpp.tier-a":
            raise ModelError(f"bad pack kind: {self.kind!r}")
        if self.version != "1":
            raise ModelError(f"bad pack version: {self.version!r}")
        _require_str(self.resolver_uri, "resolverUri")
        _require_str(self.operator_id, "operatorId")
        _require_member(self.status, PASSPORT_STATUSES, "status")
        # minItems for profiles/signatures is enforced by the wire schema
        # (tier-a.schema.json); construction allows incremental assembly.

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # normalize snake_case keys back to wire casing
        return {
            "kind": d["kind"],
            "version": d["version"],
            "subjectId": d["subject_id"],
            "passportId": d["passport_id"],
            "resolverUri": d["resolver_uri"],
            "operatorId": d["operator_id"],
            "status": d["status"],
            "criticalSafety": {
                "recall": d["critical_safety"]["recall"],
                **({"campaignRef": d["critical_safety"]["campaign_ref"]} if d["critical_safety"]["campaign_ref"] else {}),
            },
            "validity": {"notBefore": d["validity"]["not_before"], "notAfter": d["validity"]["not_after"]},
            "profiles": [{"profileId": p["profile_id"], "version": p["version"]} for p in d["profiles"]],
            "logCommitment": {
                "commitment": d["log_commitment"]["commitment"],
                "height": d["log_commitment"]["height"],
                "asOf": d["log_commitment"]["as_of"],
            },
            "signatures": [
                {"suite": s["suite"], "keyId": s["key_id"], "signedAt": s["signed_at"], "value": s["value"]}
                for s in d["signatures"]
            ],
        }


def tier_of(pack: Mapping[str, Any] | TierAPack) -> str:
    kind = pack.kind if isinstance(pack, TierAPack) else pack.get("kind")
    return "A" if kind == "unidpp.tier-a" else "unknown"


def pack_size(pack: TierAPack) -> int:
    """Estimated serialized size (canonical JSON, pre-compression), bytes."""
    from .canonical import canonical_json

    return len(canonical_json(pack.to_dict()).encode("utf-8"))


def fits_carrier(pack: TierAPack, carrier: str) -> bool:
    """Does the pack fit a carrier budget (compression out of scope here)?"""
    budget = CARRIER_BUDGETS.get(carrier)
    if budget is None:
        raise ModelError(f"unknown carrier: {carrier}")
    return pack_size(pack) <= budget


@dataclass
class Finding:
    severity: str  # info | warning | error
    code: str
    message: str

    def __post_init__(self) -> None:
        if self.severity not in ("info", "warning", "error"):
            raise ModelError(f"bad severity: {self.severity!r}")


@dataclass
class CoverageReport:
    """Coverage reports: verification is coverage-based, not boolean (I9)."""

    checks: int = 0
    passed: int = 0
    signatures_total: int = 0
    signatures_verified: int = 0
    signatures_failed: int = 0
    signatures_unsupported: int = 0
    anchor_coverage: float = 0.0
    trust_coverage: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": self.checks,
            "passed": self.passed,
            "signatures": {
                "total": self.signatures_total,
                "verified": self.signatures_verified,
                "failed": self.signatures_failed,
                "unsupported": self.signatures_unsupported,
            },
            "anchorCoverage": self.anchor_coverage,
            "trustCoverage": self.trust_coverage,
        }


def coverage_ratio(report: CoverageReport) -> float:
    return 1 if report.checks == 0 else report.passed / report.checks


@dataclass
class Verdict:
    reading: str
    outcome: str
    freshness: str
    coverage: CoverageReport
    findings: list[Finding] = field(default_factory=list)
    as_of: str = ""
    achieved_marker: str = "unsigned"

    def to_dict(self) -> dict[str, Any]:
        return {
            "reading": self.reading,
            "outcome": self.outcome,
            "freshness": self.freshness,
            "coverage": self.coverage.to_dict(),
            "findings": [asdict(f) for f in self.findings],
            "asOf": self.as_of,
            "achievedMarker": self.achieved_marker,
        }


def combine_outcome(outcomes: list[str]) -> str:
    if "fail" in outcomes:
        return "fail"
    if "degraded" in outcomes:
        return "degraded"
    return "pass"


def outcome_for_freshness(freshness: str) -> str:
    """I13: stale/offline data degrades explicitly, never silently passes."""
    if freshness == "fresh":
        return "pass"
    if freshness == "stale":
        return "degraded"
    return "pass"  # unknown: no requirement declared — informational


# ---------------------------------------------------------------------------
# Event taxonomy (events.ts types) + wire schemas (schemas.ts / schema/*.json)
# ---------------------------------------------------------------------------

EVENT_TYPES = (
    "passport.created",  # issuance (manufacturer/transformer/registrar/attestor)
    "profile.binding",  # dated applicability binding (incl. retroactive flags)
    "custody.transfer",  # E1 resale, lease, inheritance, liquidation
    "part.replace",  # E2 uninstall + install; BoM-instance updated
    "repair.perform",  # E3 authorized / independent / DIY
    "product.modify",  # E4 may spawn derived type (E4b) + profile re-evaluation
    "software.update",  # E5 firmware/software version vector; feature.unlock
    "upgrade.install",  # E6 add component: new child reference
    "refurbish.perform",  # E7 condition grade; remanufacture may be transformation
    "consumable.replace",  # E8 tires, filters — recurring
    "recall.campaign",  # E9 campaign ref; DAG traversal + custodian notification
    "correction.record",  # E10 new corrected fact + reason; prior preserved
    "status.change",  # E11 suspend / invalidate / reinstate, authority-checked
    "flag.security",  # E12 theft / loss; blacklist entry
    "material.decompose",  # E13 inverse transformation 1->N -> material passports
    "inspection.stamp",  # E14 lens-scoped attestation by any verifier
    "milestone.record",  # E15 edge-segment state commitment (device)
)

ACTOR_ROLES = (
    "economic-operator",
    "custodian",
    "repairer",
    "installer",
    "refurbisher",
    "recycler",
    "regulator",
    "device",
    "verifier",
    "registrar",
    "qualified-attestor",
)

# Typed payload contracts exercised by the fixtures and verifiers. Keys are
# required; keys listed as optional in the TS EventPayloads map to None-able
# entries. Extra keys are permitted (JsonRecord is open).
EVENT_PAYLOAD_CONTRACTS: dict[str, dict[str, bool]] = {
    "passport.created": {"typeRef": False, "profileIds": True},
    "profile.binding": {
        "profileId": True,
        "version": True,
        "from": True,
        "until": False,
        "retroactive": False,
    },
    "custody.transfer": {"fromActor": True, "toActor": True, "conveyance": False},
    "part.replace": {
        "removedChildId": False,
        "installedChildId": False,
        "likeForLike": True,
        "slotId": False,
    },
    "repair.perform": {"repairClass": True, "recordRef": False},
    "product.modify": {"modification": True, "spawnedDerivedType": False},
    "software.update": {
        "component": True,
        "fromVersion": True,
        "toVersion": True,
        "featureUnlock": False,
    },
    "upgrade.install": {
        "childId": True,
        "parentSlot": True,
        "pairing": True,
        "method": True,
        "recoverability": True,
        "visibilityEdge": True,
    },
    "refurbish.perform": {"conditionGrade": False, "remanufactureToType": False},
    "consumable.replace": {"removedChildId": False, "installedChildId": False},
    "recall.campaign": {"campaignRef": True, "predicate": True},
    "correction.record": {"field": True, "reason": True, "correctedTo": True},
    "status.change": {"from": True, "to": True, "authority": True},
    "flag.security": {"flag": True, "reportRef": False},
    "material.decompose": {"outputs": True, "inputReferences": False},
    "inspection.stamp": {
        "lensId": True,
        "lensVersion": True,
        "mode": True,
        "verdictSummary": True,
    },
    "milestone.record": {
        "commitment": True,
        "deviceKeyId": True,
        "freshWithin": True,
    },
}

_ENUM_IN_PAYLOAD = {
    ("repair.perform", "repairClass"): ("authorized", "independent", "diy"),
    ("upgrade.install", "pairing"): PAIRING_MODES,
    ("upgrade.install", "recoverability"): RECOVERABILITIES,
    ("upgrade.install", "visibilityEdge"): EDGE_VISIBILITY_CLASSES,
    ("flag.security", "flag"): ("theft", "loss"),
    ("inspection.stamp", "mode"): ("live", "snapshot"),
}


def _identifier_schema() -> dict[str, Any]:
    return {
        "$id": "https://unidpp.org/schemas/2026/identifier.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Product identifier (L0)",
        "description": "Scheme-agnostic identifier; never re-minted (I1).",
        "type": "object",
        "additionalProperties": False,
        "required": ["scheme", "value", "granularity", "state"],
        "properties": {
            "scheme": {"type": "string", "minLength": 1},
            "value": {"type": "string", "minLength": 1},
            "granularity": {"enum": list(IDENTIFIER_GRANULARITIES)},
            "state": {"enum": list(IDENTIFIER_STATES)},
        },
        "$defs": {
            "typeReference": {
                "type": "object",
                "additionalProperties": False,
                "required": ["typeId", "typeVersion"],
                "properties": {
                    "typeId": {"$ref": "#/$defs/productIdentifier"},
                    "typeVersion": {"type": "string", "minLength": 1},
                    "configurationVector": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            "productIdentifier": {"$ref": "#"},
        },
    }


def _manifest_schema(defs: dict[str, Any]) -> dict[str, Any]:
    return {
        "$id": "https://unidpp.org/schemas/2026/passport-manifest.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Passport manifest (L1 neutral core)",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "passportId",
            "subjectId",
            "status",
            "profiles",
            "children",
            "eventLog",
            "capabilityClass",
            "asOf",
        ],
        "properties": {
            "passportId": {"$ref": "#/$defs/identifier:productIdentifier"},
            "subjectId": {"$ref": "#/$defs/identifier:productIdentifier"},
            "typeRef": {"$ref": "#/$defs/identifier:typeReference"},
            "status": {"enum": list(PASSPORT_STATUSES)},
            "profiles": {"type": "array", "items": {"$ref": "#/$defs/manifest:profileBinding"}},
            "children": {"type": "array", "items": {"$ref": "#/$defs/manifest:childReference"}},
            "eventLog": {"$ref": "#/$defs/manifest:eventLogPointer"},
            "capabilityClass": {"enum": list(CAPABILITY_CLASSES)},
            "asOf": {"type": "string", "format": "date-time"},
        },
        "$defs": defs,
    }


def _link_schema(defs: dict[str, Any]) -> dict[str, Any]:
    return {
        "$id": "https://unidpp.org/schemas/2026/passport-link.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "PassportLink (I5 typed relationship algebra)",
        "type": "object",
        "additionalProperties": False,
        "required": ["type", "from", "to", "direction", "interval", "visibility"],
        "properties": {
            "type": {"enum": list(RELATIONSHIP_TYPES)},
            "from": {"type": "string"},
            "to": {"type": "string", "format": "uri"},
            "direction": {"enum": ["up", "down", "symmetric"]},
            "interval": {"$ref": "#/$defs/manifest:interval"},
            "binding": {"$ref": "#/$defs/manifest:installationBinding"},
            "slotId": {"type": "string"},
            "pairing": {"enum": list(PAIRING_MODES)},
            "alteration": {"type": "array", "items": {"type": "string"}},
            "visibility": {"$ref": "#/$defs/manifest:visibilityClause"},
            "parentCommitment": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        },
        "$defs": defs,
    }


def _event_schema(defs: dict[str, Any]) -> dict[str, Any]:
    return {
        "$id": "https://unidpp.org/schemas/2026/event.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Domain event (I4 append-only, commitment-chained)",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "eventId",
            "type",
            "subject",
            "occurredAt",
            "actor",
            "trustMarker",
            "prevCommitment",
            "commitment",
        ],
        "properties": {
            "eventId": {"type": "string", "minLength": 1},
            "type": {"enum": list(EVENT_TYPES)},
            "subject": {"type": "string", "minLength": 1},
            "occurredAt": {"type": "string", "format": "date-time"},
            "actor": {
                "type": "object",
                "additionalProperties": False,
                "required": ["actorId", "role"],
                "properties": {
                    "actorId": {"type": "string", "minLength": 1},
                    "role": {"enum": list(ACTOR_ROLES)},
                    "credentialRef": {"type": "string"},
                },
            },
            "payload": {"type": "object"},
            "trustMarker": {"enum": list(TRUST_MARKERS)},
            "prevCommitment": {"type": "string"},
            "commitment": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        },
        "$defs": defs,
    }


def _tier_a_schema(defs: dict[str, Any]) -> dict[str, Any]:
    return {
        "$id": "https://unidpp.org/schemas/2026/tier-a.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Tier-A pack (I13 carrier-embedded minimum viable passport)",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "kind",
            "version",
            "subjectId",
            "passportId",
            "resolverUri",
            "operatorId",
            "status",
            "criticalSafety",
            "validity",
            "profiles",
            "logCommitment",
            "signatures",
        ],
        "properties": {
            "kind": {"const": "unidpp.tier-a"},
            "version": {"const": "1"},
            "subjectId": {"$ref": "#/$defs/identifier:productIdentifier"},
            "passportId": {"$ref": "#/$defs/identifier:productIdentifier"},
            "resolverUri": {"type": "string", "format": "uri"},
            "operatorId": {"type": "string", "minLength": 1},
            "status": {"enum": list(PASSPORT_STATUSES)},
            "criticalSafety": {
                "type": "object",
                "additionalProperties": False,
                "required": ["recall"],
                "properties": {
                    "recall": {"type": "boolean"},
                    "campaignRef": {"type": "string"},
                },
            },
            "validity": {
                "type": "object",
                "additionalProperties": False,
                "required": ["notBefore", "notAfter"],
                "properties": {
                    "notBefore": {"type": "string", "format": "date-time"},
                    "notAfter": {"type": "string", "format": "date-time"},
                },
            },
            "profiles": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["profileId", "version"],
                    "properties": {
                        "profileId": {"type": "string", "minLength": 1},
                        "version": {"type": "string", "minLength": 1},
                    },
                },
            },
            "logCommitment": {
                "type": "object",
                "additionalProperties": False,
                "required": ["commitment", "height", "asOf"],
                "properties": {
                    "commitment": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "height": {"type": "integer", "minimum": 0},
                    "asOf": {"type": "string", "format": "date-time"},
                },
            },
            "signatures": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["suite", "keyId", "signedAt", "value"],
                    "properties": {
                        "suite": {"type": "string", "minLength": 1},
                        "keyId": {"type": "string", "minLength": 1},
                        "signedAt": {"type": "string", "format": "date-time"},
                        "value": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
        "$defs": defs,
    }


def _shared_defs() -> dict[str, Any]:
    return {
        "identifier:productIdentifier": {
            "type": "object",
            "additionalProperties": False,
            "required": ["scheme", "value", "granularity", "state"],
            "properties": {
                "scheme": {"type": "string", "minLength": 1},
                "value": {"type": "string", "minLength": 1},
                "granularity": {"enum": list(IDENTIFIER_GRANULARITIES)},
                "state": {"enum": list(IDENTIFIER_STATES)},
            },
        },
        "identifier:typeReference": {
            "type": "object",
            "additionalProperties": False,
            "required": ["typeId", "typeVersion"],
            "properties": {
                "typeId": {"$ref": "#/$defs/identifier:productIdentifier"},
                "typeVersion": {"type": "string", "minLength": 1},
                "configurationVector": {"type": "array", "items": {"type": "string"}},
            },
        },
        "manifest:interval": {
            "type": "object",
            "additionalProperties": False,
            "required": ["from"],
            "properties": {
                "from": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
            },
        },
        "manifest:effectiveWindow": {
            "type": "object",
            "additionalProperties": False,
            "required": ["from"],
            "properties": {
                "from": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "retroactive": {"type": "boolean"},
            },
        },
        "manifest:installationBinding": {
            "type": "object",
            "additionalProperties": False,
            "required": ["method", "recoverability"],
            "properties": {
                "method": {"type": "string", "minLength": 1},
                "recoverability": {"enum": list(RECOVERABILITIES)},
            },
        },
        "manifest:visibilityClause": {
            "type": "object",
            "additionalProperties": False,
            "required": ["edge"],
            "properties": {
                "edge": {"enum": list(EDGE_VISIBILITY_CLASSES)},
                "escrow": {"enum": ["none", "trustee"]},
                "audiences": {"type": "array", "items": {"type": "string"}},
            },
        },
        "manifest:childReference": {
            "type": "object",
            "additionalProperties": False,
            "required": ["childId", "relationship", "visibility"],
            "properties": {
                "childId": {"type": "string", "format": "uri"},
                "relationship": {"enum": ["installation", "membership", "derivation"]},
                "slotId": {"type": "string"},
                "pairing": {"enum": list(PAIRING_MODES)},
                "binding": {"$ref": "#/$defs/manifest:installationBinding"},
                "visibility": {"$ref": "#/$defs/manifest:visibilityClause"},
                "dormant": {"type": "boolean"},
            },
        },
        "manifest:profileBinding": {
            "type": "object",
            "additionalProperties": False,
            "required": ["profileId", "version", "effective"],
            "properties": {
                "profileId": {"type": "string", "minLength": 1},
                "version": {"type": "string", "minLength": 1},
                "effective": {"$ref": "#/$defs/manifest:effectiveWindow"},
                "bindingEventId": {"type": "string"},
            },
        },
        "manifest:eventLogPointer": {
            "type": "object",
            "additionalProperties": False,
            "required": ["logUri", "commitment", "height"],
            "properties": {
                "logUri": {"type": "string", "format": "uri"},
                "commitment": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "height": {"type": "integer", "minimum": 0},
            },
        },
    }


_DEFS = _shared_defs()
schemas: dict[str, dict[str, Any]] = {
    "identifier": _identifier_schema(),
    "manifest": _manifest_schema(_DEFS),
    "link": _link_schema(_DEFS),
    "event": _event_schema(_DEFS),
    "tierA": _tier_a_schema(_DEFS),
}


def _wire_manifest(m: Any) -> Any:
    return m.to_dict() if hasattr(m, "to_dict") else m


def validate_identifier(instance: Any) -> ValidationResult:  # noqa: F821
    from .validate import validate

    return validate(instance, schemas["identifier"])


def validate_manifest(instance: Any) -> ValidationResult:  # noqa: F821
    from .validate import validate

    return validate(_wire_manifest(instance), schemas["manifest"])


def validate_link(instance: Any) -> ValidationResult:  # noqa: F821
    from .validate import validate

    wire = instance.to_dict() if hasattr(instance, "to_dict") else instance
    return validate(wire, schemas["link"])


def validate_event(instance: Any) -> ValidationResult:  # noqa: F821
    from .validate import validate

    wire = instance.to_dict() if hasattr(instance, "to_dict") else instance
    return validate(wire, schemas["event"])


def validate_tier_a_pack(instance: Any) -> ValidationResult:  # noqa: F821
    from .validate import validate

    wire = instance.to_dict() if hasattr(instance, "to_dict") else instance
    return validate(wire, schemas["tierA"])
