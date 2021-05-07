from abc import ABCMeta, abstractmethod
from asyncio.queues import PriorityQueue, Queue
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from peer.peer import Peer
    from message.bitswap_message import BitswapMessage
    from peer.base_peer_manager import BasePeerManager


class BaseEngine(metaclass=ABCMeta):

    @abstractmethod
    def handle_bit_swap_message(self, peer: 'Peer', bit_swap_message: 'BitswapMessage',
                                peer_manager: 'BasePeerManager') -> None:
        pass

    @abstractmethod
    def create_response_queue(self, peer: 'Peer') -> Queue:
        pass

    @abstractmethod
    def create_tasks_queue(self, peer: 'Peer') -> PriorityQueue:
        pass

    @abstractmethod
    def remove_response_queue(self, peer: 'Peer') -> None:
        pass

    @abstractmethod
    def remove_tasks_queue(self, peer: 'Peer') -> None:
        pass
