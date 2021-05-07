from typing import Union, List, AsyncGenerator, Tuple, TYPE_CHECKING
from abc import ABCMeta, abstractmethod

from cid import CIDv0, CIDv1

if TYPE_CHECKING:
    from .base_peer import BasePeer


class BaseNetwork(metaclass=ABCMeta):

    @abstractmethod
    async def connect(self, peer_cid: Union[CIDv0, CIDv1]) -> 'BasePeer':
        pass

    @abstractmethod
    async def public(self, block_cid: Union[CIDv0, CIDv1]) -> None:
        pass

    @abstractmethod
    async def find_peers(self, block_cid: Union[CIDv0, CIDv1]) -> List[Union[CIDv0, CIDv1]]:
        pass

    @abstractmethod
    def new_connections(self) -> AsyncGenerator[Tuple[Union[CIDv0, CIDv1], 'BasePeer'], None]:
        pass
