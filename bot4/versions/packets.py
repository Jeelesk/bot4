import json, os, asyncio, types
from bot4.types.buffer.v1_19_1 import Buffer1_19_1


version_path = os.path.dirname(__file__)


class On(dict):
    def __setitem__(self, k, v):
        values = super().get(k)
        if isinstance(values, list):
            values.append(v)
        else:
            super().__setitem__(k, [v])


class Once(dict):
    def __getitem__(self, key):
        item = dict.__getitem__(self, key)
        del self[key]
        return item
    
    def __setitem__(self, k, v):
        values = super().get(k)
        if isinstance(values, list):
            values.append(v)
        else:
            super().__setitem__(k, [v])

    def get(self, key, default):
        item = super().get(key)
        if not item is None:
            del self[key]
            return item
        else:
            return default


class Dispatcher:
    on_d: On[str, list]
    once_d: Once[str, list]
    loop: asyncio.AbstractEventLoop
    unheandler: types.MethodType = None


    def packet_received(self, event: str, buff: Buffer1_19_1):
        raise NotImplementedError

    def __packet_received(self, event: str, buff: Buffer1_19_1):
        callbacks = self.on_d.get(event)
        callbacks = self.once_d.get(event, callbacks)
        
        if not callbacks is None:
            for callback in callbacks:
                self.loop.create_task(callback(buff.copy()), name=event)

    def __packet_received_unheandler(self, event: str, buff: Buffer1_19_1):
        callbacks = self.on_d.get(event)
        callbacks = self.once_d.get(event, callbacks)
        
        if not callbacks is None:
            for callback in callbacks:
                self.loop.create_task(callback(buff.copy()), name=event)
        else:
            self.loop.create_task(self.unheandler(event, buff), name=event)
    
    def __init__(self, unheandler: types.MethodType = None, loop: asyncio.AbstractEventLoop = None):
        self.loop = asyncio.get_event_loop() if loop is None else loop
        
        if unheandler is None:
            self.packet_received = self.__packet_received

        else:
            self.unheandler = unheandler
            self.packet_received = self.__packet_received_unheandler
        
        self.on_d = On()
        self.once_d = Once()

    def clear(self):
        self.on_d.clear()
        self.once_d.clear()

    def on(self, event: str, callback = None):
        if callback is None:
            def w(callback):
                self.on_d[event] = callback
            return w
        else:
            self.on_d[event] = callback

    def once(self, event: str, callback = None):
        if callback is None:
            def w(callback):
                self.once_d[event] = callback
            return w
        else:
            self.once_d[event] = callback


class Data_packs(dict):
    def __init__(self, download: dict, upload: dict):
        self.download = download
        self.upload = upload


class Get_packet:
    file_version_protocols = 'version_protocols.json'
    versions_list = {}
    packs = {}
    state_var = 0
    data_packs: list[Data_packs]
    version: str
    protocol_version: int
    path_to_versions = f'{version_path}\\{file_version_protocols}' if os.name == 'nt' else f'{version_path}/{file_version_protocols}'


    @classmethod
    def update_versions_list(cls):
        '''read versions'''
        cls.versions_list.clear()

        with open(cls.path_to_versions, 'r', encoding='utf-8') as file:
            cls.versions_list.__init__(json.loads(file.read()))
            for k, v in cls.versions_list.copy().items():
                cls.versions_list[v] = k

    @classmethod
    def versionstr_get(cls, version: int) -> str:
        assert isinstance(version, int), 'version type is not int'
        vs = cls.versions_list.get(version)
        if not vs is None:
            return vs

        raise Exception(f'version <{version}> not found')

    @classmethod
    def versionint_get(cls, version: str) -> int:
        assert isinstance(version, str), 'version type is not str'
        vi = cls.versions_list.get(version)
        if not vi is None:
            return vi

        raise Exception(f'version <{version}> not found')

    @classmethod
    def _get_packets(cls, protocol_version: int) -> list[list[dict], list[dict]]:
        packs = cls.packs.get(protocol_version)
        if packs is None:
            path_to_json = '{}\\{}'.format(version_path, f'{protocol_version}.json') if os.name == 'nt' else '{}/{}'.format(version_path, f'{protocol_version}.json')

            with open(path_to_json, 'r', encoding='utf-8') as file:
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
        
        self.data_packs = [Data_packs(d, u) for d, u in zip(*self._get_packets(self.protocol_version))]

        return self

Get_packet.update_versions_list()
