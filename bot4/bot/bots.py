from bot4.bot.base import BotBase, Loging
from bot4.protocol.protocols import ProtocolHandshake, ProtocolAuth, ProtocolSpawn, ProtocolState
from bot4.types.settings import Settings_auth, Settings_spawn, OfflineProfile
import asyncio


class BotAuth(BotBase):
    settings: Settings_auth
    def __init__(self, settings: Settings_auth, loop: asyncio.AbstractEventLoop = None):
        super().__init__(settings, loop)
        self.logger.name += f':{settings.name}'

        self.profile = OfflineProfile(settings.name)
    
    def set_start(self):
        self.add_protocol(0)(ProtocolHandshake)
        self.add_protocol(1)(ProtocolState)
        self.add_protocol(2)(ProtocolAuth)


class BotSpawn(BotAuth):
    def __init__(self, settings: Settings_spawn, loop: asyncio.AbstractEventLoop = None):
        super().__init__(settings, loop)
        # old_success = self.protocols[2].success
        
        # async def success(byff):
        #     await old_success(byff)
        #     self.switch_right()
        
        # self.protocols[2].success = success
        self.position_look: list[float] = [0.0, 0.0, 0.0, 0.0, 0.0]

    def set_start(self):
        super().set_start()
        self.add_protocol(3)(ProtocolSpawn)
