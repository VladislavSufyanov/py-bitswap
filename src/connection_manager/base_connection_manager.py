from abc import ABCMeta, abstractmethod
import asyncio

from peer import Peer


class BaseConnectionManager(metaclass=ABCMeta):

    @abstractmethod
    def run_message_handlers(self, peer: Peer) -> asyncio.Task:
        pass
