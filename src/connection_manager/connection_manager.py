from typing import Callable, Awaitable, Tuple
import asyncio
from functools import partial

from peer import Peer, BasePeerManager
from session import BaseSessionManager
from .base_connection_manager import BaseConnectionManager
from message import MessageDecoder, MessageEncoder
from queue_manager import BaseQueueManager


class ConnectionManager(BaseConnectionManager):

    def __init__(self, peer_manager: BasePeerManager, session_manager: BaseSessionManager,
                 queue_manager: BaseQueueManager) -> None:
        self._peer_manager = peer_manager
        self._session_manager = session_manager
        self._queue_manager = queue_manager

    def run_message_handlers(self, peer: Peer) -> Tuple[asyncio.Task, asyncio.Task]:
        out_task_handler = self._create_task(self._out_message_handler(peer),
                                             partial(self._out_message_handler, peer=peer))
        in_task_handler = self._create_task(self._in_message_handler(peer),
                                            partial(self._in_message_handler_done, peer=peer,
                                                    out_task_handler=out_task_handler))
        return in_task_handler, out_task_handler

    @staticmethod
    def _create_task(func: Awaitable, callback: Callable) -> asyncio.Task:
        task = asyncio.create_task(func)
        task.add_done_callback(callback)
        return task

    async def _in_message_handler(self, peer: Peer) -> None:
        task_queue = self._queue_manager.create_tasks_queue(peer.cid)
        if task_queue is None:
            task_queue = self._queue_manager.get_tasks_queue(peer.cid)
        async for message in peer:
            try:
                bit_msg = MessageDecoder.deserialize(peer.cid, message)
            except Exception as e:
                ...

    def _in_message_handler_done(self, task: asyncio.Task, peer: Peer, out_task_handler: asyncio.Task) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            ...
        finally:
            out_task_handler.cancel()
            for session in self._session_manager:
                session.remove_peer(peer.cid)
            self._peer_manager.remove_peer(peer.cid)

    async def _out_message_handler(self, peer: Peer) -> None:
        queue = self._queue_manager.create_response_queue(peer.cid)
        if queue is None:
            queue = self._queue_manager.get_response_queue(peer.cid)
        while True:
            bit_message = await queue.get()
            try:
                message = MessageEncoder.serialize_1_1_0(bit_message)
                await peer.send(message)
            except Exception as e:
                ...

    async def _out_message_handler_done(self, task: asyncio.Task, peer: Peer) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            ...
        finally:
            self._queue_manager.remove_response_queue(peer.cid)
