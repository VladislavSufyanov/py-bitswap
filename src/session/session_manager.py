from typing import Generator

import weakref

from .base_session_manager import BaseSessionManager
from .session import Session


class SessionManager(BaseSessionManager):

    def __init__(self) -> None:
        self.sessions = weakref.WeakSet()

    def __iter__(self) -> Generator[Session, None, None]:
        return self.sessions.__iter__()

    def create_session(self) -> Session:
        new_session = Session()
        self.sessions.add(new_session)
        return new_session
