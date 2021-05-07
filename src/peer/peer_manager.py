from typing import Union, Dict, Optional, Iterator, List, TYPE_CHECKING

from cid import CIDv0, CIDv1

from .peer import Peer
from .base_peer_manager import BasePeerManager
from decision.ledger import Ledger
from wantlist.wantlist import WantList

if TYPE_CHECKING:
    from network.base_network import BaseNetwork
    from .peer import BasePeer
    from connection_manager.base_connection_manager import BaseConnectionManager


class PeerManager(BasePeerManager):

    def __init__(self, connection_manager: 'BaseConnectionManager', network: 'BaseNetwork') -> None:
        self._connection_manager = connection_manager
        self._network = network
        self._peers: Dict[Union[CIDv0, CIDv1], Peer] = {}

    def __iter__(self) -> Iterator[Peer]:
        return self._peers.values().__iter__()

    def get_all_peers(self) -> List[Peer]:
        return list(self._peers.values())

    def get_peer(self, peer_cid: Union[CIDv0, CIDv1]) -> Optional[Peer]:
        return self._peers.get(peer_cid)

    async def connect(self, peer_cid: Union[CIDv0, CIDv1], network_peer: Optional['BasePeer'] = None) -> Peer:
        if network_peer is None:
            network_peer = await self._network.connect(peer_cid)
        peer = Peer(peer_cid, network_peer, Ledger(WantList()))
        self._connection_manager.run_message_handlers(peer, self)
        self._peers[peer_cid] = peer
        return peer

    async def remove_peer(self, cid: Union[CIDv0, CIDv1]) -> bool:
        peer = self._peers.get(cid)
        if peer is None:
            return False
        await peer.close()
        del self._peers[cid]
        return True

    async def disconnect(self) -> None:
        for peer in self._peers.values():
            await peer.close()
