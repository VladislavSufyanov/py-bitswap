from typing import Generator, TYPE_CHECKING

import weakref

from .base_session_manager import BaseSessionManager
from .session import Session

if TYPE_CHECKING:
    from network.base_network import BaseNetwork
    from peer.base_peer_manager import BasePeerManager


class SessionManager(BaseSessionManager):

    def __init__(self) -> None:
        self.sessions = weakref.WeakSet()

    def __iter__(self) -> Generator[Session, None, None]:
        return self.sessions.__iter__()

    def create_session(self, network: 'BaseNetwork', peer_manager: 'BasePeerManager', min_score: int = -100) -> Session:
        new_session = Session(network, peer_manager, min_score)
        self.sessions.add(new_session)
        return new_session
