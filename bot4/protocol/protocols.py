from bot4.protocol.protocolbase import PortocolConnect, PortocolBase
from bot4.types.buffer.v1_19_1 import Buffer1_19_1
import bot4.bot.bots as BB
import asyncio


class ProtocolError(Exception):
    pass


class ProtocolState(PortocolBase):
    def _run(self):
        super()._run()
        raise NotImplementedError('protocol not runing')


class ProtocolHandshake(PortocolConnect):
    state_or_login = 2

    def connection_made(self, transport: asyncio.Transport) -> None:
        super().connection_made(transport)
        self.send_packet('Handshake',
                        self.buff_type.pack_varint(self.bot._name_id.protocol_version),
                        self.buff_type.pack_string(self.bot.ip),
                        self.buff_type.pack('H', self.bot.port),
                        self.buff_type.pack_varint(self.state_or_login)
                        )
        self.bot.switch_protocol(self.state_or_login)


class ProtocolAuth(PortocolBase):
    bot: 'BB.BotAuth'

    def __init__(self, bot: 'BB.BotAuth', data_pack, state: int, dispatcher_type):
        super().__init__(bot, data_pack, state, dispatcher_type)

    async def set_compression(self, byff: Buffer1_19_1):
        value = byff.unpack_varint()
        self.bot.compression_threshold = value
        self.logger.debug(f'Set compression to {value}')

    async def disconect(self, byff: Buffer1_19_1):
        self.logger.info(f'Disconect in mode {self.state} {byff.unpack_json()}')

    async def success(self, byff: Buffer1_19_1):
        self.bot.uuid = byff.unpack_uuid()
        self.logger.info('Client login')

    def _run(self):
        super()._run()
        self.dispatcher.on('Disconnect (login)', self.disconect)

        if not self.bot.profile.online:
            self.dispatcher.once('Set Compression', self.set_compression)
            
            def _w(byff: Buffer1_19_1):
                self.bot.switch_right()
                return self.success(byff)
            
            self.dispatcher.once('Login Success', _w)
            self.loop.create_task(self.asend_packet('Login Start', self.buff_type.pack_string(self.bot.profile.display_name)))
        
        else:
            raise NotImplementedError('online mode not implemented')


class ProtocolSpawn(PortocolBase):
    bot: 'BB.BotSpawn'

    def flag_to_num(self, flag: int):
        for i in range(5):
            if (flag >> i) == 1:
                return i

    async def update_player_inc(self):
        while not self.bot.is_close:
            await asyncio.sleep(1 / 20)
            await self.asend_packet('Client Status', self.buff_type.pack('?', True))

    async def resource_pack(self, byff: Buffer1_19_1):
        self.send_packet('Resource Pack Status', b'\x01')

    async def keep_alive(self, buff: Buffer1_19_1):
            self.send_packet('Keep Alive (serverbound)', buff.read())

    async def set_position_look(self, buff: Buffer1_19_1):
        position = buff.unpack('dddff')
        flag = buff.unpack('B')

        for i in range(5):
            if (flag >> i) == 1:
                self.bot.position_look[i] += position[i]
            else:
                self.bot.position_look[i] = position[i]

        self.send_packet('Teleport Confirm', buff.read())

    async def update_position_and_look(self):
        while not self.bot.is_close:
            await asyncio.sleep(1)
            await self.asend_packet(
                "Player Position And Rotation (serverbound)",
                self.buff_type.pack(
                    'dddff?',
                    self.bot.position_look[0],
                    self.bot.position_look[1] - 1.62,
                    self.bot.position_look[2],
                    self.bot.position_look[3],
                    self.bot.position_look[4],
                    True))

    def _run(self):
        super()._run()
        self.bot.position_look: list[float] = [0.0, 0.0, 0.0, 0.0, 0.0]
        self.dispatcher.on('Keep Alive (clientbound)', self.keep_alive)
        self.loop.create_task(self.update_player_inc())
        
        self.dispatcher.once('Resource Pack Send', self.resource_pack)

        @self.dispatcher.once('Player Position And Look (clientbound)')
        async def _w(byff: Buffer1_19_1):
            await self.set_position_look(byff)
            self.dispatcher.on('Player Position And Look (clientbound)', self.set_position_look)
            self.loop.create_task(self.update_position_and_look())

        self.loop.create_task(self.asend_packet('Client Settings', b'\x05ru_ru\x10\x00\x01\x7f\x01'))
        self.loop.create_task(self.asend_packet('Plugin Message (serverbound)', b'\x0fminecraft:brand\x06fabric'))
