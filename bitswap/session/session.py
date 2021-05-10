from typing import Union, Dict, Optional, List, TYPE_CHECKING
import weakref
import asyncio
from logging import INFO
from time import monotonic

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

    def __init__(self, network: 'BaseNetwork', peer_manager: 'BasePeerManager',
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

    def __contains__(self, peer: 'Peer') -> bool:
        return str(peer.cid) in self._peers

    def get_notify_peers(self, block_cid: Union[CIDv0, CIDv1],
                         current_peer: Optional[Union[CIDv0, CIDv1]] = None) -> List['Peer']:
        str_block_cid = str(block_cid)
        l_p = []
        for block_cont in self._blocks_have, self._blocks_pending:
            if str_block_cid in block_cont:
                l_p.extend(p.peer for p in block_cont[str_block_cid] if p.peer.cid != current_peer)
        return l_p

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

    def change_peer_score(self, cid: Union[CIDv0, CIDv1], new: float, alpha: float = 0.5) -> bool:
        str_cid = str(cid)
        if str_cid not in self._peers:
            return False
        self._peers[str_cid].change_score(new, alpha)
        return True

    def remove_peer(self, cid: Union[CIDv0, CIDv1]) -> bool:
        str_cid = str(cid)
        if str_cid not in self._peers:
            return False
        del self._peers[str_cid]
        self._logger.debug(f'Remove peer from session, session: {self}, peer_cid: {str_cid}')
        return True

    def remove_peer_from_have(self, block_cid: Union[CIDv0, CIDv1], peer: 'Peer') -> bool:
        str_cid = str(block_cid)
        if str_cid not in self._blocks_have or peer not in self._blocks_have[str_cid]:
            return False
        self._blocks_have[str_cid].remove(peer)
        return True

    async def get(self, entry: 'Entry', connect_timeout: int = 7, peer_act_timeout: int = 5,
                  ban_peer_timeout: int = 10) -> None:
        str_entry_cid = str(entry.cid)
        entry.add_session(self)
        ban_peers: Dict[str, float] = {}
        sent_w_block_to_peers: List[PeerScore] = []
        new_peers_cid: List[Union[CIDv0, CIDv1]] = []
        if str_entry_cid not in self._blocks_have:
            self._blocks_have[str_entry_cid] = weakref.WeakSet()
        if str_entry_cid not in self._blocks_pending:
            self._blocks_pending[str_entry_cid] = weakref.WeakSet()
        if not self._peers:
            self._logger.debug(f'Session has not peers, session: {self}')
            all_peers = self._peer_manager.get_all_peers()
            if not all_peers:
                self._logger.debug(f'No active connections with peers, session: {self}')
                while True:
                    new_peers_cid = await self._network.find_peers(entry.cid)
                    if not new_peers_cid:
                        self._logger.warning(f'Cant find peers, block_cid: {entry.cid}, session: {self}')
                        await asyncio.sleep(peer_act_timeout)
                    elif await self._connect(new_peers_cid, ban_peers, connect_timeout, ban_peer_timeout) is None:
                        self._logger.warning(f'Cant connect to peers, session: {self}')
                        await asyncio.sleep(peer_act_timeout)
                    else:
                        break
                all_peers = self._peer_manager.get_all_peers()
            await Sender.send_entries((entry,), all_peers, ProtoBuff.WantType.Have)
        else:
            await Sender.send_entries((entry,), (p.peer for p in self._peers.values()), ProtoBuff.WantType.Have)
        try:
            while entry.block is None:
                try:
                    have_peer = await asyncio.wait_for(self._wait_for_have_peer(entry.cid), peer_act_timeout)
                except asyncio.exceptions.TimeoutError:
                    self._logger.debug(f'Wait have timeout, session: {self}')
                    new_peer = await self._connect(new_peers_cid, ban_peers, connect_timeout, ban_peer_timeout)
                    if new_peer is None:
                        new_peers_cid = await self._network.find_peers(entry.cid)
                        new_peer = await self._connect(new_peers_cid, ban_peers, connect_timeout, ban_peer_timeout)
                    if new_peer is not None:
                        await Sender.send_entries((entry,), (new_peer,), ProtoBuff.WantType.Have)
                else:
                    self._blocks_have[str_entry_cid].remove(have_peer)
                    if have_peer not in self._blocks_pending[str_entry_cid] and have_peer.peer in self._peer_manager:
                        self._blocks_pending[str_entry_cid].add(have_peer)
                        sent_w_block_to_peers.append(have_peer)
                        await Sender.send_entries((entry,), (have_peer.peer,), ProtoBuff.WantType.Block)
                        try:
                            await asyncio.wait_for(self._wait_for_block(entry), peer_act_timeout)
                        except asyncio.exceptions.TimeoutError:
                            self._logger.debug(f'Block wait timeout, block_cid: {entry.cid}')
        finally:
            for peer in sent_w_block_to_peers:
                if peer in self._blocks_pending[str_entry_cid]:
                    self._blocks_pending[str_entry_cid].remove(peer)

    async def _connect(self, peers_cid: List[Union[CIDv0, CIDv1]], ban_peers: Dict[str, float],
                       connect_timeout: int, ban_peer_timeout: int) -> Optional['Peer']:
        unban_cid = []
        for s_cid, ban_time in ban_peers.items():
            if monotonic() - ban_time > ban_peer_timeout:
                unban_cid.append(s_cid)
        for s_cid in unban_cid:
            del ban_peers[s_cid]
        while len(peers_cid) > 0:
            p_cid = peers_cid.pop()
            if str(p_cid) not in ban_peers:
                try:
                    peer = await asyncio.wait_for(self._peer_manager.connect(p_cid), connect_timeout)
                    if peer is not None:
                        break
                except asyncio.exceptions.TimeoutError:
                    self._logger.debug(f'Connect timeout, peer_cid: {p_cid}')
                    ban_peers[str(p_cid)] = monotonic()
                except Exception as e:
                    self._logger.debug(f'Connect exception, peer_cid: {p_cid}, e: {e}')
                    ban_peers[str(p_cid)] = monotonic()
        else:
            return
        return peer

    def _get_peer_with_max_score(self, cid: Union[CIDv0, CIDv1]) -> PeerScore:
        return max(self._blocks_have[str(cid)], key=lambda p: (p.score, -p.peer.latency))

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
