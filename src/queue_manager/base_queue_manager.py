from abc import ABCMeta, abstractmethod
from typing import Union, Optional, Tuple
from asyncio import Queue, PriorityQueue

from cid import CIDv0, CIDv1


class BaseQueueManager(metaclass=ABCMeta):

    @abstractmethod
    def create_tasks_queue(self, peer_cid: Union[CIDv0, CIDv1]) -> Optional[PriorityQueue]:
        pass

    @abstractmethod
    def get_smallest_queue(self) -> Optional[Tuple[Union[CIDv0, CIDv1], Queue]]:
        pass

    @abstractmethod
    def get_response_queue(self, peer_cid: Union[CIDv0, CIDv1]) -> Optional[Queue]:
        pass

    @abstractmethod
    def get_tasks_queue(self, peer_cid: Union[CIDv0, CIDv1]) -> Optional[Queue]:
        pass

    @abstractmethod
    def create_response_queue(self, peer_cid: Union[CIDv0, CIDv1]) -> Optional[Queue]:
        pass

    @abstractmethod
    def remove_response_queue(self, peer_cid: Union[CIDv0, CIDv1]) -> None:
        pass
