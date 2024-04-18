from bot4.protocol.protocol import Protocol, ProtocolError, Buffer1_7
from bot4.types.settings import Settings_auth
from bot4.types.buffer.v1_19_1 import Buffer1_19_1
from threading import Barrier, Thread
from time import sleep
from bot4.net.auth import OfflineProfile
import logging, typing


class Updater(Thread):
    def __init__(self, main: typing.Any):
        self.main = main
        self.is_close = False
        Thread.__init__(self)

    def run(self):
        while not self.is_close:
            self.main.send_packet(
                        "Player Position And Rotation (serverbound)",
                        self.main.buff_type.pack(
                            'dddff?',
                            self.main.position_look_list[0],
                            self.main.position_look_list[1] - 1.62,
                            self.main.position_look_list[2],
                            self.main.position_look_list[3],
                            self.main.position_look_list[4],
                            True))
            for _ in range(20):
                self.main.send_packet('Client Status', b'\x00')
                sleep(1 / 20)
                    

class Protocol_auth(Protocol):
    def __init__(self, settings: Settings_auth):
        super().__init__(settings)
        self.logger = logging.getLogger(f'{self.__class__.__name__}:{self.settings.name}')

        self.logger.setLevel(self.log_level_defult)
        self.profile = OfflineProfile(settings.name)

    def set_compression(self, byff: Buffer1_19_1):
        self.compression_threshold = byff.unpack_varint()
        self.logger.debug(f'set_comression "{self.compression_threshold}"')

    def disconect(self, byff: Buffer1_19_1):
        self.logger.error(f'Client disconneced; status_client:{self.name_id.state}, massage: {byff.unpack_json()}')
        self.close()

    def setup(self):
        self.name_id.state = 2
        self.on('Disconnect (login)', self.disconect)
        self.on('Set Compression', self.set_compression)
        self.name_id.state = 3
        self.on('Disconnect (play)', self.disconect)
        self.name_id.state = 0

        super().setup()
        br = Barrier(2)

        self.send_packet('Handshake',
                    self.buff_type.pack_varint(self.settings.version),
                    self.buff_type.pack_string(self.settings.ip),
                    self.buff_type.pack('H', self.settings.port),
                    self.buff_type.pack_varint(2))
        self.name_id.state = 2
        # self.on('Set Compression', self.set_compression)

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
    updater: Updater
    
    def __init__(self, settings: Settings_auth):
        super().__init__(settings)
        self.updater = None
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
            self.updater = Updater(self)
            self.updater.start()

            self.on('Player Position And Look (clientbound)', self.position_look)
            br.wait()

        self.lock_data_received.set()

        self.send_packet('Client Settings', b'\x05ru_ru\x10\x00\x01\x7f\x01')
        self.send_packet('Plugin Message (serverbound)', b'\x0fminecraft:brand\x06fabric')

        br.wait()

    def close(self, callback = None, *args_callback, **kvargs_callback):
        if not self.is_close:
            self.is_close = True
            if not self.updater is None:
                self.updater.is_close = self.is_close
            self.updater = None
            
            self.soket.close()
            self.compression_threshold = -1
            self.recv_buff = Buffer1_7()
            self.clear_dispatcher()
            self.logger.info('Client protocol close')
            if not callback is None:
                callback(*args_callback, **kvargs_callback)

