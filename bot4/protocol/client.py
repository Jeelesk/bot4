from bot4.protocol.protocol import Protocol, ProtocolError
from bot4.types.settings import Settings_auth
from bot4.types.buffer.v1_19_1 import Buffer1_19_1
from threading import Barrier
from bot4.protocol.protocol import create_thread
from time import sleep


class Protocol_auth(Protocol):
    def __init__(self, settings: Settings_auth):
        super().__init__(settings)
        self.profile = settings.profile

    def set_compression(self, byff: Buffer1_19_1):
        self.compression_threshold = byff.unpack_varint()
        self.logger.debug(f'set_comression "{self.compression_threshold}"')

    def disconect(self, byff: Buffer1_19_1):
        self.logger.error(f'Client disconneced; status_client:{self.name_id.state}, massage: {byff.unpack_json()}')
        self.close()

    def connect(self):
        self.name_id.state = 0
        super().connect()

    def setup(self):
        super().setup()
        br = Barrier(2)

        self.send_packet('Handshake',
                    self.buff_type.pack_varint(754),
                    self.buff_type.pack_string('mc.prostocraft.ru'),
                    self.buff_type.pack('H', 25565),
                    self.buff_type.pack_varint(2))
        self.name_id.state = 2
        self.on('Set Compression', self.set_compression)
        self.on('Disconnect (login)', self.disconect)

        if not self.profile.online:
            @self.once('Login Success')
            def success(byff: Buffer1_19_1):
                self.lock_data_received.clear()
                self.uuid = byff.unpack_uuid()

                self.name_id.state = 3
                self.on('Disconnect (play)', self.disconect)
                self.logger.info(f'Login success "{self.profile.display_name}"')
                self.lock_data_received.set()
                br.wait()
        else:
            raise ProtocolError('Online profiles Not supported')

        self.send_packet('Login Start',
                self.buff_type.pack_string(self.profile.display_name))
        br.wait()

class Protocol_spawn(Protocol_auth):
    def __init__(self, settings: Settings_auth):
        super().__init__(settings)
        self.position_look_list: list[float] = [0.0, 0.0, 0.0, 0.0, 0.0]

    def flag_to_num(self, flag: int):
        for i in range(5):
            if (flag >> i) == 1:
                return i

    def position_look(self, buff: Buffer1_19_1):
        position = buff.unpack('dddff')
        flag = buff.unpack('B')

        for i in range(5):
            if (flag >> i) == 1:
                self.position_look_list[i] += position[i]
            else:
                self.position_look_list[i] = position[i]

        self.send_packet('Teleport Confirm', buff.read())

    def setup(self):
        super().setup()
        self.lock_data_received.clear()
        br = Barrier(2)

        @self.on('Resource Pack Send')
        def resource(byff: Buffer1_19_1):
            self.send_packet('Resource Pack Status', b'\x01')

        @self.on('Keep Alive (clientbound)')
        def keep_alive(buff: Buffer1_19_1):
            self.send_packet('Keep Alive (serverbound)', buff.read())

        @self.once('Player Position And Look (clientbound)')
        def positon(buff: Buffer1_19_1):
            self.position_look(buff)
            @create_thread
            def update_position_and_look():
                while not self.is_close:
                    sleep(1)
                    self.send_packet(
                        "Player Position And Rotation (serverbound)",
                        self.buff_type.pack(
                            'dddff?',
                            self.position_look_list[0],
                            self.position_look_list[1] - 1.62,
                            self.position_look_list[2],
                            self.position_look_list[3],
                            self.position_look_list[4],
                            True))
            update_position_and_look()

            self.on('Player Position And Look (clientbound)', self.position_look)
            br.wait()

        self.lock_data_received.set()

        self.send_packet('Client Settings', b'\x05ru_ru\x10\x00\x01\x7f\x01')
        self.send_packet('Plugin Message (serverbound)', b'\x0fminecraft:brand\x06fabric')

        @create_thread
        def update_player_inc():
            while not self.is_close:
                sleep(1 / 20)
                self.send_packet('Client Status', b'\x00')
        update_player_inc()
        br.wait()


