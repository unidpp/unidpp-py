"""Laptop pilot fixture (PLAN.md stream 11 deliverable), ported from
``unidpp-ts/packages/model/src/fixtures/laptop.ts``.

A laptop with EU and JP jurisdiction profiles on ONE neutral core — no
region is the universal envelope. Child references compose by identity
reference, never data copying. Deterministic timestamps; commitments
computed on build.
"""

from __future__ import annotations

from typing import Any

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

LAPTOP_TYPE_ID = ProductIdentifier(
    scheme="iso-15459",
    value="urn:iso:std:iso-iec:15459:unidpp:type:lat-7",
    granularity="model",
    state="live",
)

LAPTOP_INSTANCE_ID = ProductIdentifier(
    scheme="iso-15459",
    value="urn:iso:std:iso-iec:15459:unidpp:inst:84120099012345",
    granularity="item",
    state="live",
)

LAPTOP_PASSPORT_ID = ProductIdentifier(
    scheme="iso-15459",
    value="urn:iso:std:iso-iec:15459:unidpp:passport:84120099012345",
    granularity="item",
    state="live",
)

EU_ELECTRONICS_PROFILE = ProfileDefinition(
    profile_id="urn:unidpp:profile:eu-espr-electronics",
    version="1.3.0",
    owner="eu:espr:commission",
    legal_basis="ESPR 2024/1781, electronics delegated act",
    axis=ProfileAxis(jurisdiction="EU", sector="electronics"),
    data_points=[
        RegistryItemRef("urn:unidpp:register:core", "de.dpp.operator-id", "1.0.0"),
        RegistryItemRef("urn:unidpp:register:core", "de.dpp.reparability-score", "1.1.0"),
        RegistryItemRef("urn:unidpp:register:core", "de.dpp.carbon-footprint", "1.2.0"),
    ],
    languages=["en", "fr", "de"],
    trust_requirements=TrustRequirements(
        suites=["ecdsa-p384-sha384", "ml-dsa-65"],
        trust_list="urn:unidpp:trustlist:eu",
        minimum_marker="third-party-attested",
    ),
    resolution=None,
)
EU_ELECTRONICS_PROFILE.resolution = None

JP_PSE_PROFILE = ProfileDefinition(
    profile_id="urn:unidpp:profile:jp-meti-pse",
    version="2026.2",
    owner="jp:meti",
    legal_basis="電気用品安全法 (Denki-Yōhin-Anzen-Hō) technical requirements",
    axis=ProfileAxis(jurisdiction="JP", sector="electronics"),
    data_points=[
        RegistryItemRef("urn:unidpp:register:core", "de.dpp.operator-id", "1.0.0"),
        RegistryItemRef("urn:unidpp:register:jp", "de.jp.pse-mark", "2.0.0"),
        RegistryItemRef("urn:unidpp:register:jp", "de.jp.top-runner-class", "2026.1"),
    ],
    transforms=[
        RegistryItemRef("urn:unidpp:register:jp", "tr.jp.top-runner-binning", "2026.1"),
    ],
    languages=["ja", "en"],
    trust_requirements=TrustRequirements(
        suites=["ecdsa-p256-sha256"],
        trust_list="urn:unidpp:trustlist:jp",
        minimum_marker="self-declared",
    ),
)

# Child references: composition by reference, each child resolvable elsewhere.
LAPTOP_CHILDREN = [
    ChildReference(
        child_id="urn:unidpp:passport:battery-pack-bp52-000841",
        relationship="installation",
        slot_id="battery-bay-1",
        pairing="firmware",
        binding=InstallationBinding("socketed-latch", "harvestable"),
        visibility=VisibilityClause("blind"),  # consumer install edge: personal data by default
    ),
    ChildReference(
        child_id="urn:unidpp:passport:sodimm-16g-aa117-0042",
        relationship="installation",
        slot_id="sodimm-0",
        binding=InstallationBinding("socketed", "restorable"),
        visibility=VisibilityClause("restricted", audiences=["repairer", "regulator"]),
    ),
    ChildReference(
        child_id="urn:unidpp:passport:sodimm-16g-aa117-0043",
        relationship="installation",
        slot_id="sodimm-1",
        binding=InstallationBinding("socketed", "restorable"),
        visibility=VisibilityClause("restricted", audiences=["repairer", "regulator"]),
    ),
    ChildReference(
        # Absorbed under the current regime: glued display module, lot-recorded
        # dormant identifier — issuable by adoption when a display regime lands.
        child_id="urn:unidpp:id:display-lot-d14-2026q3",
        relationship="installation",
        slot_id="display-lid-1",
        binding=InstallationBinding("bonded-adhesive", "absorbing"),
        visibility=VisibilityClause("restricted", audiences=["regulator"]),
        dormant=True,
    ),
]

SUBJECT = "urn:iso:std:iso-iec:15459:unidpp:inst:84120099012345"


