"""UniDPP Python library — stdlib-only mirror of the UniDPP TS SDK model.

Modules:
- ``unidpp.canonical``  — canonical JSON + SHA-256 commitments
- ``unidpp.model``      — the mirrored model (types + validation + schemas)
- ``unidpp.eventlog``   — append-only commitment-chained log, blind edges,
                          mass balance
- ``unidpp.verify``     — verification pipeline harness (readings,
                          freshness verdicts, coverage reports, crypto
                          slots with the ECDSA-None degrade placeholder)
- ``unidpp.conformance``— conformance runner (positive corpus + AUDIT.md
                          A1-A6 negative fixtures; JSON + markdown reports)
- ``unidpp.adapters``   — EPCIS event import, UNTP stub parsing
- ``unidpp.fixtures``   — laptop and car pilots ported from the TS repo
"""

from . import canonical, eventlog, model, validate, verify
from .model import (
    CLASS_CAPABILITY,
    PASSPORT_STATUSES,
    REVOCATION_REASONS,
    RETROACTIVE_REASONS,
    TRUST_MARKERS,
    VERIFICATION_READINGS,
    ChildReference,
    CoverageReport,
    EffectiveWindow,
    Finding,
    InstallationBinding,
    PassportLink,
    PassportManifest,
    ProductIdentifier,
    ProfileBinding,
    ProfileDefinition,
    RevocationRecord,
    SignatureFraming,
    TierAPack,
    TaintRecord,
    Verdict,
    VisibilityClause,
    is_visible_to,
    downstream_of,
    marker_at_least,
    signature_voided,
)
from .eventlog import (
    Actor,
    AppendOnlyError,
    DomainEvent,
    append_event,
    blind_edge_commitment,
    log_head,
    mass_balance,
    verify_chain,
)

__version__ = "0.1.0"
__all__ = [
    "canonical",
    "model",
    "validate",
    "verify",
    "eventlog",
    "Actor",
    "AppendOnlyError",
    "CLASS_CAPABILITY",
    "ChildReference",
    "CoverageReport",
    "DomainEvent",
    "EffectiveWindow",
    "Finding",
    "InstallationBinding",
    "PASSPORT_STATUSES",
    "PassportLink",
    "PassportManifest",
    "ProductIdentifier",
    "ProfileBinding",
    "ProfileDefinition",
    "REVOCATION_REASONS",
    "RETROACTIVE_REASONS",
    "RevocationRecord",
    "SignatureFraming",
    "TRUST_MARKERS",
    "TierAPack",
    "TaintRecord",
    "VERIFICATION_READINGS",
    "Verdict",
    "VisibilityClause",
    "append_event",
    "blind_edge_commitment",
    "downstream_of",
    "is_visible_to",
    "log_head",
    "marker_at_least",
    "mass_balance",
    "signature_voided",
    "verify_chain",
]
