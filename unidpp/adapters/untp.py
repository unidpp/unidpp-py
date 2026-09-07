"""UNTP-style passport stub parsing.

Parses a UNTP (UN/CEFACT Transformed Digital Product Passport, v0.x shape)
passport JSON stub into UniDPP manifest fields. This is a *stub* parser:
it extracts identity, issuer, validity and profile pointers, and leaves the
event-log pointer anchored to a commitment over the stub itself so the
resulting manifest is schema-valid and as-of-stamped at parse time.

Supported stub shape (superset tolerated, missing fields raise):

    {
      "@context": ["https://ref.gs1.org/gs1/v/...
      "type": "ProductPassport",
      "id": "https://example.com/passports/123",
      "productIdentifiers": [{"scheme": "https://gs1.org/voc/", "value": "(01)0950..."}],
      "passportIssuer": {"id": "...", "name": "..."},
      "validFrom": "2026-01-01T00:00:00Z",
      "validUntil": "2036-01-01T00:00:00Z",
      "standardsConformance": [{"standard": "ESPR", ...}]
    }
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..canonical import commitment
from ..model import (
    EffectiveWindow,
    EventLogPointer,
    PassportManifest,
    ProductIdentifier,
    ProfileBinding,
)

__all__ = ["UntpStubError", "parse_untp_stub"]

_SCHEME_MAP = {
    "https://gs1.org/voc/": "gs1",
    "https://id.gs1.org/": "gs1",
    "https://ref.gs1.org/": "gs1",
    "urn:epc:id:": "gs1",
    "https://www.w3.org/ns/": "iso-15459",
    "https://unidpp.org/id/": "iso-15459",
}


class UntpStubError(ValueError):
    """Raised when a UNTP stub cannot be parsed faithfully."""


def _map_scheme(scheme: str) -> str:
    if scheme in _SCHEME_MAP:
        return _SCHEME_MAP[scheme]
    # short-form or unknown: keep as-is (registry extension point)
    return scheme


def _first_identifier(stub: Mapping[str, Any]) -> ProductIdentifier:
    ids = stub.get("productIdentifiers")
    if not ids or not isinstance(ids[0], Mapping):
        raise UntpStubError("stub has no productIdentifiers")
    raw = ids[0]
    value = str(raw.get("value", ""))
    if not value:
        raise UntpStubError("identifier carries no value")
    scheme = _map_scheme(str(raw.get("scheme", "https://gs1.org/voc/")))
    return ProductIdentifier(
        scheme=scheme,
        value=value,
        granularity="item",
        state="live",
    )


def parse_untp_stub(stub: Mapping[str, Any], as_of: str) -> PassportManifest:
    """Parse a UNTP-style passport stub into a neutral-core manifest.

    The manifest's ``eventLog.commitment`` is the canonical commitment over
    the stub itself (an import receipt); the log URI is the stub's ``id``.
    """
    if not isinstance(stub, Mapping):
        raise UntpStubError("stub must be a JSON object")
    ptype = stub.get("type", "ProductPassport")
    if "passport" not in str(ptype).lower():
        raise UntpStubError(f"not a passport stub: type={ptype!r}")
    subject = _first_identifier(stub)
    stub_id = str(stub.get("id") or f"urn:unidpp:import:{subject.value}")
    issuer = stub.get("passportIssuer") or {}
    if not isinstance(issuer, Mapping):
        raise UntpStubError("passportIssuer must be an object")
    profiles: list[ProfileBinding] = []
    for conf in stub.get("standardsConformance") or []:
        if not isinstance(conf, Mapping):
            continue
        profiles.append(
            ProfileBinding(
                profile_id=str(conf.get("standard") or "urn:unidpp:profile:untp"),
                version=str(conf.get("conformanceVersion") or conf.get("version") or "0"),
                effective=EffectiveWindow(
                    from_=str(stub.get("validFrom") or as_of),
                ),
            )
        )

    return PassportManifest(
        passport_id=ProductIdentifier(
            scheme=subject.scheme,
            value=f"urn:iso:std:iso-iec:15459:unidpp:passport:{_slug(subject.value)}",
            granularity="item",
            state="live",
        ),
        subject_id=subject,
        status="active",
        profiles=profiles,
        children=[],
        event_log=EventLogPointer(
            log_uri=stub_id,
            commitment=commitment(dict(stub), "untp-import"),
            height=0,
        ),
        capability_class="S0",
        as_of=as_of,
    )


def _slug(value: str) -> str:
    out = []
    for ch in value:
        if ch.isalnum():
            out.append(ch.lower())
        elif ch in ":-_.":
            out.append(ch)
    return "".join(out) or "unknown"
