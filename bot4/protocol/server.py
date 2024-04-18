from bot4.protocol.protocol import Protocol_sproxi, Protocol_cproxi
from bot4.types.buffer.v1_19_1 import Buffer1_19_1
import logging


class Protocol_sproxi_states(Protocol_sproxi):
    def setup(self):
        @self.once('Handshake')
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


            self.client.send_packet_no_wait('Handshake', data)

            self.name_id.state = state
            self.client.name_id.state = state

            self.lock_data_received.set()
            self.client.lock_data_received.set()

        self.name_id.state = 2

        @self.once('Login Start')
        def login_start(byff: Buffer1_19_1):
            @self.client.once('Encryption Request')
            def encryption_requests(byff: Buffer1_19_1):
                @self.once('Encryption Response')
                def encryption_response(byff: Buffer1_19_1):
                    self.logger.info(f'''Encryption Response:
                                            Shared Secret {byff.unpack_byte_array()}
                                            Verify Token {byff.unpack_byte_array()}''')
                
                self.client.logger.info(f'''Encryption Request:
                                        Server ID {byff.unpack_string()}
                                        Public Key {byff.unpack_byte_array()}
                                        Verify Token {byff.unpack_byte_array()}''')

            self.client.once('Set Compression', self.set_compression)


            self.client.send_packet('Login Start', byff.read())

        self.name_id.state = 0

    def set_compression(self, byff: Buffer1_19_1):
        self.client.lock_data_received.clear()

        @self.client.once('Login Success')
        def login_success(byff: Buffer1_19_1):
            self.client.lock_data_received.clear()
            self.lock_data_received.clear()
            pos = byff.pos

            self.client.uuid = byff.unpack_uuid()
            self.client.name = byff.unpack_string()

            byff.pos = pos

            self.uuid = self.client.uuid
            self.name = self.client.name

            self.client.name_id.state = 3

            self.send_packet_no_wait('Login Success', byff.read())
            self.name_id.state = 3

            self.client.logger.info(f'Login success "{self.client.name}"')
            self.client.lock_data_received.set()
            self.lock_data_received.set()


        pos = byff.pos
        data = byff.read()
        byff.pos = pos

        self.client.compression_threshold = byff.unpack_varint()
        self.client.logger.debug(f'set_comression "{self.client.compression_threshold}"')
            
        self.send_packet_no_wait('Set Compression', data)
        self.compression_threshold = self.client.compression_threshold
        self.client.lock_data_received.set()


class Protocol_cproxi_states(Protocol_cproxi): ...


