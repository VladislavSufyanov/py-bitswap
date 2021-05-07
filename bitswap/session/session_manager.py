from typing import Generator, TYPE_CHECKING, Optional
from logging import INFO

import weakref

from .base_session_manager import BaseSessionManager
from .session import Session
from ..logger import get_stream_logger_colored, get_concurrent_logger

if TYPE_CHECKING:
    from ..network.base_network import BaseNetwork
    from ..peer.base_peer_manager import BasePeerManager


class SessionManager(BaseSessionManager):

    def __init__(self, min_score: int = -100, log_level: int = INFO, log_path: Optional[str] = None) -> None:
        if log_path is None:
            self._logger = get_stream_logger_colored(__name__, log_level)
        else:
            self._logger = get_concurrent_logger(__name__, log_path, log_level)
        self._log_level = log_level
        self._log_path = log_path
        self._min_score = min_score
        self.sessions = weakref.WeakSet()

    def __iter__(self) -> Generator[Session, None, None]:
        return self.sessions.__iter__()

    def create_session(self, network: 'BaseNetwork', peer_manager: 'BasePeerManager') -> Session:
        new_session = Session(network, peer_manager, self._min_score, self._log_level, self._log_path)
        self.sessions.add(new_session)
        self._logger.debug(f'New session created, session: {new_session}')
        return new_session
