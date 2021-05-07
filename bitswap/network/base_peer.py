from typing import AsyncGenerator
from abc import ABCMeta, abstractmethod


class BasePeer(metaclass=ABCMeta):

    @abstractmethod
    def __aiter__(self) -> AsyncGenerator[bytes, None]:
        pass

    @abstractmethod
    async def send(self, message: bytes) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass
