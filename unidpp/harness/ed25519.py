"""Pure-Python Ed25519 signatures (RFC 8032).

The foreign harness verifies AND issues real signatures without any
third-party dependency: the point is independence from the reference
stack, so even the cryptography is the RFC's own arithmetic. Signing
is the deterministic form the RFC specifies — the same seed and
message always produce the same signature, which is what makes a
foreign-issued signature acceptable to the reference verifier.
"""

from __future__ import annotations

import hashlib

__all__ = ["sign", "verify"]

_p = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_d = -121665 * pow(121666, _p - 2, _p) % _p
_I = pow(2, (_p - 1) // 4, _p)


def _recover_x(y: int, sign: int) -> int:
    if y >= _p:
        return None
    x2 = (y * y - 1) * pow(_d * y * y + 1, _p - 2, _p) % _p
    if x2 == 0:
        if sign:
            return None
        return 0
    x = pow(x2, (_p + 3) // 8, _p)
    if (x * x - x2) % _p != 0:
        x = x * _I % _p
    if (x * x - x2) % _p != 0:
        return None
    if (x & 1) != sign:
        x = _p - x
    return x


_BY = 4 * pow(5, _p - 2, _p) % _p
_Bx = _recover_x(_BY, 0)
_B = (_Bx, _BY, 1, _Bx * _BY % _p)


def _point_add(P, Q):
    A, B = (P[1] - P[0]) * (Q[1] - Q[0]) % _p, (P[1] + P[0]) * (Q[1] + Q[0]) % _p
    C, D = 2 * P[3] * Q[3] * _d % _p, 2 * P[2] * Q[2] % _p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _p, G * H % _p, F * G % _p, E * H % _p)


def _point_mul(s: int, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _point_add(Q, P)
        P = _point_add(P, P)
        s >>= 1
    return Q


def _point_equal(P, Q) -> bool:
    if (P[0] * Q[2] - Q[0] * P[2]) % _p != 0:
        return False
    return (P[1] * Q[2] - Q[1] * P[2]) % _p == 0


def _point_decompress(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _p)


def verify(public: bytes, message: bytes, signature: bytes) -> bool:
    """RFC 8032 Ed25519 verification."""
    if len(public) != 32 or len(signature) != 64:
        return False
    A = _point_decompress(public)
    if A is None:
        return False
    Rs = signature[:32]
    R = _point_decompress(Rs)
    if R is None:
        return False
    k = int.from_bytes(
        hashlib.sha512(Rs + public + message).digest(), "little"
    ) % _L
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:
        return False
    return _point_equal(_point_mul(8 * s, _B), _point_add(_point_mul(8, R), _point_mul(8 * k, A)))


def secret_expand(seed: bytes):
    """The RFC's scalar/nonce derivation from a 32-byte seed."""
    if len(seed) != 32:
        raise ValueError("the Ed25519 seed is 32 bytes")
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def _point_compress(P) -> bytes:
    zinv = pow(P[2], _p - 2, _p)
    x = P[0] * zinv % _p
    y = P[1] * zinv % _p
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _basepoint():
    # RFC 8032: B is the point with y = 4/5 and x even.
    y = 4 * pow(5, _p - 2, _p) % _p
    x = _recover_x(y, 0)
    if x & 1:
        x = _p - x
    return (x, y, 1, x * y % _p)


_B = _basepoint()


def sign(seed: bytes, message: bytes) -> tuple[bytes, bytes]:
    """RFC 8032 deterministic signing: returns (public, signature)."""
    a, prefix = secret_expand(seed)
    public = _point_compress(_point_mul(a, _B))
    r = int.from_bytes(
        hashlib.sha512(prefix + message).digest(), "little"
    ) % _L
    R = _point_compress(_point_mul(r, _B))
    k = (
        int.from_bytes(hashlib.sha512(R + public + message).digest(), "little")
        % _L
    )
    s = (r + k * a) % _L
    return public, R + int.to_bytes(s, 32, "little")
