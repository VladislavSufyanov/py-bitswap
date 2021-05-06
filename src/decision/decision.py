from typing import Optional, Any, NoReturn, Dict, Union
import asyncio

from cid import CIDv0, CIDv1

from .ledger import Ledger
from queue_manager import BaseQueueManager
from task import Task
from message import MessageEntry, ProtoBuff
from block_storage import BaseBlockStorage
from connection_manager import Sender
from peer import BasePeerManager
from data_structure import Block


class Decision:

    def __init__(self, queue_manager: BaseQueueManager, block_storage: BaseBlockStorage,
                 remote_ledgers: Dict[Union[CIDv0, CIDv1], Ledger], peer_manager: BasePeerManager,
                 max_block_size_have_to_block: int = 1024, task_wait_timeout: float = 0.5) -> None:
        self._queue_manager = queue_manager
        self._block_storage = block_storage
        self._remote_ledgers = remote_ledgers
        self._peer_manager = peer_manager
        self._max_block_size_have_to_block = max_block_size_have_to_block
        self._task_wait_timeout = task_wait_timeout
        self._decision_task: Optional[asyncio.Task] = None

    def run(self) -> None:
        if self._decision_task is not None:
            self._decision_task = Task.create_task(self._decision(), Task.base_callback)

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
        await Sender.send_blocks((self._peer_manager.get_peer(peer_cid),), (block,))

    async def _send_have(self, peer_cid: Union[CIDv0, CIDv1],
                         block_cid: Union[CIDv0, CIDv1]) -> None:
        await Sender.send_presence(block_cid, (self._peer_manager.get_peer(peer_cid),),
                                   ProtoBuff.BlockPresenceType.Have)

    async def _send_do_not_have(self, peer_cid: Union[CIDv0, CIDv1],
                                block_cid: Union[CIDv0, CIDv1]) -> None:
        await Sender.send_presence(block_cid, (self._peer_manager.get_peer(peer_cid),),
                                   ProtoBuff.BlockPresenceType.DontHave)

    async def _send_block_or_do_not_have(self, peer_cid: Union[CIDv0, CIDv1],
                                         block_cid: Union[CIDv0, CIDv1]) -> None:
        if self._block_storage.has(block_cid):
            await self._send_block(peer_cid, block_cid)
        else:
            await self._send_do_not_have(peer_cid, block_cid)

    async def _decision(self) -> NoReturn:
        while True:
            try:
                peer_cid, response_queue = self._queue_manager.get_smallest_response_queue()
                ledger = self._remote_ledgers.get(peer_cid)
                if ledger is not None:
                    tasks_queue = self._queue_manager.get_tasks_queue(peer_cid)
                    _, entry = await asyncio.wait_for(tasks_queue.get(), self._task_wait_timeout)
                    entry: MessageEntry
                    while entry.cid not in ledger:
                        _, entry = await asyncio.wait_for(tasks_queue.get(), self._task_wait_timeout)
                    if entry.want_type == ProtoBuff.WantType.Have:
                        wants = ledger.get_entry(entry.cid)
                        if wants.want_type == ProtoBuff.WantType.Block:
                            await self._send_block_or_do_not_have(peer_cid, entry.cid)
                        elif wants.want_type == ProtoBuff.WantType.Have:
                            if self._block_storage.has(entry.cid):
                                if await self._block_storage.size(entry.cid) <= self._max_block_size_have_to_block:
                                    await self._send_block(peer_cid, entry.cid)
                                else:
                                    await self._send_have(peer_cid, entry.cid)
                            elif entry.send_do_not_have:
                                await self._send_do_not_have(peer_cid, entry.cid)
                        else:
                            ...  # log
                    elif entry.want_type == ProtoBuff.WantType.Block:
                        await self._send_block_or_do_not_have(peer_cid, entry.cid)
                    else:
                        ...  # log
            except asyncio.exceptions.TimeoutError:
                pass
            except Exception as e:
                ...  # log
