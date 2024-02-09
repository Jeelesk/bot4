import asyncio
import buffer
import json
import sys
from quarry.net.crypto import Cipher
from quarry.net.protocol import BufferUnderrun, ProtocolError


class Data_packs(dict):
    def __init__(self, self2, dict_packs):
        self.dict_packs = dict_packs
        self.self2 = self2
        dict.__init__(self, dict_packs[self2.state])

    def state_update(self):
        self.clear()
        dict.__init__(self, self.dict_packs[self.self2.state])

class Get_packet:
    file_version_protocols = 'version_protocols'
    packs = {}
    state_var = 0
    upload: Data_packs
    download: Data_packs
    version: str
    protocol_version: int
    byff_type: buffer.Buffer1_19_1

    def set_state(self, state: int):
        self.state_var = state
        self.upload.state_update()
        self.download.state_update()

    def get_state(self) -> int:
        return self.state_var
    
    state: int = property(get_state, set_state)

    @classmethod
    def versionstr_get(cls, version: int) -> str:
        with open('{}\\versions\\{}'.format(sys.__dict__['path'][0], cls.file_version_protocols), 'r', encoding='utf-8') as file:
            for l in file.readlines():
                v1, v2 = l[:-1].split(':')
                if int(v2) == version:
                    return v1
            raise Exception(f'version int {version} not found')

    @classmethod
    def versionint_get(cls, version: str) -> int:
        with open('{}\\versions\\{}'.format(sys.__dict__['path'][0], cls.file_version_protocols), 'r', encoding='utf-8') as file:
            for l in file.readlines():
                v1, v2 = l[:-1].split(':')
                if v1 == version:
                    return v2
            raise Exception(f'version str {version} not found')

    @classmethod
    def __get_packets(cls, protocol_version: int) -> list[list[dict], list[dict]]:
        packs = cls.packs.get(protocol_version)
        if packs is None:
            with open('{}\\versions\\{}'.format(sys.__dict__['path'][0], f'{protocol_version}.json'), 'r', encoding='utf-8') as file:
                packs = json.load(file)
                for l1 in packs:
                    for l2 in l1:
                        ki = [(k, i) for k, i in l2.items()]
                        for k, i in ki:
                            try:
                                k2 = int(k)
                                del l2[k]
                                l2[k2] = i
                            except ValueError: ...

                cls.packs[protocol_version] = packs
        
        return packs

    def __new__(cls, version: int | str):
        self = object.__new__(cls)

        if isinstance(version, str):
            self.version = version
            self.protocol_version = cls.versionint_get(version)
        elif isinstance(version, int):
            self.version = cls.versionstr_get(version)
            self.protocol_version = version
        else:
            raise Exception(f'version not is int or str ({type(version)})')

        self.byff_type = buffer.Buffer1_19_1()

        self.download, self.upload = (Data_packs(self, p) for p in self.__get_packets(self.protocol_version))
        return self

class Once(dict):
    def __getitem__(self, key):
        item = dict.__getitem__(self, key)
        del self[key]
        return item
    
    def get(self, *args):
        item = dict.get(self, *args)
        if len(args) > 1:
            if not item is args[1]:
                del self[args[0]]
        else:
            if not item is None:
                del self[args[0]]

        return item

class Dispatcher:
    def __init__(self, unheandler):
        self.on_d = {}
        self.once_d = Once()
        self.unheandler = unheandler

    def on(self, event: str, _callback = None):
        if _callback is None:
            def w(_callback):
                self.on_d[event] = _callback
                return _callback
            return w
        else:
            self.on_d[event] = _callback

    def once(self, event: str, _callback = None):
        if _callback is None:
            def w(_callback2):
                self.once_d[event] = _callback2
                # return _callback2
            return w
        else:
            self.once_d[event] = _callback

    def packet_received(self, event: str, buff: bytes):
        print('N4')
        callback = self.on_d.get(event)
        callback = self.once_d.get(event, callback)
        
        if not callback is None:
            self.loop.create_task(callback(buff))
        else:
            self.loop.create_task(self.unheandler(event, buff))

class Bot(Dispatcher):
    buff_type: buffer.Buffer1_19_1 = None
    compression_threshold = -1
    tasks_data_received = []

    def __init__(self, version: str | int = 754,
            ip: str = 'mc.prostocraft.ru',
            port: int = 25565):
        self.ip = ip
        self.port = port
        self.name_id = Get_packet(version)
        self.buff_type = self.get_buff_type(self.name_id.protocol_version)
        self.recv_buff = buffer.Buffer1_7()
        self.cipher = Cipher()
        Dispatcher.__init__(self, self.unheandler)
        self.loop = asyncio.get_running_loop()
        # print(self.loop)
        # self.dispatcher = Dispatcher(self.unheandler)
        self.task_data_received = None

    @classmethod
    async def drain_all(self):
        while self.tasks_data_received:
            await self.tasks_data_received[0]
            
    async def drain_one(self):
        await self.task_data_received

    async def unheandler(self, event, buff):
        print(event, buff)

    async def data_received(self):
        print('N1')
        while True:
            data = await self.reader.read()
            print('N2')
            data = self.cipher.decrypt(data)
            print(data)

            self.recv_buff.add(data)

            while True:
                # Save the buffer, in case we read an incomplete packet
                self.recv_buff.save()

                # Read the packet
                
                try:
                    if self.recv_buff.unpack_varint(max_bits=32) <= len(self.recv_buff):
                        buff: buffer.Buffer1_7 = self.recv_buff.unpack_packet(
                            self.buff_type,
                            self.compression_threshold)

                    else:
                        self.recv_buff.restore()
                        break
                except BufferUnderrun:
                    self.recv_buff.restore()
                    break

                # Identify the packet
                name = self.name_id.download.get(buff.unpack_varint())
                # Dispatch the packet
                self.packet_received(name, buff)

    def __remove(self, c):
        self.tasks_data_received.remove(self.task_data_received)
        self.task_data_received = None

    def close(self):
        self.task_data_received.cancel()
        self.writer = self.writer.close()
        self.reader = None

    def send_packet(self, name: str, *data: tuple[bytes]):
        data = b"".join(data)

        # Prepend ident
        data = self.buff_type.pack_varint(self.name_id.upload[name]) + data

        # Pack packet
        data = self.buff_type.pack_packet(data, self.compression_threshold)

        # Encrypt
        data = self.cipher.encrypt(data)

        # Send
        self.writer.write(data)

    def get_buff_type(self, protocol_version):
        """
        Gets a buffer type for the given protocol version.
        """
        for ver, cls in reversed(buffer.buff_types):
            if protocol_version >= ver:
                return cls

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.ip, self.port)
        self.task_data_received = self.loop.create_task(self.data_received())

        self.task_data_received.add_done_callback(self.__remove)
        self.tasks_data_received.append(self.task_data_received)

async def main():
    bot = Bot()
    await bot.connect()
    print('N')

    bot.send_packet('Handshake',
                    bot.buff_type.pack_varint(754),
                    bot.buff_type.pack_string('mc.prostocraft.ru'),
                    bot.buff_type.pack('H', 25565),
                    b'\x01')

    bot.name_id.state += 1

    @bot.once('Response')
    async def test(buff: buffer.Buffer1_19):
        print(buff.buff)
        bot.close()

    bot.send_packet('Request')
    print('N5')
    
    await Bot.drain_all()

if __name__ == '__main__':
    asyncio.run(main())

