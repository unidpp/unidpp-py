"""Adapters: EPCIS event import (commissioning/aggregation/transformation)
and UNTP passport stub parsing."""

from typing import ClassVar

import pytest

from unidpp.adapters import map_epcis_event, parse_untp_stub, transformation_balance
from unidpp.adapters.epcis import UnsupportedEpcisEvent, map_epcis_document
from unidpp.eventlog import append_event, verify_chain
from unidpp.model import ModelError, validate_event, validate_manifest


class TestEpcisCommissioning:
    def test_maps_to_passport_created(self):
        events = map_epcis_event(
            {
                "type": "ObjectEvent",
                "action": "ADD",
                "bizStep": "urn:epcglobal:cbv:bizstep:commissioning",
                "eventTime": "2026-09-01T10:00:00.000Z",
                "epcList": ["urn:epc:id:sgtin:0614141.107346.2017"],
            }
        )
        assert len(events) == 1
        evt = events[0]
        assert evt.type == "passport.created"
        assert evt.subject == "urn:epc:id:sgtin:0614141.107346.2017"
        chained = append_event([], evt)
        assert validate_event(chained[0]).valid

    def test_mapped_events_chain(self):
        log: list = []
        log = append_event(
            log,
            map_epcis_event(
                {
                    "type": "ObjectEvent",
                    "action": "ADD",
                    "bizStep": "commissioning",
                    "eventTime": "2026-09-01T10:00:00Z",
                    "epcList": ["urn:epc:id:sgtin:0614141.107346.2017"],
                }
            )[0],
        )
        assert verify_chain(log)


class TestEpcisAggregation:
    def test_maps_to_upgrade_install_per_child(self):
        events = map_epcis_event(
            {
                "type": "AggregationEvent",
                "action": "ADD",
                "eventTime": "2026-09-02T10:00:00Z",
                "parentID": "urn:epc:id:sscc:0614141.1234567890",
                "childEPCs": [
                    "urn:epc:id:sgtin:0614141.107346.2017",
                    "urn:epc:id:sgtin:0614141.107346.2018",
                ],
            }
        )
        assert [e.type for e in events] == ["upgrade.install", "upgrade.install"]
        assert {e.payload["childId"] for e in events} == {
            "urn:epc:id:sgtin:0614141.107346.2017",
            "urn:epc:id:sgtin:0614141.107346.2018",
        }
        log: list = []
        for e in events:
            log = append_event(log, e)
        for e in log:
            assert validate_event(e).valid

    def test_delete_action_not_mapped(self):
        with pytest.raises(UnsupportedEpcisEvent):
            map_epcis_event(
                {
                    "type": "AggregationEvent",
                    "action": "DELETE",
                    "eventTime": "2026-09-02T10:00:00Z",
                    "parentID": "urn:x",
                    "childEPCs": ["urn:y"],
                }
            )


class TestEpcisTransformation:
    def _evt(self, outputs, inputs):
        return map_epcis_event(
            {
                "type": "TransformationEvent",
                "eventTime": "2029-01-15T08:00:00Z",
                "transformationID": "urn:x:recycle-run-1",
                "inputQuantityList": inputs,
                "outputQuantityList": outputs,
            }
        )[0]

    def test_maps_to_material_decompose_with_references(self):
        evt = self._evt(
            outputs=[
                {"epcClass": "urn:x:cells", "quantity": 40.0, "uom": "KGM"},
                {"epcClass": "urn:x:casing", "quantity": 8.0, "uom": "KGM"},
                {"epcClass": "urn:x:electronics", "quantity": 5.0, "uom": "KGM"},
            ],
            inputs=[{"epcClass": "urn:x:battery", "quantity": 53.0, "uom": "KGM"}],
        )
        assert evt.type == "material.decompose"
        assert evt.payload["inputReferences"][0]["passportId"] == "urn:x:battery"
        assert validate_event(append_event([], evt)[0]).valid
        balance = transformation_balance(evt)
        assert balance.balanced and balance.loss == 0.0

    def test_mass_violation_detected(self):
        evt = self._evt(
            outputs=[{"epcClass": "urn:x:gold", "quantity": 60.0, "uom": "KGM"}],
            inputs=[{"epcClass": "urn:x:battery", "quantity": 53.0, "uom": "KGM"}],
        )
        assert not transformation_balance(evt).balanced

    def test_balance_requires_transformation_event(self):
        evt = self._evt(
            outputs=[{"epcClass": "urn:x:cells", "quantity": 1.0, "uom": "KGM"}],
            inputs=None,
        )
        evt.type = "inspection.stamp"  # not a transformation
        with pytest.raises(ModelError):
            transformation_balance(evt)

    def test_document_mapping(self):
        doc = {
            "@context": ["https://ref.gs1.org/standards/epcis/epcis-2.0.json"],
            "type": "EPCISDocument",
            "eventList": [
                {
                    "type": "ObjectEvent",
                    "action": "ADD",
                    "bizStep": "commissioning",
                    "eventTime": "2026-09-01T10:00:00Z",
                    "epcList": ["urn:epc:id:sgtin:0614141.107346.2017"],
                },
                {
                    "type": "AggregationEvent",
                    "action": "ADD",
                    "eventTime": "2026-09-02T10:00:00Z",
                    "parentID": "urn:x:kit",
                    "childEPCs": ["urn:epc:id:sgtin:0614141.107346.2017"],
                },
            ],
        }
        events = map_epcis_document(doc)
        assert [e.type for e in events] == ["passport.created", "upgrade.install"]
        log: list = []
        for e in events:
            log = append_event(log, e)
        assert verify_chain(log)


class TestUntpStub:
    STUB: ClassVar[dict] = {
        "@context": ["https://ref.gs1.org/gs1/v/model"],
        "type": "ProductPassport",
        "id": "https://example.com/passports/123",
        "productIdentifiers": [
            {"scheme": "https://gs1.org/voc/", "value": "(01)09506000134352(21)BP52-000841"}
        ],
        "passportIssuer": {"id": "urn:example:issuer:1", "name": "Example Cells"},
        "validFrom": "2026-09-01T00:00:00Z",
        "validUntil": "2036-09-01T00:00:00Z",
        "standardsConformance": [
            {"standard": "ESPR", "conformanceVersion": "1"}
        ],
    }

    def test_parse_into_neutral_manifest(self):
        manifest = parse_untp_stub(self.STUB, as_of="2026-09-05T00:00:00Z")
        assert manifest.subject_id.scheme == "gs1"
        assert manifest.subject_id.value == "(01)09506000134352(21)BP52-000841"
        assert manifest.status == "active"
        assert manifest.profiles[0].profile_id == "ESPR"
        assert manifest.event_log.log_uri == "https://example.com/passports/123"
        assert validate_manifest(manifest).valid

    def test_import_receipt_commitment_is_stable(self):
        m1 = parse_untp_stub(self.STUB, as_of="2026-09-05T00:00:00Z")
        m2 = parse_untp_stub(self.STUB, as_of="2026-09-05T00:00:00Z")
        assert m1.event_log.commitment == m2.event_log.commitment
        assert len(m1.event_log.commitment) == 64

    def test_rejects_non_passport(self):
        with pytest.raises(ValueError):
            parse_untp_stub({"type": "DeliveryNote"}, as_of="2026-09-05T00:00:00Z")

    def test_rejects_stub_without_identifiers(self):
        with pytest.raises(ValueError):
            parse_untp_stub({"type": "ProductPassport"}, as_of="2026-09-05T00:00:00Z")
