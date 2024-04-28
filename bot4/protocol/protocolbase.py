import asyncio, zlib
from bot4.bot.base import Dispatcher, Buffer1_19_1
from bot4.versions.packets import Data_packs
from bot4.types.buffer import BufferUnderrun
import bot4.bot.base as BBase

class PortocolBase(asyncio.Protocol):
    dispatcher: Dispatcher
    data_pack: Data_packs
    state: int
    unheandler = None


    def __init__(self, bot: 'BBase.BotBase', data_pack: Data_packs, state: int, dispatcher_type: Dispatcher):
        self.bot = bot
        self.data_pack = data_pack
        self.state = state

        self.loop = self.bot.loop
        self.recv_buff = self.bot.recv_buff
        self.cipher = self.bot.cipher
        self.buff_type = self.bot.buff_type
        self.logger = self.bot.logger
        
        self.dispatcher = dispatcher_type(self.unheandler, self.loop)

    def _run(self):
        self.logger.debug(f'Run protocol "{self.__class__.__name__}" state {self.state}')
        self.bot.state = self.state

    def _switched(self):
        self.logger.debug(f'Switched protocol "{self.__class__.__name__}" state {self.state}')
        self.dispatcher.clear()

    def connection_made(self, transport: asyncio.Transport) -> None:
        raise NotImplementedError

    async def asend_packet(self, *args):
        self.send_packet(*args)

    def connection_lost(self, exc: Exception | None) -> None:
        self._switched()
        self.bot._connection_lost(exc)

    def data_received(self, data: bytearray):
        data = self.cipher.decrypt(bytes(data))
        
        self.recv_buff.add(data)

        while True:
            # Save the buffer, in case we read an incomplete packet
            self.recv_buff.save()

            # Read the packet                    
            try:
                recv_buff_len = len(self.recv_buff)
                size = self.recv_buff.unpack_varint(max_bits=32)

                if  size <= recv_buff_len:
                    buff: Buffer1_19_1 = self.unpack_packet(size)
                else:
                    self.recv_buff.restore()
                    break

            except BufferUnderrun:
                self.recv_buff.restore()
                break

            # Identify the packet
            try:
                name = self.data_pack.download[buff.unpack_varint()]
                # Dispatch the packet
                self.dispatcher.packet_received(name, buff)
            except KeyError as e:
                raise KeyError(f'{e} state {self.state} protocol {self.__class__.__name__}')

    def unpack_packet(self, size: int):
        body = self.recv_buff.read(size)

        buff = self.buff_type(body)
        if self.bot.compression_threshold >= 0:
            uncompressed_length = buff.unpack_varint()
            if uncompressed_length > 0:
                body = zlib.decompress(buff.read())
                buff = self.buff_type(body)

        return buff

    def pack_packet(self, data):
        """
        Unpacks a packet frame. This method handles length-prefixing and
        compression.
        """

        if self.bot.compression_threshold >= 0:
            # Compress data and prepend uncompressed data length
            if len(data) >= self.bot.compression_threshold:
                data = self.buff_type.pack_varint(len(data)) + zlib.compress(data)
            else:
                data = self.buff_type.pack_varint(0) + data

        # Prepend packet length
        return self.buff_type.pack_varint(len(data), max_bits=32) + data

    def send_packet(self, name: str, *data: tuple[bytes]):
        data: bytes = b"".join(data)
        # Prepend ident
        data = self.buff_type.pack_varint(self.data_pack.upload[name]) + data

        # Pack packet
        data = self.pack_packet(data)

        # Encrypt
        data = self.cipher.encrypt(data)

        self.bot.transport.write(data)
        self.logger.debug(f'Packet "{name}" sended')

    def __call__(self):
        self._run()
        return self


class PortocolConnect(PortocolBase):
    def connection_made(self, transport: asyncio.Transport) -> None:  # set transport
        self.bot.transport = transport
        self.logger.info(f'Client connected to "{self.bot.ip}:{self.bot.port}"')

    def _run(self):
        self.bot.is_close = False
        super()._run()

