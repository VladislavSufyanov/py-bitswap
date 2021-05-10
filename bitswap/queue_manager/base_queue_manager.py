from abc import ABCMeta, abstractmethod
from typing import Optional, Iterable, TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..peer.peer import Peer


class BaseQueueManager(metaclass=ABCMeta):

    @staticmethod
    @abstractmethod
    def get_peers_smallest_response_queue(peers: Iterable['Peer']) -> Optional[List['Peer']]:
        pass
