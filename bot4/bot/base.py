import logging, asyncio
from bot4.types.buffer import Buffer1_19_1, Buffer1_7, buff_types
from bot4.net.crypto import Cipher
from bot4.types.settings import Settings
from bot4.versions.packets import Get_packet, Dispatcher
from bot4.protocol.protocolbase import PortocolBase, PortocolConnect


class Loging:
    logging.basicConfig(encoding='utf-8')  #filename='log.log', filemode='w'
    log_level_defult = logging.INFO


    def __init__(self, name: str = None):
        if (not (name is None)) and isinstance(name, str):
            name = f'{self.__class__.__name__}:{name}'
        else:
            name = self.__class__.__name__

        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level_defult)

    def _log_level_set(self, value):
        self.__log_level = value
        self.logger.setLevel(value)

    def _log_level_get(self):
        return self.__log_level

    log_level = property(_log_level_get, _log_level_set)


class ProtocolError(Exception):
    pass


class Protocols_LoopError(Exception):
    pass


class BotBase(Loging):
    buff_type: Buffer1_19_1 = None
    compression_threshold = -1
    is_close = True
    recv_buff: Buffer1_7
    loop: asyncio.AbstractEventLoop
    transport: asyncio.Transport
    state = 0

    
    def __init__(self, settings: Settings, loop: asyncio.AbstractEventLoop = None):
        Loging.__init__(self)
        self.loop = asyncio.get_event_loop() if loop is None else loop

        self.settings = settings
        self.ip = settings.ip
        self.port = settings.port
        self.timeout = settings.timeout

        self._name_id = Get_packet(settings.version)
        self.data_packs = self._name_id.data_packs

        self.buff_type = self.get_buff_type(self._name_id.protocol_version)
        self.cipher = Cipher()
        self.recv_buff = Buffer1_7()


        self.protocols = {}
        self.set_start()

    def set_start(self):
        self.add_protocol(0)(PortocolConnect)

    def config_protocol(self, protocol: PortocolBase, state: int, dispatcher_type: Dispatcher) -> PortocolBase:
        if not isinstance(state, int):
            raise TypeError(f'state no valid type <{type(state)}>')
        try:
            data_pack = self.data_packs[state]
        except IndexError:
            raise Protocols_LoopError(f'state {state} not found')

        return protocol(self, data_pack, state, dispatcher_type)

    def add_protocol(self, state: int, dispatcher_type: Dispatcher = Dispatcher):
        def _w(protocol: PortocolBase):
            p = self.config_protocol(protocol, state, dispatcher_type)
            self.protocols[state] = p
            return p

        return _w

    def switch_protocol(self, state: int):
        self.transport.get_protocol()._switched()
        self.transport.set_protocol(self.protocols[state]())

    def switch_right(self):
        self.switch_protocol(self.state + 1)

    def switch_left(self):
        self.switch_protocol(self.state - 1)

    def _connection_lost(self, exc: Exception | None):
        self.is_close = True
        self.compression_threshold = -1
        self.recv_buff.clear()
        self.cipher.disable()
        self.logger.info('Client close')

    def get_buff_type(self, protocol_version):
        for ver, cls in reversed(buff_types):
            if protocol_version >= ver:
                return cls

    async def connect(self):
        if self.is_close:
            await self.loop.create_connection(self.protocols[0], host=self.ip, port=self.port)

    def close(self):
        if not self.is_close:
            self.transport.close()



