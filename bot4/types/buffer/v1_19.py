from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from bot4.net.auth import PlayerPublicKey
from bot4.net.crypto import import_public_key
from bot4.types.buffer.v1_14 import Buffer1_14


class Buffer1_19(Buffer1_14):
    @classmethod
    def pack_player_public_key(cls, data: PlayerPublicKey):
        return cls.pack('Q', data.expiry) \
               + cls.pack_byte_array(data.key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)) \
               + cls.pack_byte_array(data.signature)

    def unpack_player_public_key(self):
        expiry = self.unpack('Q')
        key_bytes = self.unpack_byte_array()
        signature = self.unpack_byte_array()

        return PlayerPublicKey(expiry, import_public_key(key_bytes), signature)
