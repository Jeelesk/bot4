import json, threading, os
from logging import Logger
from threading import Event
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
        # item = dict.get(self, *args)
        # if len(args) > 1:
        #     if not item is args[1]:
        #         del self[args[0]]
        # else:
        #     if not item is None:
        #         del self[args[0]]

        # return item


class Dispatcher:
    on_d: On[str, list]
    once_d: Once[str, list]
    state = 0
    lock: Event

    def __new__(cls, unheandler = None, daemon=True):
        lock = threading.Event()
        if unheandler is None:
            def packet_received(self, event: str, buff: Buffer1_19_1):
                callback = self.on_d.get(event)
                callback = self.once_d.get(event, callback)
                
                if not callback is None:
                    for c in callback:
                        lock.clear()
                        threading.Thread(target=c, args=(buff.copy(),), daemon=daemon).start()
                        lock.wait()
                else:
                    lock.set()
            cls.packet_received0 = packet_received
        else:
            def unheandlerr(event, buff):
                lock.set()
                unheandler(event, buff)

            def packet_received(self, event: str, buff: Buffer1_19_1):
                callback = self.on_d.get(event)
                callback = self.once_d.get(event, callback)
                
                if not callback is None:
                    for c in callback:
                        lock.clear()
                        threading.Thread(target=c, args=(buff.copy(),), daemon=daemon).start()
                        lock.wait()
                else:
                    threading.Thread(target=unheandlerr, args=(event, buff.copy()), daemon=daemon).start()
            cls.packet_received0 = packet_received
        
        self = object().__new__(cls)
        self.packet_received = self.packet_received0
        self.lock = lock
        del cls.packet_received0
        
        self.on_d = On()
        self.once_d = Once()
        self.__events_to_status = {0: (self.on_d, self.once_d)}
        return self

    def state_update(self, state):
        self.state = state
        events = self.__events_to_status.get(state)
        if events is None:
            self.on_d = On()
            self.once_d = Once()
            self.__events_to_status[state] = (self.on_d, self.once_d)
        else:
            self.on_d, self.once_d = events

    def on(self, event: str, _callback = None):
        if _callback is None:
            def w(_callback):
                def ww(byff):
                    self.lock.set()
                    _callback(byff)
                ww.__name__ = _callback.__name__
                self.on_d[event] = ww
                return _callback
            return w
        else:
            def ww(byff):
                self.lock.set()
                _callback(byff)
            ww.__name__ = _callback.__name__
            self.on_d[event] = ww

    def once(self, event: str, _callback = None):
        if _callback is None:
            def w(_callback2):
                def ww(byff):
                    self.lock.set()
                    _callback2(byff)
                ww.__name__ = _callback2.__name__
                self.once_d[event] = ww
                return _callback2
            return w
        else:
            def ww(byff):
                    self.lock.set()
                    _callback(byff)
            ww.__name__ = _callback.__name__
            self.once_d[event] = ww


class Data_packs(dict):
    def __init__(self, dict_packs: list[dict], state: int):
        self.dict_packs = dict_packs
        self.state = state
        dict.__init__(self, dict_packs[state])

    def state_update(self, new_state: int):
        self.clear()
        self.state = new_state
        dict.__init__(self, self.dict_packs[new_state])


class Get_packet:
    file_version_protocols = 'version_protocols'
    versions_list = {}
    packs = {}
    state_var = 0
    upload: Data_packs
    download: Data_packs
    version: str
    protocol_version: int
    state_updates: list
    logger: Logger
    if os.name == 'nt':
        path_to_versions = f'{version_path}\\{file_version_protocols}'
    else:
        path_to_versions = f'{version_path}/{file_version_protocols}'


    @classmethod
    def update_versions_list(cls):
        cls.versions_list.clear()

        with open(cls.path_to_versions, 'r', encoding='utf-8') as file:
            for l in file.readlines():
                v1, v2 = l[:-1].split(':')
                v2 = int(v2)
                cls.versions_list[v1] = v2
                cls.versions_list[v2] = v1

    def __set_state(self, state: int):
        self.logger.debug(f'State Client set to "{state}"')
        self.state_var = state
        for u in self.state_updates: u.state_update(state)

    def __get_state(self) -> int:
        return self.state_var
    
    state = property(__get_state, __set_state)
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
    def __get_packets(cls, protocol_version: int) -> list[list[dict], list[dict]]:
        packs = cls.packs.get(protocol_version)
        if packs is None:

            if os.name == 'nt':
                path_to_json = '{}\\{}'.format(version_path, f'{protocol_version}.json')
            else:
                path_to_json = '{}/{}'.format(version_path, f'{protocol_version}.json')

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

    def __new__(cls, version: int | str, logger: Logger = None):
        self = object.__new__(cls)
        self.logger = logger

        if isinstance(version, str):
            self.version = version
            self.protocol_version = cls.versionint_get(version)
        elif isinstance(version, int):
            self.version = cls.versionstr_get(version)
            self.protocol_version = version
        else:
            raise Exception(f'version not is int or str ({type(version)})')
        
        self.download, self.upload = (Data_packs(p, self.state) for p in self.__get_packets(self.protocol_version))
        self.state_updates = [self.download, self.upload]

        return self

Get_packet.update_versions_list()
