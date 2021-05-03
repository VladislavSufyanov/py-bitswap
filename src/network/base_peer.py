from typing import AsyncGenerator
from abc import ABCMeta, abstractmethod


class BasePeer(metaclass=ABCMeta):

    @abstractmethod
    def __aiter__(self) -> AsyncGenerator[bytes, None]:
        pass
