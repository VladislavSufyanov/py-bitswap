from abc import ABCMeta, abstractmethod
from typing import Set, Generator, TYPE_CHECKING

if TYPE_CHECKING:
    from .session import Session
    from ..peer.base_peer_manager import BasePeerManager
    from ..network.base_network import BaseNetwork


class BaseSessionManager(metaclass=ABCMeta):

    session: Set['Session']

    @abstractmethod
    def __iter__(self) -> Generator['Session', None, None]:
        pass

    @abstractmethod
    def create_session(self, network: 'BaseNetwork', peer_manager: 'BasePeerManager') -> 'Session':
        pass
