from typing import Union, Any, Optional, TYPE_CHECKING
import logging
import asyncio
from functools import partial

from cid import CIDv0, CIDv1

from .base_bitswap import BaseBitswap
from .logger import get_stream_logger_colored, get_concurrent_logger
from .session.session import Session
from .session.session_manager import SessionManager
from .decision.ledger import Ledger
from .decision.decision import Decision
from .decision.engine import Engine
from .wantlist.wantlist import WantList
from .message.proto_buff import ProtoBuff
from .peer.peer_manager import PeerManager
from .connection_manager.connection_manager import ConnectionManager
from .task.task import Task

if TYPE_CHECKING:
    from network import BaseNetwork
    from block_storage import BaseBlockStorage


class Bitswap(BaseBitswap):

    def __init__(self, network: 'BaseNetwork', block_storage: 'BaseBlockStorage',
                 log_level: int = logging.INFO, log_path: Optional[str] = None,
                 max_block_size_have_to_block: int = 1024, task_wait_timeout: float = 0.5,
                 decision_sleep_timeout: float = 0.1, min_score: int = -100) -> None:
        if log_path is None:
            self._logger = get_stream_logger_colored(__name__, log_level)
        else:
            self._logger = get_concurrent_logger(__name__, log_path, log_level)
        self._network = network
        self._block_storage = block_storage
        self._local_ledger = Ledger(WantList())
        self._session_manager = SessionManager(min_score, log_level, log_path)
        self._engine = Engine(self._local_ledger, log_level, log_path)
        self._connection_manager = ConnectionManager(self._session_manager, self._engine, log_level, log_path)
        self._peer_manager = PeerManager(self._connection_manager, self._network, log_level, log_path)
        self._decision = Decision(self._block_storage, self._peer_manager, max_block_size_have_to_block,
                                  task_wait_timeout, decision_sleep_timeout, log_level, log_path)

    async def __aenter__(self) -> 'Bitswap':
        await self.run()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.stop()

    async def run(self):
        self._decision.run()
        self._connection_manager.run_handle_conn(self._network, self._peer_manager)

    async def stop(self):
        self._decision.stop()
        self._connection_manager.stop_handle_conn()
        await self._peer_manager.disconnect()

    async def put(self, cid: Union[CIDv0, CIDv1], block: bytes) -> bool:
        if not self._block_storage.has(cid):
            await self._block_storage.put(cid, block)
            await self._network.public(cid)
            return True
        else:
            return False

    async def get(self, cid: Union[CIDv0, CIDv1], priority: int = 1, timeout: int = 60,
                  session: Optional[Session] = None, connect_timeout: int = 7,
                  peer_act_timeout: int = 5, ban_peer_timeout: int = 10) -> Optional[bytes]:
        if self._block_storage.has(cid):
            self._logger.info(f'Get block from block storage, block_cid: {cid}')
            return await self._block_storage.get(cid)
        if session is None:
            session = self._session_manager.create_session(self._network, self._peer_manager)
        entry = self._local_ledger.get_entry(cid)
        if entry is None:
            self._local_ledger.wants(cid, priority, ProtoBuff.WantType.Block)
            entry = self._local_ledger.get_entry(cid)
        elif entry.block is not None:
            self._logger.info(f'Get block from local ledger, block_cid: {cid}')
            block = entry.block
            self._local_ledger.cancel_want(entry.cid)
            return block
        elif entry.want_type == ProtoBuff.WantType.Have or entry.priority != priority:
            entry.priority = priority
            entry.want_type = ProtoBuff.WantType.Block
        session_get_task = Task.create_task(session.get(entry, connect_timeout, peer_act_timeout, ban_peer_timeout),
                                            partial(Task.base_callback, logger=self._logger))
        try:
            await asyncio.wait_for(entry.block_event.wait(), timeout)
        except asyncio.exceptions.TimeoutError:
            self._logger.warning(f'Get timeout, block_cid: {cid}')
        session_get_task.cancel()
        block = entry.block
        if block is not None:
            self._local_ledger.cancel_want(entry.cid)
            self._logger.info(f'Session found block, block_cid: {cid}')
        return block
