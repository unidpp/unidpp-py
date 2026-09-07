"""Car example (the UniDPP design framework P4 pilot core), ported from
``unidpp-ts/packages/model/src/fixtures/car.ts``.

Composite products are a federation of passports, not one mega-passport.
The car has one passport; the battery — independently regulated — has its
own, joined by typed child references. The single QR on the car resolves
the car's identity; children join by identity reference, never by data
copying. Dormant cell-lot identifiers record absorption at finest
available granularity (I3).
"""

from __future__ import annotations

from ..canonical import commitment
from ..eventlog import Actor, DomainEvent, append_event, log_head
from ..model import (
    ChildReference,
    EffectiveWindow,
    EventLogPointer,
    InstallationBinding,
    PassportLink,
    PassportManifest,
    ProductIdentifier,
    ProfileAxis,
    ProfileBinding,
    ProfileDefinition,
    RegistryItemRef,
    TrustRequirements,
    TypeReference,
    VisibilityClause,
)

CAR_INSTANCE_ID = ProductIdentifier(
    scheme="vin",
    value="WVWZZZ1JZXW000841",
    granularity="item",
    state="live",
)

CAR_PASSPORT_ID = ProductIdentifier(
    scheme="iso-15459",
    value="urn:iso:std:iso-iec:15459:unidpp:passport:car-wvwzzz1jzxw000841",
    granularity="item",
    state="live",
)

BATTERY_SUBJECT_ID = ProductIdentifier(
    scheme="gs1",
    value="(01)09506000134352(21)BP52-000841",
    granularity="item",
    state="live",
)

BATTERY_PASSPORT_ID = ProductIdentifier(
    scheme="iso-15459",
    value="urn:iso:std:iso-iec:15459:unidpp:passport:battery-pack-bp52-000841",
    granularity="item",
    state="live",
)

EU_VEHICLE_PROFILE = ProfileDefinition(
    profile_id="urn:unidpp:profile:eu-vehicle-type-approval",
    version="2.1.0",
    owner="eu:commission-dg-grow",
    legal_basis="Reg (EU) 2018/858 type approval + ESPR 2024/1781 vehicle carve-outs",
    axis=ProfileAxis(jurisdiction="EU", sector="automotive"),
    data_points=[
        RegistryItemRef("urn:unidpp:register:core", "de.dpp.operator-id", "1.0.0"),
        RegistryItemRef("urn:unidpp:register:core", "de.vehicle.type-approval-no", "1.0.0"),
    ],
    languages=["en"],
    trust_requirements=TrustRequirements(
        suites=["ecdsa-p384-sha384"],
        trust_list="urn:unidpp:trustlist:eu",
        minimum_marker="third-party-attested",
    ),
)

EU_BATTERY_PROFILE = ProfileDefinition(
    profile_id="urn:unidpp:profile:eu-battery-2023-1542",
    version="1.0.0",
    owner="eu:commission-dg-env",
    legal_basis="Reg (EU) 2023/1542 battery passport, Art. 77",
    axis=ProfileAxis(jurisdiction="EU", sector="batteries"),
    data_points=[
        RegistryItemRef("urn:unidpp:register:core", "de.dpp.operator-id", "1.0.0"),
        RegistryItemRef("urn:unidpp:register:core", "de.battery.chemistry", "1.0.0"),
        RegistryItemRef("urn:unidpp:register:core", "de.battery.carbon-footprint", "1.3.0"),
        RegistryItemRef("urn:unidpp:register:core", "de.battery.recycled-content", "1.1.0"),
        RegistryItemRef("urn:unidpp:register:core", "de.battery.due-diligence", "1.0.0"),
    ],
    languages=["en", "fr", "de"],
    trust_requirements=TrustRequirements(
        suites=["ecdsa-p384-sha384"],
        trust_list="urn:unidpp:trustlist:eu",
        minimum_marker="third-party-attested",
    ),
)

