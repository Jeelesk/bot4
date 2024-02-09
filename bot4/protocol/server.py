from bot4.protocol.protocol import Protocol_sproxi, Protocol_cproxi
from bot4.types.buffer.v1_19_1 import Buffer1_19_1


class Protocol_sproxi_states(Protocol_sproxi):
    def setup(self):
        @self.on('Handshake')
        def handshake(byff: Buffer1_19_1):
            self.lock_data_received.clear()
            self.client.lock_data_received.clear()

            version = byff.unpack_varint()
            self.regenerate_name_id(version)
            self.client.regenerate_name_id(version)

            ip = byff.unpack_string()
            port = byff.unpack('H')
            state = byff.unpack_varint()

            data = byff.pack_varint(version) \
                + byff.pack_string(self.ip_destination) \
                + byff.pack('H', self.port_destination) \
                + byff.pack_varint(state)

            self.client.lock_data_received.set()

            self.client.send_packet('Handshake', data)

            self.client.lock_data_received.clear()

            self.name_id.state = state
            self.client.name_id.state = state

            self.lock_data_received.set()
            self.client.lock_data_received.set()

        @self.on('Login Start')
        def login_start(byff: Buffer1_19_1):
            self.lock_data_received.clear()
            self.client.send_packet('Login Start', byff.read())

class Protocol_cproxi_states(Protocol_cproxi):
    def setup(self):
        self.name_id.state = 2
        @self.once('Set Compression')
        def set_compression(byff: Buffer1_19_1):
            self.lock_data_received.clear()

            pos = byff.pos
            data = byff.read()
            byff.pos = pos

            self.compression_threshold = byff.unpack_varint()
            self.logger.debug(f'set_comression "{self.compression_threshold}"')
            
            self.server.send_packet_no_wait('Set Compression', data)
            self.server.compression_threshold = self.compression_threshold
            self.lock_data_received.set()

        @self.once('Login Success')
        def login_success(byff: Buffer1_19_1):
            self.lock_data_received.clear()
            pos = byff.pos

            self.uuid = byff.unpack_uuid()
            self.name = byff.unpack_string()

            byff.pos = pos

            self.server.uuid = self.uuid
            self.server.name = self.name

            self.name_id.state = 3

            self.server.send_packet('Login Success', byff.read())
            self.server.name_id.state = 3

            self.lock_data_received.set()
            self.server.lock_data_received.set()
            self.logger.info(f'Login success "{self.name}"')

        self.name_id.state = 0


