import threading, zlib, socket
from bot4.types.buffer import BufferUnderrun, Buffer1_19_1, Buffer1_7, buff_types
from bot4.net.crypto import Cipher
from bot4.types.settings import Settings, Server_Settings
from bot4.versions.packets import Get_packet, Dispatcher
import logging
socket.herror
socket.error
socket.timeout

logging.basicConfig(encoding='utf-8')  #filename='log.log', filemode='w'

def create_thread(func = None, return_thread = False, daemon=True):
    if func:
        if not return_thread:
            def w(*args, **kwargs) -> threading.Thread:
                th = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=daemon)
                th.start()
        else:
            def w(*args, **kwargs) -> threading.Thread:
                th = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=daemon)
                th.start()
                return th
    else:
        if not return_thread:
            def w(func):
                def ww(*args, **kwargs) -> threading.Thread:
                    th = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=daemon)
                    th.start()
                return ww
        else:
            def w(func):
                def ww(*args, **kwargs) -> threading.Thread:
                    th = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=daemon)
                    th.start()
                    return th
                return ww
    
    return w
    

class ProtocolError(Exception): ...


class Protocol:
    buff_type: Buffer1_19_1 = None
    compression_threshold = -1
    soket = None
    is_close = True
    log_level_defult = logging.INFO
    recv_buff = Buffer1_7

    def __init__(self, settings: Settings):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.logger.setLevel(self.log_level_defult)
        self.lock_data_received = threading.Event()

        self.settings = settings
        self.ip = settings.ip
        self.port = settings.port
        self.timeout = settings.timeout
        self.daemon = settings.daemon
        self.name_id = Get_packet(settings.version, self.logger)
        self.buff_type = self.get_buff_type(self.name_id.protocol_version)
        self.cipher = Cipher()

        self.dispatcher = Dispatcher(getattr(self, 'unheandler', None), self.daemon)
        self.name_id.state_updates.append(self.dispatcher)
        self.on = self.dispatcher.on
        self.once = self.dispatcher.once

    def __log_level_set(self, value):
        self.__log_level = value
        self.logger.setLevel(value)

    def __log_level_get(self):
        return self.__log_level

    log_level = property(__log_level_get, __log_level_set)

    def data_received(self):
        while not self.is_close:
            try:
                data = self.soket.recv(4096)
                if data == b'':
                    if not self.is_close:
                        self.close()
                    break
                
                data = self.cipher.decrypt(data)

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

                    self.lock_data_received.wait()
                    self.dispatcher.lock.clear()
                    # Identify the packet
                    name = self.name_id.download[buff.unpack_varint()]
                    # Dispatch the packet
                    self.dispatcher.packet_received(name, buff)
                    self.dispatcher.lock.wait()
                    
            except (socket.gaierror, socket.error, socket.herror, OSError):
                if not self.is_close:
                    self.close()
                break

    def unpack_packet(self, size: int):
        body = self.recv_buff.read(size)

        buff = self.buff_type(body)
        if self.compression_threshold >= 0:
            uncompressed_length = buff.unpack_varint()
            if uncompressed_length > 0:
                body = zlib.decompress(buff.read())
                buff = self.buff_type(body)

        return buff

    def clear_dispatcher(self):
        for i in range(3, -1, -1):
            self.name_id.state = i
            self.dispatcher.on_d.clear()
            self.dispatcher.once_d.clear()

    def close(self, callback = None, *args_callback, **kvargs_callback):
        if not self.is_close:
            self.is_close = True
            # self.soket = self.soket.close()
            self.soket.close()
            self.compression_threshold = -1
            self.recv_buff = Buffer1_7()
            self.clear_dispatcher()
            self.logger.info('Client protocol close')
            if not callback is None:
                callback(*args_callback, **kvargs_callback)
    
    def send_packet(self, name: str, *data: tuple[bytes]):
        data = b"".join(data)
        self.lock_data_received.wait()
        # Prepend ident
        try:
            data = self.buff_type.pack_varint(self.name_id.upload[name]) + data

            # Pack packet
            data = self.buff_type.pack_packet(data, self.compression_threshold)

            # Encrypt
            data = self.cipher.encrypt(data)

            # Send
            if not self.is_close:
                try:
                    self.soket.send(data)
                    self.logger.debug(f'Packet "{name}" sended')

                except (ConnectionAbortedError, OSError, socket.gaierror, socket.error, socket.herror):
                    self.logger.error(f'Packet: "{name}" not send, socket is closed')
                    if not self.is_close:
                        self.close()
        except KeyError:
            self.logger.critical(f'Packet: "{name}" not send, not found in self.name_id.upload, state: {self.name_id.state}, self.is_close: {self.is_close}')
            if not self.is_close:
                self.close()

    def send_packet_no_wait(self, name: str, *data: tuple[bytes]):
        data = b"".join(data)
        # Prepend ident
        try:
            idd = self.name_id.upload[name]
            # self.logger.info(f'{idd}')
            data = self.buff_type.pack_varint(idd) + data

            # Pack packet
            data = self.buff_type.pack_packet(data, self.compression_threshold)

            # Encrypt
            data = self.cipher.encrypt(data)

            # Send
            if not self.is_close:
                try:
                    self.soket.send(data)
                    self.logger.debug(f'Packet "{name}" sended')
                except (ConnectionAbortedError, OSError, socket.gaierror, socket.error, socket.herror):
                    self.logger.error(f'Packet: "{name}" not send, socket is closed')
                    if not self.is_close:
                        self.close()
        except KeyError:
            self.logger.critical(f'Packet: "{name}" not send, not found in self.name_id.upload, state: {self.name_id.state}, self.is_close: {self.is_close}')
            if not self.is_close:
                self.close()

    def get_buff_type(self, protocol_version):
        for ver, cls in reversed(buff_types):
            if protocol_version >= ver:
                return cls

    def setup(self): ...

    def connect(self):
        if self.is_close:
            self.recv_buff = Buffer1_7()
            self.clear_dispatcher()
            self.compression_threshold = -1
            self.is_close = False

            self.soket = socket.create_connection((self.ip, self.port), timeout=self.timeout)
            self.logger.info(f'Client connected to "{self.ip}:{self.port}"')
                    
            # self.setup()
            self.d_received = threading.Thread(target=self.data_received, daemon=self.daemon)
            self.lock_data_received.set()
            self.d_received.start()
            self.setup()


