from abc import ABCMeta, abstractmethod
from typing import Union, Dict, Tuple
import asyncio

from cid import CIDv0, CIDv1

from .peer import Peer


class BasePeerManager(metaclass=ABCMeta):

    peers: Dict[Union[CIDv0, CIDv1], Tuple[Peer, asyncio.Task]]

    @abstractmethod
    async def connect(self, peer_cid: Union[CIDv0, CIDv1]) -> None:
        pass

    @abstractmethod
    def remove_peer(self, cid: Union[CIDv0, CIDv1]) -> bool:
        pass
