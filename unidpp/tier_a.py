"""The Tier-A carrier codec (the native framing, R11's unification):
the tag-length-value encoding the issuers mint and the offline CLI
decodes, now readable in Python. The decoder mirrors unidpp-core's
tier_a packer byte for byte; the re-encoder exists for one purpose —
reconstructing the signing body (the payload canonical bytes without
its signature block) so a verifier checks each slot's signature over
exactly what the issuer signed. Stdlib only; the payload document is
a plain dict with the snake_case keys the corpus fixtures pin.
"""

from __future__ import annotations

__all__ = [
    "decode_tier_a",
    "decode_tier_a_hex",
    "encode_tier_a",
    "tier_a_signing_body",
]

TAG_PRODUCT_ID = 0x01
TAG_RESOLVER_URI = 0x02
TAG_PASSPORT_ID = 0x03
TAG_EO_ID = 0x04
TAG_STATUS = 0x05
TAG_SAFETY = 0x06
TAG_VALIDITY_FROM = 0x07
TAG_VALIDITY_TO = 0x08
TAG_AS_OF = 0x09
TAG_LOG_HEAD = 0x0A
TAG_SIG_COUNT = 0x0B
TAG_SIG_SLOT = 0x0C
SIG_PLACEHOLDER = 0xFFFF

SUITE_BY_CODE = {
    1: "ecdsa-p256",
    2: "sm2",
    3: "ml-dsa-44",
    4: "ml-dsa-65",
    5: "ml-dsa-87",
}

STATUSES = [
    "issued",
    "suspended",
    "invalidated",
    "non-conformant",
    "consumed",
    "transformed",
    "end-of-waste",
    "archived",
]
SAFETIES = ["none", "recall-active", "security-flagged"]


class CarrierError(ValueError):
    """The carrier bytes are not a decodable native payload."""


class _Reader:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    def remaining(self) -> int:
        return len(self._data) - self._pos

    def _take(self, n: int) -> bytes:
        if self.remaining() < n:
            raise CarrierError(f"canonical stream truncated at offset {self._pos} (need {n} bytes)")
        out = self._data[self._pos : self._pos + n]
        self._pos += n
        return out

    def read_tag(self) -> int:
        return self._take(1)[0]

    def read_u16(self) -> int:
        b = self._take(2)
        return b[0] | (b[1] << 8)

    def read_u32(self) -> int:
        b = self._take(4)
        return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)

    def read_bytes(self) -> bytes:
        return self._take(self.read_u32())

    def read_str(self) -> str:
        return self.read_bytes().decode("utf-8")

    def read_opt_str(self) -> str | None:
        tag = self.read_tag()
        if tag == 0:
            return None
        if tag == 1:
            return self.read_str()
        raise CarrierError(f"bad optional tag {tag}")

    def read_opt_hash(self) -> str | None:
        tag = self.read_tag()
        if tag == 0:
            return None
        if tag == 1:
            return self._take(32).hex()
        raise CarrierError(f"bad optional tag {tag}")


def _require(value: str | None, field: str) -> str:
    if value is None:
        raise CarrierError(f"missing {field}")
    return value


def decode_tier_a(data: bytes) -> dict:
    """Decode the canonical carrier bytes into the payload document."""
    r = _Reader(data)
    product_id = resolver_uri = passport_id = eo_id = None
    status = safety = validity_from = as_of = None
    validity_to = log_head = None
    signatures: list[dict] = []
    while r.remaining() > 0:
        tag = r.read_tag()
        if tag == TAG_PRODUCT_ID:
            product_id = r.read_str()
        elif tag == TAG_RESOLVER_URI:
            resolver_uri = r.read_str()
        elif tag == TAG_PASSPORT_ID:
            passport_id = r.read_str()
        elif tag == TAG_EO_ID:
            eo_id = r.read_str()
        elif tag == TAG_STATUS:
            token = r.read_str()
            if token not in STATUSES:
                raise CarrierError(f"unknown status `{token}`")
            status = token
        elif tag == TAG_SAFETY:
            token = r.read_str()
            if token not in SAFETIES:
                raise CarrierError(f"unknown safety `{token}`")
            safety = token
        elif tag == TAG_VALIDITY_FROM:
            validity_from = r.read_str()
        elif tag == TAG_VALIDITY_TO:
            validity_to = r.read_opt_str()
        elif tag == TAG_AS_OF:
            as_of = r.read_str()
        elif tag == TAG_LOG_HEAD:
            log_head = r.read_opt_hash()
        elif tag == TAG_SIG_COUNT:
            count = r.read_tag()
            for _ in range(count):
                slot_tag = r.read_tag()
                if slot_tag != TAG_SIG_SLOT:
                    raise CarrierError(f"expected the signature-slot tag, read {slot_tag}")
                code = r.read_tag()
                suite = SUITE_BY_CODE.get(code)
                if suite is None:
                    raise CarrierError(f"unknown suite code {code}")
                key_id = r.read_bytes().decode("utf-8")
                length = r.read_u16()
                signature = None if length == SIG_PLACEHOLDER else r._take(length)
                signatures.append(
                    {
                        "suite": suite,
                        "key_id": key_id,
                        "signature": signature,
                    }
                )
        else:
            raise CarrierError(f"unknown field tag {tag}")
    return {
        "product_id": _require(product_id, "product_id"),
        "resolver_uri": _require(resolver_uri, "resolver_uri"),
        "passport_id": _require(passport_id, "passport_id"),
        "eo_id": _require(eo_id, "eo_id"),
        "status": _require(status, "status"),
        "safety": _require(safety, "safety"),
        "validity": {
            "from": _require(validity_from, "validity.from"),
            "to": validity_to,
        },
        "as_of": _require(as_of, "as_of"),
        "log_head": log_head,
        "signatures": signatures,
    }


