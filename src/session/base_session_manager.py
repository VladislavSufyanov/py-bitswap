from abc import ABCMeta, abstractmethod
from typing import Set, Generator

from .session import Session


class BaseSessionManager(metaclass=ABCMeta):

    session: Set[Session]

    @abstractmethod
    def __iter__(self) -> Generator[Session, None, None]:
        pass

    @abstractmethod
    def create_session(self) -> Session:
        pass
