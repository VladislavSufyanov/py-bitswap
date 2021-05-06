from typing import Dict, Union, Iterable
from asyncio.queues import PriorityQueue, Queue

from cid import CIDv0, CIDv1

from .ledger import Ledger
from data_structure import Block
from peer import BasePeerManager, Peer
from task import Task
from connection_manager import Sender
from message import ProtoBuff, MessageEntry, BitswapMessage
from queue_manager import BaseQueueManager
from .base_engine import BaseEngine
from wantlist import WantList


class Engine(BaseEngine):

    def __init__(self, local_ledger: Ledger, remote_ledgers: Dict[Union[CIDv0, CIDv1], Ledger],
                 peer_manager: BasePeerManager, queue_manager: BaseQueueManager) -> None:
        self.local_ledger = local_ledger
        self.remote_ledgers = remote_ledgers
        self._peer_manager = peer_manager
        self._queue_manager = queue_manager

    def handle_bit_swap_message(self, peer: Peer, bit_swap_message:  BitswapMessage) -> None:
        self._handle_payload(peer, bit_swap_message.payload)
        self._handle_presences(peer, bit_swap_message.block_presences)
        self._handle_entries(peer, bit_swap_message.want_list)

    def create_response_queue(self, peer: Peer) -> Queue:
        queue = self._queue_manager.create_response_queue(peer.cid)
        if queue is None:
            queue = self._queue_manager.get_response_queue(peer.cid)
        return queue

    def create_tasks_queue(self, peer: Peer) -> PriorityQueue:
        queue = self._queue_manager.create_tasks_queue(peer.cid)
        if queue is None:
            queue = self._queue_manager.get_tasks_queue(peer.cid)
        return queue

    def remove_response_queue(self, peer: Peer) -> None:
        return self._queue_manager.remove_response_queue(peer.cid)

    def remove_tasks_queue(self, peer: Peer) -> None:
        return self._queue_manager.remove_tasks_queue(peer.cid)

    def _handle_payload(self, peer: Peer, payload: Dict[Union[CIDv0, CIDv1], Block]) -> None:
        all_peers = self._peer_manager.get_all_peers()
        for cid, block in payload.items():
            entry = self.local_ledger.get_entry(cid)
            if entry is not None:
                entry.block = block.data
                for session in entry.sessions:
                    if peer not in session:
                        session.add_peer(peer)
                    session.change_peer_score(peer.cid, 1)
                Task.create_task(Sender.send_cancel(cid, all_peers), Task.base_callback)
            wants_peers = filter(lambda p: cid in p.ledger, all_peers)
            Task.create_task(Sender.send_blocks(wants_peers, (block,)), Task.base_callback)

    def _handle_presences(self, peer: Peer,
                          block_presences: Dict[Union[CIDv0, CIDv1], 'ProtoBuff.BlockPresenceType']) -> None:
        for cid, b_presence_type in block_presences.items():
            entry = self.local_ledger.get_entry(cid)
            if entry is not None:
                if b_presence_type == ProtoBuff.BlockPresenceType.Have:
                    for session in entry.sessions:
                        if peer not in session:
                            session.add_peer(peer)
                elif b_presence_type == ProtoBuff.BlockPresenceType.DontHave:
                    for session in entry.sessions:
                        session.change_peer_score(peer.cid, -1)

    async def _handle_entries(self, peer: Peer, entries: Dict[Union[CIDv0, CIDv1], MessageEntry]) -> None:
        queue = self._queue_manager.get_tasks_queue(peer.cid)
        if queue is not None:
            Task.create_task(self._add_entries_q_ledger(peer, queue, entries.values()), Task.base_callback)

    async def _add_entries_q_ledger(self, peer: Peer, queue: PriorityQueue,
                                    entries: Iterable[MessageEntry]) -> None:
        ledger = self.remote_ledgers.get(peer.cid)
        if ledger is None:
            ledger = Ledger(WantList())
            self.remote_ledgers[peer.cid] = ledger
        for entry in entries:
            ledger.wants(entry.cid, entry.priority, entry.want_type)
            await queue.put((-entry.priority, entry))