def decode_tier_a_hex(hex_text: str) -> dict:
    """Decode the hex form the issuer's mint response carries."""
    if len(hex_text) % 2 != 0:
        raise CarrierError("the carrier hex is odd-length")
    return decode_tier_a(bytes.fromhex(hex_text))


class _Writer:
    def __init__(self) -> None:
        self._parts = bytearray()

    def write_tag(self, tag: int) -> None:
        self._parts.append(tag)

    def write_u16(self, value: int) -> None:
        self._parts += bytes((value & 0xFF, (value >> 8) & 0xFF))

    def write_u32(self, value: int) -> None:
        self._parts += bytes(
            (value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF, (value >> 24) & 0xFF)
        )

    def write_bytes(self, data: bytes) -> None:
        self.write_u32(len(data))
        self._parts += data

    def write_str(self, text: str) -> None:
        self.write_bytes(text.encode("utf-8"))

    def write_opt_str(self, text: str | None) -> None:
        if text is None:
            self.write_tag(0)
        else:
            self.write_tag(1)
            self.write_str(text)

    def write_opt_hash(self, hex_text: str | None) -> None:
        if hex_text is None:
            self.write_tag(0)
            return
        self.write_tag(1)
        self._parts += bytes.fromhex(hex_text)

    def into_bytes(self) -> bytes:
        return bytes(self._parts)


_CODE_BY_SUITE = {suite: code for code, suite in SUITE_BY_CODE.items()}


def _write_payload(w: _Writer, payload: dict) -> None:
    w.write_tag(TAG_PRODUCT_ID)
    w.write_str(payload["product_id"])
    w.write_tag(TAG_RESOLVER_URI)
    w.write_str(payload["resolver_uri"])
    w.write_tag(TAG_PASSPORT_ID)
    w.write_str(payload["passport_id"])
    w.write_tag(TAG_EO_ID)
    w.write_str(payload["eo_id"])
    w.write_tag(TAG_STATUS)
    w.write_str(payload["status"])
    w.write_tag(TAG_SAFETY)
    w.write_str(payload["safety"])
    w.write_tag(TAG_VALIDITY_FROM)
    w.write_str(payload["validity"]["from"])
    w.write_tag(TAG_VALIDITY_TO)
    w.write_opt_str(payload["validity"]["to"])
    w.write_tag(TAG_AS_OF)
    w.write_str(payload["as_of"])
    w.write_tag(TAG_LOG_HEAD)
    w.write_opt_hash(payload["log_head"])


def _write_signature_block(w: _Writer, signatures: list[dict]) -> None:
    w.write_tag(TAG_SIG_COUNT)
    w.write_tag(min(len(signatures), 255))
    for slot in signatures[:255]:
        w.write_tag(TAG_SIG_SLOT)
        code = _CODE_BY_SUITE.get(slot["suite"])
        if code is None:
            raise CarrierError(f"unknown suite `{slot['suite']}`")
        w.write_tag(code)
        w.write_bytes(slot["key_id"].encode("utf-8"))
        signature = slot["signature"]
        if signature is None:
            w.write_u16(SIG_PLACEHOLDER)
        else:
            if len(signature) > 0xFFFF:
                raise CarrierError(f"signature of {len(signature)} bytes exceeds u16 framing")
            w.write_u16(len(signature))
            w._parts += signature


def tier_a_signing_body(payload: dict) -> bytes:
    """The signing body: the payload's canonical bytes with the
    signature block omitted — what every slot's signature covers
    (framed in the ARTIFACT-EVENT domain by the verifier)."""
    w = _Writer()
    _write_payload(w, payload)
    w.write_tag(TAG_SIG_COUNT)
    w.write_tag(0)
    return w.into_bytes()


def encode_tier_a(payload: dict) -> bytes:
    """The carrier's full canonical bytes (the round trip's mirror)."""
    w = _Writer()
    _write_payload(w, payload)
    _write_signature_block(w, payload["signatures"])
    return w.into_bytes()
