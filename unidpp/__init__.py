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
- ``unidpp.temporal``  — the DPP temporal profile: ISO 8601-1:2019
                          (incl. Amd 1:2022 disambiguation) validation of
                          every timestamp field, with precise paths
- ``unidpp.carrier``   — carrier budgets: ISO/IEC 18004 QR capacity
                          tables (ported from the CLI) and the budget
                          grammar
- ``unidpp.adapters``   — EPCIS event import, UNTP stub parsing
- ``unidpp.fixtures``   — laptop and car pilots ported from the TS repo
"""

from . import canonical, eventlog, model, validate, verify
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
from .model import (
    CLASS_CAPABILITY,
    PASSPORT_STATUSES,
    RETROACTIVE_REASONS,
    REVOCATION_REASONS,
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
    TaintRecord,
    TierAPack,
    Verdict,
    VisibilityClause,
    downstream_of,
    is_visible_to,
    marker_at_least,
    signature_voided,
)

__version__ = "0.1.0"
__all__ = [
    "CLASS_CAPABILITY",
    "PASSPORT_STATUSES",
    "RETROACTIVE_REASONS",
    "REVOCATION_REASONS",
    "TRUST_MARKERS",
    "VERIFICATION_READINGS",
    "Actor",
    "AppendOnlyError",
    "ChildReference",
    "CoverageReport",
    "DomainEvent",
    "EffectiveWindow",
    "Finding",
    "InstallationBinding",
    "PassportLink",
    "PassportManifest",
    "ProductIdentifier",
    "ProfileBinding",
    "ProfileDefinition",
    "RevocationRecord",
    "SignatureFraming",
    "TaintRecord",
    "TierAPack",
    "Verdict",
    "VisibilityClause",
    "append_event",
    "blind_edge_commitment",
    "canonical",
    "downstream_of",
    "eventlog",
    "is_visible_to",
    "log_head",
    "marker_at_least",
    "mass_balance",
    "model",
    "signature_voided",
    "validate",
    "verify",
    "verify_chain",
]
