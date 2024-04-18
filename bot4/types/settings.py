from dataclasses import dataclass
from bot4.net.auth import OfflineProfile


@dataclass
class Settings:
    version: int = 754
    ip: str = 'mc.prostocraft.ru'
    port: int = 25565
    timeout: float = 30.0
    daemon: bool = True


@dataclass
class Settings_auth(Settings):
    name: str = "quarry"

Settings_spawn = Settings_auth

@dataclass
class Server_Settings:
    version: str | int = 757
    daemon: bool = True

    ip_source: str = '127.0.0.1'
    port_source: int = 25565

    ip_destination: str = 'mc.prostocraft.com'
    port_destination: int = 25565