def build_laptop_event_log() -> list[DomainEvent]:
    log: list[DomainEvent] = []
    log = append_event(
        log,
        DomainEvent(
            event_id="evt-lap-001",
            type="passport.created",
            subject=SUBJECT,
            occurred_at="2026-08-03T09:15:00Z",
            actor=Actor("urn:unidpp:actor:oem-nordwave", "economic-operator"),
            payload={
                "typeRef": "urn:iso:std:iso-iec:15459:unidpp:type:lat-7@hw-rev-b",
                "profileIds": ["urn:unidpp:profile:eu-espr-electronics"],
            },
            trust_marker="third-party-attested",
            prev_commitment="",
        ),
    )
    log = append_event(
        log,
        DomainEvent(
            event_id="evt-lap-002",
            type="profile.binding",
            subject=SUBJECT,
            occurred_at="2026-08-03T09:15:01Z",
            actor=Actor("urn:unidpp:actor:oem-nordwave", "economic-operator"),
            payload={
                "profileId": "urn:unidpp:profile:jp-meti-pse",
                "version": "2026.2",
                "from": "2026-10-01T00:00:00Z",
            },
            trust_marker="third-party-attested",
            prev_commitment="",
        ),
    )
    log = append_event(
        log,
        DomainEvent(
            event_id="evt-lap-003",
            type="custody.transfer",
            subject=SUBJECT,
            occurred_at="2026-08-20T14:02:00Z",
            actor=Actor("urn:unidpp:actor:retailer-kyoto-denshi", "custodian"),
            payload={
                "fromActor": {"actorId": "urn:unidpp:actor:oem-nordwave", "role": "economic-operator"},
                "toActor": {"actorId": "urn:unidpp:actor:consumer-anon-1", "role": "custodian"},
                "conveyance": "retail-sale",
            },
            trust_marker="self-declared",
            prev_commitment="",
        ),
    )
    log = append_event(
        log,
        DomainEvent(
            event_id="evt-lap-004",
            type="software.update",
            subject=SUBJECT,
            occurred_at="2026-11-05T02:30:00Z",
            actor=Actor("urn:unidpp:actor:oem-nordwave", "economic-operator"),
            payload={"component": "system-firmware", "fromVersion": "1.04", "toVersion": "1.07"},
            trust_marker="self-declared",
            prev_commitment="",
        ),
    )
    log = append_event(
        log,
        DomainEvent(
            event_id="evt-lap-005",
            type="part.replace",
            subject=SUBJECT,
            occurred_at="2027-02-11T10:44:00Z",
            actor=Actor("urn:unidpp:actor:repair-shibuya", "repairer"),
            payload={
                "removedChildId": "urn:unidpp:passport:sodimm-16g-aa117-0042",
                "installedChildId": "urn:unidpp:passport:sodimm-32g-aa119-0007",
                "likeForLike": False,
                "slotId": "sodimm-0",
            },
            trust_marker="third-party-attested",
            prev_commitment="",
        ),
    )
    return log


class LaptopFixture:
    def __init__(
        self,
        manifest: PassportManifest,
        events: list[DomainEvent],
        profiles: list[ProfileDefinition],
        links: list[PassportLink],
    ) -> None:
        self.manifest = manifest
        self.events = events
        self.profiles = profiles
        self.links = links


def build_laptop() -> LaptopFixture:
    events = build_laptop_event_log()
    head = log_head(events)
    manifest = PassportManifest(
        passport_id=LAPTOP_PASSPORT_ID,
        subject_id=LAPTOP_INSTANCE_ID,
        type_ref=TypeReference(
            type_id=LAPTOP_TYPE_ID,
            type_version="hw-rev-b",
            configuration_vector=["ram-2x16g", "ssd-512g", "display-14"],
        ),
        status="active",
        profiles=[
            ProfileBinding(
                profile_id="urn:unidpp:profile:eu-espr-electronics",
                version="1.3.0",
                effective=EffectiveWindow(from_="2027-01-01T00:00:00Z"),
                binding_event_id="evt-lap-001",
            ),
            ProfileBinding(
                profile_id="urn:unidpp:profile:jp-meti-pse",
                version="2026.2",
                effective=EffectiveWindow(from_="2026-10-01T00:00:00Z"),
                binding_event_id="evt-lap-002",
            ),
        ],
        children=LAPTOP_CHILDREN,
        event_log=EventLogPointer(
            log_uri="https://logs.unidpp.org/84120099012345",
            commitment=head["commitment"],
            height=head["height"],
        ),
        capability_class="S0",
        as_of="2027-02-11T10:44:00Z",
    )
    links = [
        PassportLink(
            type="installation",
            from_="urn:unidpp:passport:battery-pack-bp52-000841",
            to="urn:iso:std:iso-iec:15459:unidpp:passport:84120099012345",
            direction="up",
            interval_from="2026-08-03T09:15:00Z",
            binding=InstallationBinding("socketed-latch", "harvestable"),
            slot_id="battery-bay-1",
            pairing="firmware",
            visibility=VisibilityClause("blind"),
            # Deviation from the TS fixture (which carries a decorative
            # placeholder): compute the real salted blind-edge commitment,
            # same discipline as the car fixture. The wire schema requires
            # ^[0-9a-f]{64}$, which the TS placeholder violates.
            parent_commitment=commitment(
                {"parent": LAPTOP_PASSPORT_ID.value, "slot": "battery-bay-1"},
                "salt-bp52-000841",
            ),
        ),
    ]
    return LaptopFixture(
        manifest=manifest,
        events=events,
        profiles=[EU_ELECTRONICS_PROFILE, JP_PSE_PROFILE],
        links=links,
    )