# Battery's own manifest: cells absorbed (no passport under the current
# regime), lot-recorded dormant identifiers for future adoption (I3).
BATTERY_CHILDREN = [
    ChildReference(
        child_id="urn:unidpp:id:cell-lot-c75-2026b-0001",
        relationship="derivation",
        binding=InstallationBinding("welded-module-assembly", "absorbing"),
        visibility=VisibilityClause("restricted", audiences=["regulator", "recycler"]),
        dormant=True,
    ),
    ChildReference(
        child_id="urn:unidpp:id:cell-lot-c75-2026b-0002",
        relationship="derivation",
        binding=InstallationBinding("welded-module-assembly", "absorbing"),
        visibility=VisibilityClause("restricted", audiences=["regulator", "recycler"]),
        dormant=True,
    ),
]


def build_car_event_log() -> list[DomainEvent]:
    log: list[DomainEvent] = []
    log = append_event(
        log,
        DomainEvent(
            event_id="evt-car-001",
            type="passport.created",
            subject="urn:unidpp:subject:car-wvwzzz1jzxw000841",
            occurred_at="2026-09-12T08:00:00Z",
            actor=Actor("urn:unidpp:actor:oem-autowerke", "economic-operator"),
            payload={"profileIds": ["urn:unidpp:profile:eu-vehicle-type-approval"]},
            trust_marker="third-party-attested",
            prev_commitment="",
        ),
    )
    log = append_event(
        log,
        DomainEvent(
            event_id="evt-car-002",
            type="upgrade.install",
            subject="urn:unidpp:subject:car-wvwzzz1jzxw000841",
            occurred_at="2026-09-12T08:05:00Z",
            actor=Actor("urn:unidpp:actor:oem-autowerke", "installer"),
            payload={
                "childId": "urn:iso:std:iso-iec:15459:unidpp:passport:battery-pack-bp52-000841",
                "parentSlot": "traction-battery-1",
                "pairing": "firmware",
                "method": "bolted-busbar",
                "recoverability": "harvestable",
                "visibilityEdge": "blind",
            },
            trust_marker="third-party-attested",
            prev_commitment="",
        ),
    )
    log = append_event(
        log,
        DomainEvent(
            event_id="evt-car-003",
            type="custody.transfer",
            subject="urn:unidpp:subject:car-wvwzzz1jzxw000841",
            occurred_at="2026-10-01T16:20:00Z",
            actor=Actor("urn:unidpp:actor:dealer-lyon", "custodian"),
            payload={
                "fromActor": {"actorId": "urn:unidpp:actor:oem-autowerke", "role": "economic-operator"},
                "toActor": {"actorId": "urn:unidpp:actor:consumer-anon-2", "role": "custodian"},
                "conveyance": "retail-sale",
            },
            trust_marker="self-declared",
            prev_commitment="",
        ),
    )
    return log


def build_battery_event_log() -> list[DomainEvent]:
    log: list[DomainEvent] = []
    log = append_event(
        log,
        DomainEvent(
            event_id="evt-bat-001",
            type="passport.created",
            subject="urn:unidpp:subject:battery-pack-bp52-000841",
            occurred_at="2026-09-01T11:30:00Z",
            actor=Actor("urn:unidpp:actor:cellco-eu", "economic-operator"),
            payload={"profileIds": ["urn:unidpp:profile:eu-battery-2023-1542"]},
            trust_marker="third-party-attested",
            prev_commitment="",
        ),
    )
    log = append_event(
        log,
        DomainEvent(
            event_id="evt-bat-002",
            type="milestone.record",
            subject="urn:unidpp:subject:battery-pack-bp52-000841",
            occurred_at="2027-03-04T06:12:00Z",
            actor=Actor("urn:unidpp:device:bms-bp52-000841", "device"),
            payload={
                "commitment": "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
                "deviceKeyId": "urn:unidpp:key:bms-bp52-000841",
                "freshWithin": "P30D",
            },
            trust_marker="self-declared",
            prev_commitment="",
        ),
    )
    log = append_event(
        log,
        DomainEvent(
            event_id="evt-bat-003",
            type="recall.campaign",
            subject="urn:unidpp:subject:battery-pack-bp52-000841",
            occurred_at="2027-06-15T09:00:00Z",
            actor=Actor("urn:unidpp:actor:eu-market-surveillance", "regulator"),
            payload={
                "campaignRef": "urn:eu:recall:2027-06-batt-bp52",
                # Predicate-based recall: evaluated locally by custodians,
                # never enumerated centrally (I12).
                "predicate": "battery.firmware < 2.3.1 and cycle_count > 800",
            },
            trust_marker="log-anchored",
            prev_commitment="",
        ),
    )
    return log


