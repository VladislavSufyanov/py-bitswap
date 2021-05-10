from typing import Optional, Iterable, TYPE_CHECKING, List

from .base_queue_manager import BaseQueueManager

if TYPE_CHECKING:
    from ..peer.peer import Peer


class QueueManager(BaseQueueManager):

    @staticmethod
    def get_peers_smallest_response_queue(peers: Iterable['Peer']) -> Optional[List['Peer']]:
        s_peers = sorted(peers, key=lambda p: p.response_queue.qsize())
        if not s_peers:
            return
        peers = [s_peers[0]]
        min_size = s_peers[0].response_queue.qsize()
        for i in range(1, len(s_peers)):
            if s_peers[i].response_queue.qsize() == min_size:
                peers.append(s_peers[i])
            else:
                break
        return peers
