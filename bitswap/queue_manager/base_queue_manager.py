from abc import ABCMeta, abstractmethod
from typing import Optional, Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..peer.peer import Peer


class BaseQueueManager(metaclass=ABCMeta):

    @staticmethod
    @abstractmethod
    def get_smallest_response_queue(peers: Iterable['Peer']) -> Optional['Peer']:
        pass
