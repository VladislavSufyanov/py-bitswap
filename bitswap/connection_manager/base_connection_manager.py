from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from ..peer.peer import Peer
    from ..peer.base_peer_manager import BasePeerManager
    from ..network.base_network import BaseNetwork


class BaseConnectionManager(metaclass=ABCMeta):

    @abstractmethod
    def run_handle_conn(self, network: 'BaseNetwork', peer_manager: 'BasePeerManager') -> None:
        pass

    @abstractmethod
    def stop_handle_conn(self) -> None:
        pass

    @abstractmethod
    def run_message_handlers(self, peer: 'Peer', peer_manager: 'BasePeerManager') -> asyncio.Task:
        pass
