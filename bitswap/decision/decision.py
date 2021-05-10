from typing import Optional, Any, NoReturn, Union, TYPE_CHECKING
import asyncio
from logging import INFO
from functools import partial

from cid import CIDv0, CIDv1

from ..task.task import Task
from ..message.proto_buff import ProtoBuff
from ..connection_manager.sender import Sender
from ..data_structure.block import Block
from .base_decision import BaseDecision
from ..logger import get_stream_logger_colored, get_concurrent_logger
from ..queue_manager.queue_manager import QueueManager

if TYPE_CHECKING:
    from ..message.message_entry import MessageEntry
    from ..block_storage.base_block_storage import BaseBlockStorage
    from ..peer.base_peer_manager import BasePeerManager


class Decision(BaseDecision):

    def __init__(self, block_storage: 'BaseBlockStorage', peer_manager: 'BasePeerManager',
                 max_block_size_have_to_block: int = 1024, task_wait_timeout: float = 0.5,
                 sleep_timeout: float = 0.1, log_level: int = INFO, log_path: Optional[str] = None) -> None:
        if log_path is None:
            self._logger = get_stream_logger_colored(__name__, log_level)
        else:
            self._logger = get_concurrent_logger(__name__, log_path, log_level)
        self._block_storage = block_storage
        self._peer_manager = peer_manager
        self._max_block_size_have_to_block = max_block_size_have_to_block
        self._task_wait_timeout = task_wait_timeout
        self._sleep_timeout = sleep_timeout
        self._decision_task: Optional[asyncio.Task] = None

    def run(self) -> None:
        if self._decision_task is None:
            self._decision_task = Task.create_task(self._decision(), partial(Task.base_callback, logger=self._logger))

    def stop(self) -> None:
        self._decision_task.cancel()
        self._decision_task = None

    def __enter__(self) -> 'Decision':
        self.run()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    async def _send_block(self, peer_cid: Union[CIDv0, CIDv1],
                          block_cid: Union[CIDv0, CIDv1]) -> None:
        block = Block(block_cid, await self._block_storage.get(block_cid))
        peer = self._peer_manager.get_peer(peer_cid)
        peer.bytes_send += len(block)
        await Sender.send_blocks((peer,), (block,))
        self._logger.debug(f'Sent block, peer_cid: {peer_cid}, block_cid: {block_cid}')

    async def _send_have(self, peer_cid: Union[CIDv0, CIDv1],
                         block_cid: Union[CIDv0, CIDv1]) -> None:
        await Sender.send_presence(block_cid, (self._peer_manager.get_peer(peer_cid),),
                                   ProtoBuff.BlockPresenceType.Have)
        self._logger.debug(f'Sent have, peer_cid: {peer_cid}, block_cid: {block_cid}')

    async def _send_do_not_have(self, peer_cid: Union[CIDv0, CIDv1],
                                block_cid: Union[CIDv0, CIDv1]) -> None:
        await Sender.send_presence(block_cid, (self._peer_manager.get_peer(peer_cid),),
                                   ProtoBuff.BlockPresenceType.DontHave)
        self._logger.debug(f'Sent do not have, peer_cid: {peer_cid}, block_cid: {block_cid}')

    async def _send_block_or_do_not_have(self, peer_cid: Union[CIDv0, CIDv1],
                                         block_cid: Union[CIDv0, CIDv1]) -> None:
        if self._block_storage.has(block_cid):
            await self._send_block(peer_cid, block_cid)
        else:
            await self._send_do_not_have(peer_cid, block_cid)

    async def _decision(self) -> NoReturn:
        while True:
            try:
                peers_sm_q = QueueManager.get_peers_smallest_response_queue(self._peer_manager.get_all_peers())
                if peers_sm_q is None:
                    await asyncio.sleep(self._sleep_timeout)
                else:
                    peer_not_empty_tasks_queue = []
                    for peer_s_q in peers_sm_q:
                        if peer_s_q.tasks_queue.qsize() > 0:
                            peer_not_empty_tasks_queue.append(peer_s_q)
                    if not peer_not_empty_tasks_queue:
                        await asyncio.sleep(self._sleep_timeout)
                    else:
                        peer_high_rank = max(peer_not_empty_tasks_queue, key=lambda p: p.peer_rank)
                        peer_cid = peer_high_rank.cid
                        ledger = peer_high_rank.ledger
                        tasks_queue = peer_high_rank.tasks_queue
                        entry: 'MessageEntry' = await asyncio.wait_for(tasks_queue.get(), self._task_wait_timeout)
                        while entry.cid not in ledger:
                            _, entry = await asyncio.wait_for(tasks_queue.get(), self._task_wait_timeout)
                        if entry.want_type == ProtoBuff.WantType.Have:
                            wants = ledger.get_entry(entry.cid)
                            if wants.want_type == ProtoBuff.WantType.Block:
                                await self._send_block_or_do_not_have(peer_cid, entry.cid)
                            elif wants.want_type == ProtoBuff.WantType.Have:
                                if self._block_storage.has(entry.cid):
                                    if await self._block_storage.size(entry.cid) <= \
                                            self._max_block_size_have_to_block:
                                        await self._send_block(peer_cid, entry.cid)
                                    else:
                                        await self._send_have(peer_cid, entry.cid)
                                elif entry.send_do_not_have:
                                    await self._send_do_not_have(peer_cid, entry.cid)
                            else:
                                self._logger.warning(f'Bad wants want type, want_type: {wants.want_type}, '
                                                     f'cid: {entry.cid}')
                        elif entry.want_type == ProtoBuff.WantType.Block:
                            await self._send_block_or_do_not_have(peer_cid, entry.cid)
                        else:
                            self._logger.warning(f'Bad task entry want type, want_type: {entry.want_type}, '
                                                 f'cid: {entry.cid}')
            except asyncio.exceptions.TimeoutError:
                pass
            except asyncio.exceptions.CancelledError:
                raise
            except Exception as e:
                self._logger.exception(f'Decision work exception, e: {e}')
