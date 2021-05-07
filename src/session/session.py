from typing import Union, Dict, Optional, List, TYPE_CHECKING
import weakref
import asyncio

from cid import CIDv0, CIDv1

from .peer_score import PeerScore
from connection_manager.sender import Sender
from message.proto_buff import ProtoBuff

if TYPE_CHECKING:
    from peer.peer import Peer
    from peer.base_peer_manager import BasePeerManager
    from wantlist.entry import Entry
    from network.base_network import BaseNetwork


class Session:

    def __init__(self, network: 'BaseNetwork', peer_manager: 'BasePeerManager', min_score: int = -100) -> None:
        self._network = network
        self._peer_manager = peer_manager
        self._peers: Dict[Union[CIDv0, CIDv1], PeerScore] = {}
        self._blocks_have: Dict[Union[CIDv0, CIDv1], weakref.WeakSet] = {}
        self._blocks_pending: Dict[Union[CIDv0, CIDv1], weakref.WeakSet] = {}
        self._min_score = min_score

    def __contains__(self, peer: 'Peer') -> bool:
        return peer.cid in self._peers

    def add_peer(self, peer: 'Peer', block_cid: Union[CIDv0, CIDv1], have: bool = True) -> None:
        if peer.cid not in self._peers:
            self._peers[peer.cid] = PeerScore(peer)
        if have:
            if block_cid not in self._blocks_have:
                self._blocks_have[block_cid] = weakref.WeakSet()
            self._blocks_have[block_cid].add(self._peers[peer.cid])

    def change_peer_score(self, cid: Union[CIDv0, CIDv1], score_diff: int) -> bool:
        if cid not in self._peers:
            return False
        new_score = self._peers[cid].change_score(score_diff)
        if new_score < self._min_score:
            self.remove_peer(cid)
        return True

    def remove_peer(self, cid: Union[CIDv0, CIDv1]) -> bool:
        if cid not in self._peers:
            return False
        del self._peers[cid]
        return True

    async def _connect(self, peers_cid: List[Union[CIDv0, CIDv1]], connect_timeout: int) -> Optional['Peer']:
        while len(peers_cid) > 0:
            try:
                peer = await asyncio.wait_for(self._peer_manager.connect(peers_cid.pop()), connect_timeout)
                break
            except asyncio.exceptions.TimeoutError:
                ...  # log
            except Exception as e:
                ...  # log
        else:
            return
        return peer

    def _get_peer_with_max_score(self, cid: Union[CIDv0, CIDv1]) -> 'Peer':
        return max(self._blocks_have[cid], key=lambda p: p.score)

    async def _wait_for_have_peer(self, cid: Union[CIDv0, CIDv1], period: float = 0.1) -> 'Peer':
        while cid not in self._blocks_have or len(self._blocks_have[cid]) == 0:
            await asyncio.sleep(period)
        return self._get_peer_with_max_score(cid)

    @staticmethod
    async def _wait_for_block(entry: 'Entry', period: float = 0.1) -> Optional[bytes]:
        while entry.block is None:
            await asyncio.sleep(period)
        return entry.block

    async def get(self, entry: 'Entry', connect_timeout: int = 7, peer_act_timeout: int = 5) -> Optional[bytes]:
        entry.add_session(self)
        new_peers_cid = []
        if entry.cid not in self._blocks_have:
            self._blocks_have[entry.cid] = weakref.WeakSet()
        if entry.cid not in self._blocks_pending:
            self._blocks_pending[entry.cid] = weakref.WeakSet()
        if not self._peers:
            all_peers = self._peer_manager.get_all_peers()
            if not all_peers:
                new_peers_cid = await self._network.find_peers(entry.cid)
                if await self._connect(new_peers_cid, connect_timeout) is None:
                    return
                all_peers = self._peer_manager.get_all_peers()
            await Sender.send_entries((entry,), all_peers, ProtoBuff.WantType.Have)
        else:
            await Sender.send_entries((entry,), (p.peer for p in self._peers.values()), ProtoBuff.WantType.Have)
        while entry.block is None:
            try:
                have_peer = await asyncio.wait_for(self._wait_for_have_peer(entry.cid), peer_act_timeout)
            except asyncio.exceptions.TimeoutError:
                new_peer = await self._connect(new_peers_cid, connect_timeout)
                if new_peer is None:
                    new_peers_cid = await self._network.find_peers(entry.cid)
                    new_peer = await self._connect(new_peers_cid, connect_timeout)
                if new_peer is not None:
                    await Sender.send_entries((entry,), (new_peer,), ProtoBuff.WantType.Have)
            else:
                self._blocks_have[entry.cid].remove(have_peer)
                if have_peer not in self._blocks_pending[entry.cid]:
                    self._blocks_pending[entry.cid].add(have_peer)
                    await Sender.send_entries((entry,), (have_peer,), ProtoBuff.WantType.Block)
                    try:
                        await asyncio.wait_for(self._wait_for_block(entry), peer_act_timeout)
                    except asyncio.exceptions.TimeoutError:
                        ...  # log
        self._blocks_have[entry.cid].clear()
        self._blocks_pending[entry.cid].clear()
        del self._blocks_have[entry.cid]
        del self._blocks_pending[entry.cid]
        return entry.block
