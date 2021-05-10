import asyncio
from typing import Union, Dict, Optional, Iterator, List, TYPE_CHECKING, Any, NoReturn
from logging import INFO
from time import monotonic
from functools import partial

from cid import CIDv0, CIDv1

from .peer import Peer
from .base_peer_manager import BasePeerManager
from ..decision.ledger import Ledger
from ..wantlist.wantlist import WantList
from ..logger import get_stream_logger_colored, get_concurrent_logger
from ..task.task import Task

if TYPE_CHECKING:
    from ..network.base_network import BaseNetwork
    from .peer import BasePeer
    from ..connection_manager.base_connection_manager import BaseConnectionManager


class PeerManager(BasePeerManager):

    def __init__(self, connection_manager: 'BaseConnectionManager', network: 'BaseNetwork',
                 max_no_active_time: int = 3600, check_no_active_ping_period: int = 30,
                 log_level: int = INFO, log_path: Optional[str] = None) -> None:
        if log_path is None:
            self._logger = get_stream_logger_colored(__name__, log_level)
        else:
            self._logger = get_concurrent_logger(__name__, log_path, log_level)
        self._connection_manager = connection_manager
        self._network = network
        self._max_no_active_time = max_no_active_time
        self._check_no_active_ping_period = check_no_active_ping_period
        self._peers: Dict[str, Peer] = {}
        self._disconnect_task: Optional[asyncio.Task] = None

    def __contains__(self, peer: Peer):
        return str(peer.cid) in self._peers

    def __iter__(self) -> Iterator[Peer]:
        return self._peers.values().__iter__()

    def __enter__(self) -> 'PeerManager':
        self.run()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    def run(self) -> None:
        self._disconnect_task = Task.create_task(self.disconnect_no_active_peers(),
                                                 partial(Task.base_callback, logger=self._logger))

    def stop(self) -> None:
        self._disconnect_task.cancel()
        self._disconnect_task = None

    def get_all_peers(self) -> List[Peer]:
        return list(self._peers.values())

    def get_peer(self, peer_cid: Union[CIDv0, CIDv1]) -> Optional[Peer]:
        return self._peers.get(str(peer_cid))

    async def connect(self, peer_cid: Union[CIDv0, CIDv1],
                      network_peer: Optional['BasePeer'] = None) -> Optional[Peer]:
        str_peer_cid = str(peer_cid)
        if str_peer_cid in self._peers:
            return
        if network_peer is None:
            network_peer = await self._network.connect(peer_cid)
            self._logger.debug(f'Connected to peer, peer_cid: {peer_cid}')
        peer = Peer(peer_cid, network_peer, Ledger(WantList()))
        self._connection_manager.run_message_handlers(peer, self)
        self._peers[str_peer_cid] = peer
        self._logger.debug(f'Add new peer, peer_cid: {peer_cid}')
        return peer

    async def remove_peer(self, cid: Union[CIDv0, CIDv1]) -> bool:
        str_cid = str(cid)
        peer = self._peers.get(str_cid)
        if peer is None:
            return False
        if await self._disconnect_peer(peer):
            del self._peers[str_cid]
            self._logger.debug(f'Remove peer, peer_cid: {cid}')
            return True
        else:
            return False

    async def disconnect(self) -> None:
        for peer in self:
            await self._disconnect_peer(peer)
        self._logger.debug('Disconnect all peers')

    async def disconnect_no_active_peers(self) -> NoReturn:
        while True:
            for peer in self:
                if monotonic() - peer.last_active > self._max_no_active_time:
                    self._logger.debug(f'Peer no active, peer_cid: {peer.cid}')
                    res = await self._disconnect_peer(peer)
                    if res:
                        self._logger.debug(f'Connection was terminated, peer_cid: {peer.cid}')
                await peer.ping()
            await asyncio.sleep(self._check_no_active_ping_period)

    async def _disconnect_peer(self, peer: Peer) -> bool:
        try:
            await peer.close()
        except Exception as e:
            self._logger.exception(f'Close connection with peer exception, peer_cid: {peer.cid}, e: {e}')
            return False
        return True
