"""Append-only, commitment-chained event log (I4).

Mirror of ``@unidpp/model`` ``events.ts``. The log is the authoritative
record: nothing is edited in place, every post-first-sale change is an
appended event. Each event carries a SHA-256 commitment over the canonical
JSON of ``{"salt": <salt>, "event": <event body>}`` where the body is the
event without its commitment; the commitment chain links each event to its
predecessor (``prevCommitment`` is "" for genesis).

Blind edges (I12): R3 proof-of-binding != knowledge-of-parent. The child's
log carries a *salted* commitment to the parent — ``blind_edge_commitment``
— so log operators cannot correlate edges while the binding remains
provable when the salt is revealed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .canonical import commitment
from .model import (
    EVENT_PAYLOAD_CONTRACTS,
    EVENT_TYPES,
    TRUST_MARKERS,
    ModelError,
    _ENUM_IN_PAYLOAD,
    _require_member,
    _require_str,
)

__all__ = [
    "AppendOnlyError",
    "Actor",
    "DomainEvent",
    "append_event",
    "verify_chain",
    "log_head",
    "blind_edge_commitment",
    "mass_balance",
    "BalanceResult",
]


class AppendOnlyError(ModelError):
    """Raised when an append would violate the commitment chain."""


@dataclass
class Actor:
    actor_id: str
    role: str
    credential_ref: str | None = None

    def __post_init__(self) -> None:
        _require_str(self.actor_id, "actorId")
        from .model import ACTOR_ROLES

        _require_member(self.role, ACTOR_ROLES, "role")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"actorId": self.actor_id, "role": self.role}
        if self.credential_ref is not None:
            d["credentialRef"] = self.credential_ref
        return d


@dataclass
class DomainEvent:
    """Discriminated event: type + typed payload + trust marker + chain."""

    event_id: str
    type: str
    subject: str
    occurred_at: str
    actor: Actor
    payload: dict[str, Any] = field(default_factory=dict)
    trust_marker: str = "unsigned"
    prev_commitment: str = ""
    commitment: str | None = None

    def __post_init__(self) -> None:
        _require_str(self.event_id, "eventId")
        _require_member(self.type, EVENT_TYPES, "type")
        _require_str(self.subject, "subject")
        _require_str(self.occurred_at, "occurredAt")
        _require_member(self.trust_marker, TRUST_MARKERS, "trustMarker")
        if not isinstance(self.payload, dict):
            raise ModelError("payload must be a JSON object")
        contract = EVENT_PAYLOAD_CONTRACTS.get(self.type, {})
        for key, required in contract.items():
            if required and key not in self.payload:
                raise ModelError(f"payload for {self.type} requires {key!r}")
            if key in self.payload and self.payload[key] is None:
                raise ModelError(f"payload.{key} for {self.type} must not be null")
        for (etype, key), allowed in _ENUM_IN_PAYLOAD.items():
            if etype == self.type and key in self.payload:
                _require_member(
                    self.payload[key], allowed, f"payload.{key}"
                )

    @property
    def body(self) -> dict[str, Any]:
        """The hashed body: everything except the commitment itself."""
        d = self.to_dict()
        d.pop("commitment", None)
        return d

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "eventId": self.event_id,
            "type": self.type,
            "subject": self.subject,
            "occurredAt": self.occurred_at,
            "actor": self.actor.to_dict(),
            "payload": self.payload,
            "trustMarker": self.trust_marker,
            "prevCommitment": self.prev_commitment,
        }
        if self.commitment is not None:
            d["commitment"] = self.commitment
        return d


def _event_commitment(event_body: dict[str, Any], salt: str) -> str:
    return commitment({"salt": salt, "event": event_body}, "")


def append_event(
    log: list[DomainEvent],
    event: DomainEvent,
    salt: str = "",
) -> list[DomainEvent]:
    """Append an event to a log, computing its commitment chain.

    The chain is stamped by append: callers cannot know the head commitment
    before it is computed; a caller-supplied ``prevCommitment`` is
    authoritative only when it matches (fork detection).
    """
    prev = "" if len(log) == 0 else log[-1].commitment or ""
    if event.prev_commitment not in ("", prev):
        raise AppendOnlyError(
            "prevCommitment does not match log head; append-only violated"
        )
    chained = DomainEvent(
        event_id=event.event_id,
        type=event.type,
        subject=event.subject,
        occurred_at=event.occurred_at,
        actor=event.actor,
        payload=dict(event.payload),
        trust_marker=event.trust_marker,
        prev_commitment=prev,
    )
    c = _event_commitment(chained.body, salt)
    chained.commitment = c
    return [*log, chained]


def verify_chain(log: list[DomainEvent], salt: str = "") -> bool:
    """Verify the commitment chain of a log (tamper detection)."""
    prev = ""
    for event in log:
        if event.prev_commitment != prev:
            return False
        expected = _event_commitment(event.body, salt)
        if event.commitment != expected:
            return False
        prev = event.commitment or ""
    return True


def log_head(log: list[DomainEvent]) -> dict[str, Any]:
    return {
        "commitment": "" if len(log) == 0 else log[-1].commitment or "",
        "height": len(log),
    }


def blind_edge_commitment(
    parent_passport_value: str, slot: str, salt: str
) -> str:
    """R3 blind edge: salted commitment to the parent (+slot) in the child's log.

    Mirrors the car fixture: ``commitment({parent, slot}, salt)``.
    """
    return commitment({"parent": parent_passport_value, "slot": slot}, salt)


@dataclass
class BalanceResult:
    balanced: bool
    inputs: float
    outputs: float
    loss: float


def mass_balance(
    inputs: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
) -> BalanceResult:
    """Mass-balance conservation for split/combine transformations.

    PLAN.md: quantities are new measured facts with provenance "computed by
    transformation event E" (mass balance in − out = loss, auditable),
    never copies. Only quantities sharing a unit participate; mismatched
    unit sets raise rather than silently balancing.
    """
    units_out = {q.get("unit") for q in outputs}
    units_out.discard(None)
    if len(units_out) != 1:
        raise ModelError(
            f"mass balance requires a single output unit, got {sorted(str(u) for u in units_out)}"
        )
    unit = next(iter(units_out))
    # inputReferences carry (passportId, quantity, stateHash) — no unit;
    # a bare quantity inherits the transformation's single output unit.
    units_in = {q.get("unit", unit) for q in inputs}
    if units_in - {unit}:
        raise ModelError(
            f"mass balance requires matching units, got in={sorted(str(u) for u in units_in)} out={unit}"
        )
    total_in = sum(float(q["quantity"]) for q in inputs)
    total_out = sum(float(q["quantity"]) for q in outputs)
    return BalanceResult(
        balanced=total_out <= total_in + 1e-9,
        inputs=total_in,
        outputs=total_out,
        loss=round(total_in - total_out, 9),
    )
