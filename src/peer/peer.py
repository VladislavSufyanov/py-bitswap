from typing import Union, AsyncGenerator
from asyncio import Lock

from cid import CIDv0, CIDv1

from network import BasePeer
from decision import Ledger


class Peer:

    def __init__(self, peer_cid: Union[CIDv0, CIDv1], network_peer: BasePeer, ledger: Ledger) -> None:
        self.cid = peer_cid
        self.ledger = ledger
        self._network_peer = network_peer
        self._send_lock = Lock()

    def __aiter__(self) -> AsyncGenerator[bytes, None]:
        return self._network_peer.__aiter__()

    async def send(self, message: bytes) -> None:
        async with self._send_lock:
            await self._network_peer.send(message)

    async def close(self) -> None:
        await self._network_peer.close()
