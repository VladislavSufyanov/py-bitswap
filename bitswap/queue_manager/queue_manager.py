from typing import Optional, Iterable, TYPE_CHECKING
from random import choice

from .base_queue_manager import BaseQueueManager

if TYPE_CHECKING:
    from ..peer.peer import Peer


class QueueManager(BaseQueueManager):

    @staticmethod
    def get_smallest_response_queue(peers: Iterable['Peer']) -> Optional['Peer']:
        s_peers = sorted(peers, key=lambda p: p.response_queue.qsize())
        if not s_peers:
            return
        duplicate_size = []
        min_size = s_peers[0].response_queue.qsize()
        for i in range(1, len(s_peers)):
            if s_peers[i].response_queue.qsize() == min_size:
                duplicate_size.append(s_peers[i])
            else:
                break
        if duplicate_size:
            return choice(duplicate_size)
        else:
            return s_peers[0]
