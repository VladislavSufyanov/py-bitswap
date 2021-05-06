from abc import ABCMeta, abstractmethod
from typing import Union, Dict

from cid import CIDv0, CIDv1


class BaseBlockStorage(metaclass=ABCMeta):

    @abstractmethod
    async def get(self, cid: Union[CIDv0, CIDv1]) -> bytes:
        pass

    @abstractmethod
    async def put(self, cid: Union[CIDv0, CIDv1], block: bytes) -> None:
        pass

    @abstractmethod
    async def put_many(self, blocks: Dict[Union[CIDv0, CIDv1], bytes]) -> None:
        pass

    @abstractmethod
    def has(self, cid: Union[CIDv0, CIDv1]) -> bool:
        pass

    @abstractmethod
    async def size(self, cid: Union[CIDv0, CIDv1]) -> int:
        pass
