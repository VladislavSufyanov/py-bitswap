from typing import Union, Dict, Tuple
import asyncio

from cid import CIDv0, CIDv1

from network import BaseNetwork
from .peer import Peer
from .base_peer_manager import BasePeerManager
from connection_manager import BaseConnectionManager


class PeerManager(BasePeerManager):

    def __init__(self, connection_manager: BaseConnectionManager, network: BaseNetwork) -> None:
        self._connection_manager = connection_manager
        self._network = network
        self._peers: Dict[Union[CIDv0, CIDv1], Tuple[Peer, asyncio.Task]] = {}

    async def connect(self, peer_cid: Union[CIDv0, CIDv1]) -> None:
        network_peer = await self._network.connect(peer_cid)
        peer = Peer(peer_cid, network_peer)
        message_handler = self._connection_manager.run_message_handler(peer)
        self._peers[peer_cid] = peer, message_handler

    def remove_peer(self, cid: Union[CIDv0, CIDv1]) -> bool:
        if cid not in self._peers:
            return False
        del self._peers[cid]
        return True
