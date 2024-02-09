from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from dataclasses import dataclass


@dataclass
class OfflineProfile(object):
    online = False
    display_name: str = "quarry"

    @classmethod
    def from_display_name(cls, display_name):
        return cls(display_name)

    def __hash__(self): return object.__hash__(self)


class PlayerPublicKey:
    def __init__(self, expiry: int, key: RSAPublicKey, signature: bytes):
        self.key = key
        self.signature = signature
        self.expiry = expiry

