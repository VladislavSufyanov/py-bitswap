from abc import ABCMeta, abstractmethod
from typing import Union

from cid import CIDv0, CIDv1


class BaseBitswap(metaclass=ABCMeta):

    @abstractmethod
    async def put(self, cid: Union[CIDv0, CIDv1], block: bytes) -> None:
        pass

    @abstractmethod
    async def get(self, cid: Union[CIDv0, CIDv1]) -> bytes:
        pass
