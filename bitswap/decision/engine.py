from typing import Dict, Union, Iterable, TYPE_CHECKING, Optional
from logging import INFO
from functools import partial

from cid import CIDv0, CIDv1

from .ledger import Ledger
from ..task.task import Task
from ..connection_manager.sender import Sender
from ..message.proto_buff import ProtoBuff
from .base_engine import BaseEngine
from ..logger import get_stream_logger_colored, get_concurrent_logger

if TYPE_CHECKING:
    from ..data_structure.block import Block
    from ..peer.base_peer_manager import BasePeerManager
    from ..peer.peer import Peer
    from ..message.message_entry import MessageEntry
    from ..message.bitswap_message import BitswapMessage


class Engine(BaseEngine):

    def __init__(self, local_ledger: Ledger, log_level: int = INFO, log_path: Optional[str] = None) -> None:
        if log_path is None:
            self._logger = get_stream_logger_colored(__name__, log_level)
        else:
            self._logger = get_concurrent_logger(__name__, log_path, log_level)
        self.local_ledger = local_ledger

    def handle_bit_swap_message(self, peer: 'Peer', bit_swap_message:  'BitswapMessage',
                                peer_manager: 'BasePeerManager') -> None:
        self._handle_payload(peer, bit_swap_message.payload, peer_manager)
        self._handle_presences(peer, bit_swap_message.block_presences)
        self._handle_entries(peer, bit_swap_message.want_list)

    def _handle_payload(self, peer: 'Peer', payload: Dict[Union[CIDv0, CIDv1], 'Block'],
                        peer_manager: 'BasePeerManager') -> None:
        all_peers = peer_manager.get_all_peers()
        for cid, block in payload.items():
            entry = self.local_ledger.get_entry(cid)
            if entry is not None:
                cancel_peers = []
                for session in entry.sessions:
                    session.add_peer(peer, cid, have=False)
                    session.change_peer_score(peer.cid, 1)
                    if entry.block is None:
                        cancel_peers.extend(session.get_notify_peers(cid, peer.cid))
                if entry.block is None:
                    entry.block = block.data
                    self._logger.debug(f'Got block from {peer.cid}, block_cid: {cid}')
                    if cancel_peers:
                        Task.create_task(Sender.send_cancel(cid, cancel_peers),
                                         partial(Task.base_callback, logger=self._logger))
                        self._logger.debug(f'Send cancel to {[str(p.cid) for p in all_peers]}, block_cid: {cid}')
            wants_peers = list(filter(lambda p: cid in p.ledger, all_peers))
            if wants_peers:
                Task.create_task(Sender.send_blocks(wants_peers, (block,)),
                                 partial(Task.base_callback, logger=self._logger))
                self._logger.debug(f'Send block to {[str(p.cid) for p in wants_peers]}, block_cid: {cid}')

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

    def _handle_entries(self, peer: 'Peer', entries: Dict[Union[CIDv0, CIDv1], 'MessageEntry']) -> None:
        Task.create_task(self._add_entries_q_ledger(peer, entries.values()),
                         partial(Task.base_callback, logger=self._logger))

    @staticmethod
    async def _add_entries_q_ledger(peer: 'Peer', entries: Iterable['MessageEntry']) -> None:
        for entry in entries:
            peer.ledger.wants(entry.cid, entry.priority, entry.want_type)
            await peer.tasks_queue.put((-entry.priority, entry))
