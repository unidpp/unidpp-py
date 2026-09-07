"""EPCIS-style event JSON import.

Maps GS1 EPCIS 2.0 event shapes onto the UniDPP post-sale event taxonomy
(E1–E15). The mapping is deliberately conservative: anything that does not
carry a recognizable ``bizStep``/event-type combination raises
``UnsupportedEpcisEvent`` rather than being silently coerced.

Mapping table (EPCIS -> UniDPP):

============================  ==============================
EPCIS                         UniDPP
============================  ==============================
ObjectEvent, bizStep          passport.created
"commissioning" (action ADD)
AggregationEvent (ADD)        upgrade.install per child (E6)
  parent + childEPCs          (R3 installation; membership for
                              bizStep "packing")
TransformationEvent           material.decompose (E13) with
                              inputQuantityList/outputQuantityList
                              -> outputs + inputReferences
ObjectEvent, bizStep          custody.transfer (E1)
 "shipping"/"taking_charge"
ObjectEvent, bizStep          inspection.stamp (E14)
 "inspecting"
============================  ==============================
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from ..eventlog import Actor, BalanceResult, DomainEvent, mass_balance
from ..model import ModelError

__all__ = [
    "UnsupportedEpcisEvent",
    "map_epcis_event",
    "map_epcis_document",
    "transformation_balance",
]


class UnsupportedEpcisEvent(ModelError):
    """Raised when an EPCIS event has no faithful UniDPP mapping."""


_CUSTODY_STEPS = ("shipping", "taking_charge_of", "accepting", "retail_selling")
_INSTALL_STEPS = ("assembling", "installing", "packing")


def _event_time(evt: Mapping[str, Any]) -> str:
    ts = evt.get("eventTimeZone", None)
    when = evt.get("eventTime") or evt.get("eventDateTime")
    if not when:
        raise UnsupportedEpcisEvent("EPCIS event carries no eventTime")
    return str(when)


def _actor(evt: Mapping[str, Any], default_role: str = "economic-operator") -> Actor:
    # EPCIS 2.0 sensoring/actor is rare; fall back to the event's source list.
    source = evt.get("sourceList") or []
    if source and isinstance(source[0], Mapping):
        sid = source[0].get("source") or "urn:epcis:actor:unknown"
        return Actor(str(sid), default_role)
    return Actor("urn:epcis:actor:unknown", default_role)


def _epc_to_subject(epc: Any) -> str:
    return str(epc)


def _quantity_entries(qs: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for q in qs or []:
        if not isinstance(q, Mapping):
            continue
        epc = q.get("epcClass") or q.get("epc") or "urn:epcis:id:sgtin:unknown"
        out.append(
            {
                "passportId": _epc_to_subject(epc),
                "quantity": float(q.get("quantity", 0.0)),
                "unit": q.get("uom", "EA"),
            }
        )
    return out


def map_epcis_event(evt: Mapping[str, Any]) -> list[DomainEvent]:
    """Map one EPCIS event to zero or more UniDPP DomainEvents (uncommitted).

    Returned events have empty ``prev_commitment`` and no commitment —
    feed them through :func:`unidpp.eventlog.append_event` to chain them.
    """
    etype = evt.get("type") or evt.get("@type") or ""
    when = _event_time(evt)
    biz_step = (evt.get("bizStep") or "").split(":")[-1]

    if etype in ("AggregationEvent", "AggregationEventType") or (
        not etype and _looks_aggregation(evt)
    ):
        return _map_aggregation(evt, when, biz_step)

    if etype in ("TransformationEvent", "TransformationEventType") or (
        not etype and _looks_transformation(evt)
    ):
        return _map_transformation(evt, when)

    if etype in ("ObjectEvent", "ObjectEventType") or _looks_object(evt):
        return _map_object(evt, when, biz_step)

    raise UnsupportedEpcisEvent(f"unrecognized EPCIS event type: {etype!r}")


def _map_object(evt: Mapping[str, Any], when: str, biz_step: str) -> list[DomainEvent]:
    actor = _actor(evt)
    out: list[DomainEvent] = []
    epcs = [e for e in (evt.get("epcList") or []) if isinstance(e, str)]
    if biz_step == "commissioning":
        if epcs:
            out.append(
                DomainEvent(
                    event_id=f"epcis-{uuid.uuid5(uuid.NAMESPACE_URL, epcs[0] + when)}",
                    type="passport.created",
                    subject=_epc_to_subject(epcs[0]),
                    occurred_at=when,
                    actor=actor,
                    payload={"profileIds": []},
                    trust_marker="self-declared",
                    prev_commitment="",
                )
            )
    elif biz_step in _CUSTODY_STEPS:
        if not epcs:
            raise UnsupportedEpcisEvent("custody event without epcList")
        out.append(
            DomainEvent(
                event_id=f"epcis-{uuid.uuid5(uuid.NAMESPACE_URL, epcs[0] + when + 'custody')}",
                type="custody.transfer",
                subject=_epc_to_subject(epcs[0]),
                occurred_at=when,
                actor=Actor("urn:epcis:actor:custodian", "custodian"),
                payload={
                    "fromActor": {"actorId": "urn:epcis:actor:previous", "role": "custodian"},
                    "toActor": {"actorId": "urn:epcis:actor:next", "role": "custodian"},
                    "conveyance": biz_step,
                },
                trust_marker="self-declared",
                prev_commitment="",
            )
        )
    elif biz_step == "inspecting":
        if epcs:
            out.append(
                DomainEvent(
                    event_id=f"epcis-{uuid.uuid5(uuid.NAMESPACE_URL, epcs[0] + when + 'inspect')}",
                    type="inspection.stamp",
                    subject=_epc_to_subject(epcs[0]),
                    occurred_at=when,
                    actor=Actor("urn:epcis:actor:verifier", "verifier"),
                    payload={
                        "lensId": "urn:unidpp:lens:epcis-import",
                        "lensVersion": "1.0.0",
                        "mode": "snapshot",
                        "verdictSummary": "observed",
                    },
                    trust_marker="self-declared",
                    prev_commitment="",
                )
            )
    else:
        raise UnsupportedEpcisEvent(
            f"ObjectEvent bizStep {biz_step!r} has no UniDPP mapping"
        )
    return out


def _map_aggregation(evt: Mapping[str, Any], when: str, biz_step: str) -> list[DomainEvent]:
    parent = evt.get("parentID")
    if not parent:
        raise UnsupportedEpcisEvent("aggregation event without parentID")
    children = [
        c for c in (evt.get("childEPCs") or evt.get("childQuantityList") or []) if isinstance(c, str)
    ]
    action = evt.get("action", "ADD")
    if action != "ADD":
        raise UnsupportedEpcisEvent(
            f"aggregation action {action!r} not mapped (disassembly is an R3 uninstall, not an EPCIS import)"
        )
    out: list[DomainEvent] = []
    for child in children or ["urn:epcis:child:unknown"]:
        out.append(
            DomainEvent(
                event_id=f"epcis-{uuid.uuid5(uuid.NAMESPACE_URL, parent + child + when)}",
                type="upgrade.install",
                subject=_epc_to_subject(parent),
                occurred_at=when,
                actor=Actor("urn:epcis:actor:installer", "installer"),
                payload={
                    "childId": _epc_to_subject(child),
                    "parentSlot": "epcis-aggregation",
                    "pairing": "none",
                    "method": "epcis-aggregation",
                    "recoverability": "restorable",
                    "visibilityEdge": "public",
                },
                trust_marker="self-declared",
                prev_commitment="",
            )
        )
    return out


def _map_transformation(evt: Mapping[str, Any], when: str) -> list[DomainEvent]:
    outputs = _quantity_entries(evt.get("outputQuantityList"))
    inputs = _quantity_entries(evt.get("inputQuantityList"))
    if not outputs:
        raise UnsupportedEpcisEvent("transformation event without outputQuantityList")
    subject = (
        evt.get("transformationID")
        or (outputs[0]["passportId"] if outputs else "urn:epcis:transformation")
    )
    payload: dict[str, Any] = {"outputs": outputs}
    if inputs:
        payload["inputReferences"] = [
            {"passportId": q["passportId"], "quantity": q["quantity"], "stateHash": ""}
            for q in inputs
        ]
    return [
        DomainEvent(
            event_id=f"epcis-{uuid.uuid5(uuid.NAMESPACE_URL, str(subject) + when)}",
            type="material.decompose",
            subject=_epc_to_subject(subject),
            occurred_at=when,
            actor=Actor("urn:epcis:actor:transformer", "economic-operator"),
            payload=payload,
            trust_marker="self-declared",
            prev_commitment="",
        )
    ]


def _infer_type(evt: Mapping[str, Any]) -> str:
    if _looks_aggregation(evt):
        return "AggregationEvent"
    if _looks_transformation(evt):
        return "TransformationEvent"
    if _looks_object(evt):
        return "ObjectEvent"
    return ""


def _looks_object(evt: Mapping[str, Any]) -> bool:
    return "epcList" in evt or "action" in evt


def _looks_aggregation(evt: Mapping[str, Any]) -> bool:
    return "parentID" in evt and ("childEPCs" in evt or "childQuantityList" in evt)


def _looks_transformation(evt: Mapping[str, Any]) -> bool:
    return "inputQuantityList" in evt or "outputQuantityList" in evt


def map_epcis_document(doc: Mapping[str, Any]) -> list[DomainEvent]:
    """Map an EPCISDocument (eventList) to uncommitted DomainEvents."""
    events_field = None
    for key in ("eventList", "@eventList", "epcisBody"):
        if key in doc:
            events_field = doc[key]
            break
    if events_field is None:
        raise UnsupportedEpcisEvent("no eventList in EPCIS document")
    if isinstance(events_field, Mapping) and "eventList" in events_field:
        events_field = events_field["eventList"]
    out: list[DomainEvent] = []
    for evt in events_field:
        out.extend(map_epcis_event(evt))
    return out


def transformation_balance(evt: DomainEvent) -> BalanceResult:
    """Mass balance for a mapped transformation (in - out = loss >= 0)."""
    if evt.type != "material.decompose":
        raise ModelError(f"not a transformation event: {evt.type}")
    inputs = evt.payload.get("inputReferences") or []
    outs = evt.payload.get("outputs") or []
    return mass_balance(inputs, outs)
