from typing import Union, Dict, Optional, List, TYPE_CHECKING
import weakref
import asyncio
from logging import INFO

from cid import CIDv0, CIDv1

from .peer_score import PeerScore
from ..connection_manager.sender import Sender
from ..message.proto_buff import ProtoBuff
from ..logger import get_stream_logger_colored, get_concurrent_logger

if TYPE_CHECKING:
    from ..peer.peer import Peer
    from ..peer.base_peer_manager import BasePeerManager
    from ..wantlist.entry import Entry
    from ..network.base_network import BaseNetwork


class Session:

    def __init__(self, network: 'BaseNetwork', peer_manager: 'BasePeerManager', min_score: int = -100,
                 log_level: int = INFO, log_path: Optional[str] = None) -> None:
        if log_path is None:
            self._logger = get_stream_logger_colored(__name__, log_level)
        else:
            self._logger = get_concurrent_logger(__name__, log_path, log_level)
        self._network = network
        self._peer_manager = peer_manager
        self._peers: Dict[str, PeerScore] = {}
        self._blocks_have: Dict[str, weakref.WeakSet] = {}
        self._blocks_pending: Dict[str, weakref.WeakSet] = {}
        self._min_score = min_score

    def __contains__(self, peer: 'Peer') -> bool:
        return peer.cid in self._peers

    def add_peer(self, peer: 'Peer', block_cid: Union[CIDv0, CIDv1], have: bool = True) -> None:
        str_peer_cid = str(peer.cid)
        str_block_cid = str(block_cid)
        if str_peer_cid not in self._peers:
            self._peers[str_peer_cid] = PeerScore(peer)
            self._logger.debug(f'Add new peer to session, session: {self}, peer_cid: {str_peer_cid}')
        if have:
            if str_block_cid not in self._blocks_have:
                self._blocks_have[str_block_cid] = weakref.WeakSet()
            self._blocks_have[str_block_cid].add(self._peers[str(peer.cid)])

    def change_peer_score(self, cid: Union[CIDv0, CIDv1], score_diff: int) -> bool:
        str_cid = str(cid)
        if str_cid not in self._peers:
            return False
        new_score = self._peers[str_cid].change_score(score_diff)
        if new_score < self._min_score:
            self._logger.debug(f'Min score, session: {self}, peer_cid: {str_cid}')
            self.remove_peer(cid)
        return True

    def remove_peer(self, cid: Union[CIDv0, CIDv1]) -> bool:
        str_cid = str(cid)
        if str_cid not in self._peers:
            return False
        del self._peers[str_cid]
        self._logger.debug(f'Remove peer from session, session: {self}, peer_cid: {str_cid}')
        return True

    async def _connect(self, peers_cid: List[Union[CIDv0, CIDv1]], connect_timeout: int) -> Optional['Peer']:
        while len(peers_cid) > 0:
            p_cid = peers_cid.pop()
            try:
                peer = await asyncio.wait_for(self._peer_manager.connect(p_cid), connect_timeout)
                if peer is not None:
                    break
            except asyncio.exceptions.TimeoutError:
                self._logger.debug(f'Connect timeout, peer_cid: {p_cid}')
            except Exception as e:
                self._logger.exception(f'Connect exception, peer_cid: {p_cid}, e: {e}')
        else:
            return
        return peer

    def _get_peer_with_max_score(self, cid: Union[CIDv0, CIDv1]) -> PeerScore:
        return max(self._blocks_have[str(cid)], key=lambda p: p.score)

    async def _wait_for_have_peer(self, cid: Union[CIDv0, CIDv1], period: float = 0.1) -> PeerScore:
        str_cid = str(cid)
        while str_cid not in self._blocks_have or len(self._blocks_have[str_cid]) == 0:
            await asyncio.sleep(period)
        return self._get_peer_with_max_score(cid)

    @staticmethod
    async def _wait_for_block(entry: 'Entry', period: float = 0.1) -> Optional[bytes]:
        while entry.block is None:
            await asyncio.sleep(period)
        return entry.block

    async def get(self, entry: 'Entry', connect_timeout: int = 7, peer_act_timeout: int = 5) -> Optional[bytes]:
        str_entry_cid = str(entry.cid)
        entry.add_session(self)
        new_peers_cid = []
        if str_entry_cid not in self._blocks_have:
            self._blocks_have[str_entry_cid] = weakref.WeakSet()
        if str_entry_cid not in self._blocks_pending:
            self._blocks_pending[str_entry_cid] = weakref.WeakSet()
        if not self._peers:
            self._logger.debug(f'Session has not peers, session: {self}')
            all_peers = self._peer_manager.get_all_peers()
            if not all_peers:
                self._logger.debug(f'No active connections with peers, session: {self}')
                new_peers_cid = await self._network.find_peers(entry.cid)
                if await self._connect(new_peers_cid, connect_timeout) is None:
                    self._logger.warning(f'Cant connect to peers, session: {self}')
                    return
                all_peers = self._peer_manager.get_all_peers()
            await Sender.send_entries((entry,), all_peers, ProtoBuff.WantType.Have, logger=self._logger)
        else:
            await Sender.send_entries((entry,), (p.peer for p in self._peers.values()), ProtoBuff.WantType.Have,
                                      logger=self._logger)
        while entry.block is None:
            try:
                have_peer = await asyncio.wait_for(self._wait_for_have_peer(entry.cid), peer_act_timeout)
            except asyncio.exceptions.TimeoutError:
                self._logger.debug(f'Wait have timeout, session: {self}')
                new_peer = await self._connect(new_peers_cid, connect_timeout)
                if new_peer is None:
                    new_peers_cid = await self._network.find_peers(entry.cid)
                    new_peer = await self._connect(new_peers_cid, connect_timeout)
                if new_peer is not None:
                    await Sender.send_entries((entry,), (new_peer,), ProtoBuff.WantType.Have,
                                              logger=self._logger)
            else:
                self._blocks_have[str_entry_cid].remove(have_peer)
                if have_peer not in self._blocks_pending[str_entry_cid]:
                    self._blocks_pending[str_entry_cid].add(have_peer)
                    await Sender.send_entries((entry,), (have_peer.peer,), ProtoBuff.WantType.Block,
                                              logger=self._logger)
                    try:
                        await asyncio.wait_for(self._wait_for_block(entry), peer_act_timeout)
                    except asyncio.exceptions.TimeoutError:
                        self._logger.debug(f'Block wait timeout, block_cid: {entry.cid}')
        self._blocks_have[str_entry_cid].clear()
        self._blocks_pending[str_entry_cid].clear()
        del self._blocks_have[str_entry_cid]
        del self._blocks_pending[str_entry_cid]
        return entry.block
