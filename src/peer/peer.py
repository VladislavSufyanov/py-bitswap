from typing import Union, AsyncGenerator

from cid import CIDv0, CIDv1

from network import BasePeer


class Peer:

    def __init__(self, peer_cid: Union[CIDv0, CIDv1], network_peer: BasePeer) -> None:
        self.cid = peer_cid
        self._network_peer = network_peer

    def __aiter__(self) -> AsyncGenerator[bytes, None]:
        return self._network_peer.__aiter__()

    async def send(self, message: bytes) -> None:
        self._network_peer.send(message)
