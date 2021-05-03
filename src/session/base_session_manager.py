from abc import ABCMeta, abstractmethod
from typing import Set

from .session import Session


class BaseSessionManager(metaclass=ABCMeta):

    session: Set[Session]

    @abstractmethod
    def __iter__(self) -> Session:
        pass

    @abstractmethod
    def create_session(self) -> Session:
        pass
