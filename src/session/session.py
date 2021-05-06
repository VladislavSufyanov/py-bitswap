from typing import Union, Dict, List

from cid import CIDv0, CIDv1

from peer import Peer
from .peer_score import PeerScore


class Session:

    def __init__(self, min_score: int = -100) -> None:
        self._peers: Dict[Union[CIDv0, CIDv1], PeerScore] = {}
        self._min_score = min_score

    def __contains__(self, peer: Peer) -> bool:
        return peer.cid in self._peers

    def add_peer(self, peer: Peer) -> bool:
        if peer.cid in self._peers:
            return False
        self._peers[peer.cid] = PeerScore(peer)
        return True

    def change_peer_score(self, cid: Union[CIDv0, CIDv1], score_diff: int) -> bool:
        if cid not in self._peers:
            return False
        new_score = self._peers[cid].change_score(score_diff)
        if new_score < self._min_score:
            self.remove_peer(cid)
        return True

    def remove_peer(self, cid: Union[CIDv0, CIDv1]) -> bool:
        if cid not in self._peers:
            return False
        del self._peers[cid]
        return True