class Protocol_cproxi(Protocol):
    __log_level = logging.INFO

    def __init__(self, settings: Settings, server):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(self.__log_level)
        self.server = server

        self.lock_data_received = threading.Event()
        self.lock_data_received_2 = threading.Event()
        
        self.ip = settings.ip
        self.port = settings.port
        self.timeout = settings.timeout

        self.recv_buff = Buffer1_7()
        self.cipher = Cipher()

        # self.logger.info('{}'.format(getattr(self, 'unheandler', None)))
        self.dispatcher = Dispatcher(getattr(self, 'unheandler', None), self.lock_data_received_2)
        self.on = self.dispatcher.on
        self.once = self.dispatcher.once
        self.regenerate_name_id(settings.version)

    def regenerate_name_id(self, version: int | str):
        self.name_id = Get_packet(version, self.logger)
        self.buff_type = self.get_buff_type(self.name_id.protocol_version)
        self.name_id.state_updates.append(self.dispatcher)

    def unheandler(self, name: str, byff: Buffer1_19_1):
        # if len(byff.buff) > 200: print(f'<-- {name}:{byff.buff[:200]} . . .')
        # else: print(f'<-- {name}:{byff.buff}')
        self.server.send_packet_no_wait(name, byff.read())

    def close(self):
        if not self.is_close:
            self.logger.info('Client protocol close')
            self.server.close(recursion=False)
            self.is_close = True
            self.soket.close()

    def connect(self):
        if self.is_close:
            self.is_close = False
            self.soket = socket.create_connection((self.ip, self.port), timeout=self.timeout)
            self.logger.info(f'Client connected to "{self.ip}:{self.port}"')
            self.d_received = threading.Thread(target=self.data_received)
            self.lock_data_received.set()
            self.setup()
            self.d_received.start()


