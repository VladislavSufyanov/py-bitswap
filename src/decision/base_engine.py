from abc import ABCMeta, abstractmethod
from asyncio.queues import PriorityQueue, Queue

from peer import Peer
from message import BitswapMessage


class BaseEngine(metaclass=ABCMeta):

    @abstractmethod
    def handle_bit_swap_message(self, peer: Peer, bit_swap_message: BitswapMessage) -> None:
        pass

    @abstractmethod
    def create_response_queue(self, peer: Peer) -> Queue:
        pass

    @abstractmethod
    def create_tasks_queue(self, peer: Peer) -> PriorityQueue:
        pass

    @abstractmethod
    def remove_response_queue(self, peer: Peer) -> None:
        pass

    @abstractmethod
    def remove_tasks_queue(self, peer: Peer) -> None:
        pass
