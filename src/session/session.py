from typing import Union, Dict, Tuple
import asyncio

from cid import CIDv0, CIDv1

from peer import Peer


class Session:

    def __iter__(self) -> None:
        self._peers: Dict[Union[CIDv0, CIDv1], Tuple[Peer, asyncio.Task]] = {}

    def remove_peer(self, cid: Union[CIDv0, CIDv1]) -> bool:
        if cid not in self._peers:
            return False
        del self._peers[cid]
        return True
