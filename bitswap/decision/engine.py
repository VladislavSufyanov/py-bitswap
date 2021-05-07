from typing import Dict, Union, Iterable, TYPE_CHECKING, Optional
from asyncio.queues import PriorityQueue, Queue
from logging import INFO

from cid import CIDv0, CIDv1

from .ledger import Ledger
from ..task.task import Task
from ..connection_manager.sender import Sender
from ..message.proto_buff import ProtoBuff
from ..wantlist.wantlist import WantList
from .base_engine import BaseEngine
from ..logger import get_stream_logger_colored, get_concurrent_logger

if TYPE_CHECKING:
    from ..data_structure.block import Block
    from ..peer.base_peer_manager import BasePeerManager
    from ..peer.peer import Peer
    from ..message.message_entry import MessageEntry
    from ..message.bitswap_message import BitswapMessage
    from ..queue_manager.base_queue_manager import BaseQueueManager


class Engine(BaseEngine):

    def __init__(self, local_ledger: Ledger, remote_ledgers: Dict[Union[CIDv0, CIDv1], Ledger],
                 queue_manager: 'BaseQueueManager', log_level: int = INFO,
                 log_path: Optional[str] = None) -> None:
        if log_path is None:
            self._logger = get_stream_logger_colored(__name__, log_level)
        else:
            self._logger = get_concurrent_logger(__name__, log_path, log_level)
        self.local_ledger = local_ledger
        self.remote_ledgers = remote_ledgers
        self._queue_manager = queue_manager

    def handle_bit_swap_message(self, peer: 'Peer', bit_swap_message:  'BitswapMessage',
                                peer_manager: 'BasePeerManager') -> None:
        self._handle_payload(peer, bit_swap_message.payload, peer_manager)
        self._handle_presences(peer, bit_swap_message.block_presences)
        self._handle_entries(peer, bit_swap_message.want_list)

    def create_response_queue(self, peer: 'Peer') -> Queue:
        queue = self._queue_manager.create_response_queue(peer.cid)
        if queue is None:
            queue = self._queue_manager.get_response_queue(peer.cid)
        return queue

    def create_tasks_queue(self, peer: 'Peer') -> PriorityQueue:
        queue = self._queue_manager.create_tasks_queue(peer.cid)
        if queue is None:
            queue = self._queue_manager.get_tasks_queue(peer.cid)
        return queue

    def remove_response_queue(self, peer: 'Peer') -> None:
        return self._queue_manager.remove_response_queue(peer.cid)

    def remove_tasks_queue(self, peer: 'Peer') -> None:
        return self._queue_manager.remove_tasks_queue(peer.cid)

    def _handle_payload(self, peer: 'Peer', payload: Dict[Union[CIDv0, CIDv1], 'Block'],
                        peer_manager: 'BasePeerManager') -> None:
        all_peers = peer_manager.get_all_peers()
        for cid, block in payload.items():
            entry = self.local_ledger.get_entry(cid)
            if entry is not None:
                if entry.block is None:
                    entry.block = block.data
                    self._logger.debug(f'Got block from {peer.cid}, block_cid: {cid}')
                    Task.create_task(Sender.send_cancel(cid, all_peers, logger=self._logger), Task.base_callback)
                    self._logger.debug(f'Send cancel to {[p.cid for p in all_peers]}, block_cid: {cid}')
                for session in entry.sessions:
                    session.add_peer(peer, cid, have=False)
                    session.change_peer_score(peer.cid, 1)
            wants_peers = filter(lambda p: cid in p.ledger, all_peers)
            Task.create_task(Sender.send_blocks(wants_peers, (block,), self._logger), Task.base_callback)
            self._logger.debug(f'Send block to {[p.cid for p in wants_peers]}, block_cid: {cid}')

    def _handle_presences(self, peer: 'Peer',
                          block_presences: Dict[Union[CIDv0, CIDv1], 'ProtoBuff.BlockPresenceType']) -> None:
        for cid, b_presence_type in block_presences.items():
            entry = self.local_ledger.get_entry(cid)
            if entry is not None:
                if b_presence_type == ProtoBuff.BlockPresenceType.Have:
                    for session in entry.sessions:
                        session.add_peer(peer, cid)
                elif b_presence_type == ProtoBuff.BlockPresenceType.DontHave:
                    for session in entry.sessions:
                        session.change_peer_score(peer.cid, -1)

    async def _handle_entries(self, peer: 'Peer', entries: Dict[Union[CIDv0, CIDv1], 'MessageEntry']) -> None:
        queue = self._queue_manager.get_tasks_queue(peer.cid)
        if queue is not None:
            Task.create_task(self._add_entries_q_ledger(peer, queue, entries.values()), Task.base_callback)

    async def _add_entries_q_ledger(self, peer: 'Peer', queue: PriorityQueue,
                                    entries: Iterable['MessageEntry']) -> None:
        ledger = self.remote_ledgers.get(peer.cid)
        if ledger is None:
            ledger = Ledger(WantList())
            self.remote_ledgers[peer.cid] = ledger
        for entry in entries:
            ledger.wants(entry.cid, entry.priority, entry.want_type)
            await queue.put((-entry.priority, entry))
