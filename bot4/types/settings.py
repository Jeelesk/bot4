from dataclasses import dataclass
from bot4.net.auth import OfflineProfile


@dataclass
class Settings:
    version: str | int = 754
    ip: str = 'mc.prostocraft.ru'
    port: int = 25565
    timeout: float = 30.0


@dataclass
class Settings_auth(Settings):
    profile: OfflineProfile = OfflineProfile()

Settings_spawn = Settings_auth

@dataclass
class Server_Settings:
    version: str | int = 754

    ip_source: str = '127.0.0.1'
    port_source: int = 25565

    ip_destination: str = 'mc.prostocraft.ru'
    port_destination: int = 25565

