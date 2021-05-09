from typing import Dict, Union, Optional, Tuple
from asyncio import Queue, PriorityQueue
from random import choice

from cid import CIDv0, CIDv1

from .base_queue_manager import BaseQueueManager


class QueueManager(BaseQueueManager):

    def __init__(self) -> None:
        self._response_queues: Dict[Union[CIDv0, CIDv1], Queue] = {}
        self._tasks_queues: Dict[Union[CIDv0, CIDv1], PriorityQueue] = {}

    def create_tasks_queue(self, peer_cid: Union[CIDv0, CIDv1]) -> Optional[PriorityQueue]:
        if peer_cid not in self._tasks_queues:
            p_queue = PriorityQueue()
            self._tasks_queues[peer_cid] = p_queue
            return p_queue

    def remove_tasks_queue(self, peer_cid: Union[CIDv0, CIDv1]) -> None:
        if peer_cid in self._tasks_queues:
            del self._tasks_queues[peer_cid]

    def get_smallest_response_queue(self) -> Optional[Tuple[Union[CIDv0, CIDv1], Queue]]:
        if not self._response_queues:
            return
        s_queues = sorted(self._response_queues.items(), key=lambda t_q: t_q[1].qsize())
        duplicate_size = []
        min_size = s_queues[0][1].qsize()
        for i in range(1, len(s_queues)):
            if s_queues[i][1].qsize() == min_size:
                duplicate_size.append(s_queues[i])
            else:
                break
        if duplicate_size:
            return choice(duplicate_size)
        else:
            return s_queues[0]

    def get_response_queue(self, peer_cid: Union[CIDv0, CIDv1]) -> Optional[Queue]:
        return self._response_queues.get(peer_cid)

    def get_tasks_queue(self, peer_cid: Union[CIDv0, CIDv1]) -> Optional[PriorityQueue]:
        return self._tasks_queues.get(peer_cid)

    def create_response_queue(self, peer_cid: Union[CIDv0, CIDv1]) -> Optional[Queue]:
        if peer_cid not in self._response_queues:
            queue = Queue()
            self._response_queues[peer_cid] = queue
            return queue

    def remove_response_queue(self, peer_cid: Union[CIDv0, CIDv1]) -> None:
        if peer_cid in self._response_queues:
            del self._response_queues[peer_cid]