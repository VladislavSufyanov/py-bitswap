from typing import Union, Any, Optional, Dict, TYPE_CHECKING
import logging
import asyncio

from cid import CIDv0, CIDv1

from base_bitswap import BaseBitswap
from logger.logger import get_stream_logger
from session.session import Session
from session.session_manager import SessionManager
from decision.ledger import Ledger
from decision.decision import Decision
from decision.engine import Engine
from wantlist.wantlist import WantList
from message.proto_buff import ProtoBuff
from peer.peer_manager import PeerManager
from connection_manager.connection_manager import ConnectionManager
from queue_manager.queue_manager import QueueManager

if TYPE_CHECKING:
    from network.base_network import BaseNetwork
    from block_storage.base_block_storage import BaseBlockStorage


class Bitswap(BaseBitswap):

    def __init__(self, network: 'BaseNetwork', block_storage: 'BaseBlockStorage',
                 logger: Optional[logging.Logger] = None) -> None:
        self._network = network
        self._block_storage = block_storage
        self._local_ledger = Ledger(WantList())
        self._remote_ledgers: Dict[Union[CIDv0, CIDv1], Ledger] = {}
        self._queue_manager = QueueManager()
        self._session_manager = SessionManager()
        self._engine = Engine(self._local_ledger, self._remote_ledgers, self._queue_manager)
        self._connection_manager = ConnectionManager(self._session_manager, self._engine)
        self._peer_manager = PeerManager(self._connection_manager, self._network)
        self._decision = Decision(self._queue_manager, self._block_storage, self._remote_ledgers,
                                  self._peer_manager)
        self._logger = logger if logger is not None else get_stream_logger(__name__, logging.INFO)

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
                  session: Optional[Session] = None) -> Optional[bytes]:
        if self._block_storage.has(cid):
            return await self._block_storage.get(cid)
        if session is None:
            session = self._session_manager.create_session(self._network, self._peer_manager)
        entry = self._local_ledger.get_entry(cid)
        if entry is None:
            self._local_ledger.wants(cid, priority, ProtoBuff.WantType.Block)
        elif entry.block is not None:
            return entry.block
        elif entry.want_type == ProtoBuff.WantType.Have or entry.priority != priority:
            entry.priority = priority
            entry.want_type = ProtoBuff.WantType.Block
        try:
            await asyncio.wait_for(session.get(entry), timeout)
        except asyncio.exceptions.TimeoutError:
            ...  # log
        block = entry.block
        if block is not None:
            self._local_ledger.cancel_want(entry.cid)
        return block
