from typing import Union
from abc import ABCMeta, abstractmethod

from cid import CIDv0, CIDv1

from .base_peer import BasePeer


class BaseNetwork(metaclass=ABCMeta):

    @abstractmethod
    async def connect(self, peer_cid: Union[CIDv0, CIDv1]) -> BasePeer:
        pass