class Protocol_sproxi:
    buff_type: Buffer1_19_1 = None
    compression_threshold = -1
    soket = None
    is_close = True
    __log_level = logging.INFO
    client_protocol = Protocol_cproxi

    @create_thread
    def __init__(self, settings: Server_Settings, user_socket: socket.socket, addres):
        self.soket = user_socket
        self.addres = addres
        self.lock_data_received = threading.Event()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(self.__log_level)
        
        self.ip_destination = settings.ip_destination
        self.port_destination = settings.port_destination
        self.ip_source = settings.ip_source
        self.port_source = settings.port_source
        self.settings = settings
        
        # self.logger.info('{}'.format(getattr(self, 'unheandler', None)))
        self.dispatcher = Dispatcher(getattr(self, 'unheandler', None), settings.daemon)
        self.on = self.dispatcher.on
        self.once = self.dispatcher.once
        self.regenerate_name_id(settings.version)

        self.recv_buff = Buffer1_7()
        self.cipher = Cipher()

        self.connect()

    def regenerate_name_id(self, version: int | str):
        self.name_id = Get_packet(version, self.logger)
        self.buff_type = self.get_buff_type(self.name_id.protocol_version)
        self.name_id.state_updates.append(self.dispatcher)

    def __log_level_set(self, value):
        self.__log_level = value
        self.logger.setLevel(value)

    def __log_level_get(self): return self.__log_level

    log_level = property(__log_level_get, __log_level_set)

    def unheandler(self, name: str, byff: Buffer1_19_1):
        # if len(byff.buff) > 200: print(f'--> {name}:{byff.buff[:200]} . . .')
        # else: print(f'--> {name}:{byff.buff}')
        self.client.send_packet_no_wait(name, byff.read())

    def data_received(self):
        while not self.is_close:
            try:
                # print('N1')
                data = self.soket.recv(4096)

                if data == b'':
                    self.close()
                    break
                
                data = self.cipher.decrypt(data)

                self.recv_buff.add(data)

                while True:
                    # Save the buffer, in case we read an incomplete packet
                    self.recv_buff.save()

                    # Read the packet
                    
                    try:
                        # pos = self.recv_buff.pos
                        recv_buff_len = len(self.recv_buff)
                        size = self.recv_buff.unpack_varint(max_bits=32)

                        if  size <= recv_buff_len:
                            # self.recv_buff.restore()
                            buff: Buffer1_19_1 = self.unpack_packet(size)
                        else:
                            self.recv_buff.restore()
                            break

                    except BufferUnderrun:
                        self.recv_buff.restore()
                        break
                    # Identify the packet
                    self.lock_data_received.wait()
                    name = self.name_id.upload[buff.unpack_varint()]
                    # Dispatch the packet
                    self.dispatcher.packet_received(name, buff)
            except (ConnectionAbortedError, OSError):
                self.close()
                break

    def unpack_packet(self, size: int):
        body = self.recv_buff.read(size)

        buff = self.buff_type(body)
        if self.compression_threshold >= 0:
            uncompressed_length = buff.unpack_varint()
            if uncompressed_length > 0:
                body = zlib.decompress(buff.read())
                buff = self.buff_type(body)

        return buff

    def close(self, recursion = True):
        if not self.is_close:
            self.logger.info('Client protocol close')
            if recursion:
                self.client.close()
            self.is_close = True
            self.soket.close()

    def send_packet(self, name: str, *data: tuple[bytes]):
        data = b"".join(data)
        self.lock_data_received.wait()
        # Prepend ident
        data = self.buff_type.pack_varint(self.name_id.download[name]) + data

        # Pack packet
        data = self.buff_type.pack_packet(data, self.compression_threshold)

        # Encrypt
        data = self.cipher.encrypt(data)

        # Send
        if not self.is_close:
            try:
                self.soket.send(data)
                self.logger.debug(f'Packet "{name}" sended')
            except (ConnectionAbortedError, OSError):
                self.logger.error(f'Packet: "{name}" not send, socket is closed')
                # raise ProtocolError(f'Packet: "{name}" not send, socket is closed')

    def send_packet_no_wait(self, name: str, *data: tuple[bytes]):
        data = b"".join(data)
        # Prepend ident
        idd = self.name_id.download[name]
        # self.logger.info(f'{idd}')
        data = self.buff_type.pack_varint(idd) + data

        # Pack packet
        data = self.buff_type.pack_packet(data, self.compression_threshold)

        # Encrypt
        data = self.cipher.encrypt(data)

        # Send
        if not self.is_close:
            try:
                self.soket.send(data)
                self.logger.debug(f'Packet "{name}" sended')
            except (ConnectionAbortedError, OSError):
                self.logger.error(f'Packet: "{name}" not send, socket is closed')
                # raise ProtocolError(f'Packet: "{name}" not send, socket is closed')

    def get_buff_type(self, protocol_version):
        for ver, cls in reversed(buff_types):
            if protocol_version >= ver:
                return cls

    def setup(self): ...

    def connect(self):
        if self.is_close:
            self.is_close = False
            self.client = self.client_protocol(Settings(self.name_id.protocol_version,
                                                                self.ip_destination,
                                                                self.port_destination), self)
            self.client.connect()
            self.logger.info(f'Client "{self.addres}" connect')
            self.d_received = threading.Thread(target=self.data_received)
            self.lock_data_received.set()
            self.setup()
            self.d_received.start()


class Proxi:
    protocol = Protocol_sproxi
    is_close = False

    def create_server(self, settings: Server_Settings, in_thread: bool = False):
        if in_thread:
            threading.Thread(target=self.create_server, args=(settings, False), daemon=settings.daemon).start()
        else:
            self.server = socket.create_server((settings.ip_source, settings.port_source))
            self.is_close = False

            while not self.is_close:
                self.server.listen()
                self.protocol(settings, *self.server.accept())

    def close_server(self):
        self.is_close = True
        self.server.close()