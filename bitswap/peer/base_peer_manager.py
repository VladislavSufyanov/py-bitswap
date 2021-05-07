from abc import ABCMeta, abstractmethod
from typing import Union, Dict, Tuple, Iterator, Optional, List, TYPE_CHECKING
import asyncio

from cid import CIDv0, CIDv1

if TYPE_CHECKING:
    from .peer import Peer
    from ..network.base_network import BasePeer


class BasePeerManager(metaclass=ABCMeta):

    peers: Dict[Union[CIDv0, CIDv1], Tuple['Peer', asyncio.Task]]

    @abstractmethod
    def __iter__(self) -> Iterator['Peer']:
        pass

    @abstractmethod
    def get_all_peers(self) -> List['Peer']:
        pass

    @abstractmethod
    def get_peer(self, peer_cid: Union[CIDv0, CIDv1]) -> Optional['Peer']:
        pass

    @abstractmethod
    async def connect(self, peer_cid: Union[CIDv0, CIDv1], network_peer: Optional['BasePeer'] = None) -> 'Peer':
        pass

    @abstractmethod
    async def remove_peer(self, cid: Union[CIDv0, CIDv1]) -> bool:
        pass
