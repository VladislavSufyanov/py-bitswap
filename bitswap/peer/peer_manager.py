from typing import Union, Dict, Optional, Iterator, List, TYPE_CHECKING
from logging import INFO

from cid import CIDv0, CIDv1

from .peer import Peer
from .base_peer_manager import BasePeerManager
from ..decision.ledger import Ledger
from ..wantlist.wantlist import WantList
from ..logger import get_stream_logger_colored, get_concurrent_logger

if TYPE_CHECKING:
    from ..network.base_network import BaseNetwork
    from .peer import BasePeer
    from ..connection_manager.base_connection_manager import BaseConnectionManager


class PeerManager(BasePeerManager):

    def __init__(self, connection_manager: 'BaseConnectionManager', network: 'BaseNetwork',
                 log_level: int = INFO, log_path: Optional[str] = None) -> None:
        if log_path is None:
            self._logger = get_stream_logger_colored(__name__, log_level)
        else:
            self._logger = get_concurrent_logger(__name__, log_path, log_level)
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
            self._logger.debug(f'Connected to peer, peer_cid: {peer_cid}')
        peer = Peer(peer_cid, network_peer, Ledger(WantList()))
        self._connection_manager.run_message_handlers(peer, self)
        self._peers[peer_cid] = peer
        self._logger.debug(f'Add new peer, peer_cid: {peer_cid}')
        return peer

    async def remove_peer(self, cid: Union[CIDv0, CIDv1]) -> bool:
        peer = self._peers.get(cid)
        if peer is None:
            return False
        await peer.close()
        del self._peers[cid]
        self._logger.debug(f'Remove peer, peer_cid: {cid}')
        return True

    async def disconnect(self) -> None:
        for peer in self._peers.values():
            await peer.close()
        self._logger.debug('Disconnect all peers')
