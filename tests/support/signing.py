"""Ed25519 keys and detached signatures, made without publet's code.

A scenario about signatures needs objects signed the way Section 4.4 says,
so that what is checked is the implementation against the specification, and
not the implementation against itself.
"""

from __future__ import annotations

import hashlib

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from support.objects import cid_of, head, obj, text

CREATED = "2026-11-03T00:00:00Z"


def bstr(data: bytes) -> bytes:
    return head(2, len(data)) + data


class Key:
    """A key named by `seed`, with its `key` object (Section 10.1)."""

    def __init__(self, seed: str, principal: str | None = "human"):
        self.private = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(seed.encode()).digest())
        public = self.private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        fields = [("alg", text("ed25519")), ("pubkey", bstr(public))]
        if principal is not None:
            fields.append(("principal", text(principal)))
        self.object = obj("key", cid_of(public), CREATED, fields)
        self.cid = cid_of(self.object)

    def sign(self, target: bytes, purpose: str = "authored", value: bytes | None = None) -> bytes:
        """A `sig` object over `target`, or with `value` as its signature instead."""
        message = b"pub/v1/sig\x00" + purpose.encode() + b"\x00" + target
        return obj("sig", self.cid, CREATED, [
            ("target", text(cid_of(target))), ("alg", text("ed25519")),
            ("value", bstr(value if value is not None else self.private.sign(message))),
            ("purpose", text(purpose)),
        ])
