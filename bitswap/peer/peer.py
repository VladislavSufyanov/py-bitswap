from typing import Union, AsyncGenerator, TYPE_CHECKING
from asyncio.queues import Queue, PriorityQueue
from time import monotonic

from cid import CIDv0, CIDv1

if TYPE_CHECKING:
    from ..network.base_network import BasePeer
    from ..decision.ledger import Ledger


class Peer:

    def __init__(self, peer_cid: Union[CIDv0, CIDv1], network_peer: 'BasePeer', ledger: 'Ledger') -> None:
        self.cid = peer_cid
        self.ledger = ledger
        self.response_queue = Queue()
        self.tasks_queue = PriorityQueue()
        self.last_active = monotonic()
        self._network_peer = network_peer

    def __aiter__(self) -> AsyncGenerator[bytes, None]:
        return self._network_peer.__aiter__()

    async def send(self, message: bytes) -> None:
        await self._network_peer.send(message)

    async def close(self) -> None:
        await self._network_peer.close()