class CarFixture:
    def __init__(
        self,
        car: dict,
        battery: dict,
        links: list[PassportLink],
        profiles: list[ProfileDefinition],
    ) -> None:
        self.car = car
        self.battery = battery
        self.links = links
        self.profiles = profiles


def build_car() -> CarFixture:
    car_events = build_car_event_log()
    battery_events = build_battery_event_log()
    car_head = log_head(car_events)
    battery_head = log_head(battery_events)

    car_manifest = PassportManifest(
        passport_id=CAR_PASSPORT_ID,
        subject_id=CAR_INSTANCE_ID,
        type_ref=TypeReference(
            type_id=ProductIdentifier(
                scheme="iso-15459",
                value="urn:iso:std:iso-iec:15459:unidpp:type:ev-c1",
                granularity="model",
                state="live",
            ),
            type_version="hw-rev-a",
        ),
        status="active",
        profiles=[
            ProfileBinding(
                profile_id="urn:unidpp:profile:eu-vehicle-type-approval",
                version="2.1.0",
                effective=EffectiveWindow(from_="2026-09-12T08:00:00Z"),
                binding_event_id="evt-car-001",
            ),
        ],
        children=[
            ChildReference(
                child_id="urn:iso:std:iso-iec:15459:unidpp:passport:battery-pack-bp52-000841",
                relationship="installation",
                slot_id="traction-battery-1",
                pairing="firmware",
                binding=InstallationBinding("bolted-busbar", "harvestable"),
                visibility=VisibilityClause("blind"),
            ),
        ],
        event_log=EventLogPointer(
            log_uri="https://logs.unidpp.org/car-wvwzzz1jzxw000841",
            commitment=car_head["commitment"],
            height=car_head["height"],
        ),
        capability_class="S2",
        as_of="2027-06-15T09:00:00Z",
    )

    battery_manifest = PassportManifest(
        passport_id=BATTERY_PASSPORT_ID,
        subject_id=BATTERY_SUBJECT_ID,
        status="active",
        profiles=[
            ProfileBinding(
                profile_id="urn:unidpp:profile:eu-battery-2023-1542",
                version="1.0.0",
                effective=EffectiveWindow(from_="2026-09-01T11:30:00Z"),
                binding_event_id="evt-bat-001",
            ),
        ],
        children=BATTERY_CHILDREN,
        event_log=EventLogPointer(
            log_uri="https://logs.unidpp.org/battery-pack-bp52-000841",
            commitment=battery_head["commitment"],
            height=battery_head["height"],
        ),
        capability_class="S2",
        as_of="2027-06-15T09:00:00Z",
    )

    # R3 edge: proof-of-binding without knowledge-of-parent — salted
    # commitment to the parent in the child's log.
    parent_commitment = commitment(
        {"parent": CAR_PASSPORT_ID.value, "slot": "traction-battery-1"},
        "salt-bp52-000841",
    )
    links = [
        PassportLink(
            type="installation",
            from_="urn:iso:std:iso-iec:15459:unidpp:passport:battery-pack-bp52-000841",
            to="urn:iso:std:iso-iec:15459:unidpp:passport:car-wvwzzz1jzxw000841",
            direction="up",
            interval_from="2026-09-12T08:05:00Z",
            binding=InstallationBinding("bolted-busbar", "harvestable"),
            slot_id="traction-battery-1",
            pairing="firmware",
            alteration=["busbar-torque-marked"],
            visibility=VisibilityClause("blind"),
            parent_commitment=parent_commitment,
        ),
        PassportLink(
            type="custody",
            from_="urn:unidpp:passport:car-wvwzzz1jzxw000841",
            to="urn:unidpp:actor:consumer-anon-2",
            direction="symmetric",
            interval_from="2026-10-01T16:20:00Z",
            visibility=VisibilityClause("blind"),
        ),
    ]

    return CarFixture(
        car={"manifest": car_manifest, "events": car_events},
        battery={"manifest": battery_manifest, "events": battery_events},
        links=links,
        profiles=[EU_VEHICLE_PROFILE, EU_BATTERY_PROFILE],
    )
