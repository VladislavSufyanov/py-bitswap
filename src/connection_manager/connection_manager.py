from typing import Tuple, NoReturn
import asyncio
from functools import partial

from peer import Peer, BasePeerManager
from session import BaseSessionManager
from .base_connection_manager import BaseConnectionManager
from message import MessageDecoder, MessageEncoder
from task import Task
from decision import BaseEngine


class ConnectionManager(BaseConnectionManager):

    def __init__(self, peer_manager: BasePeerManager, session_manager: BaseSessionManager,
                 engine: BaseEngine) -> None:
        self._peer_manager = peer_manager
        self._session_manager = session_manager
        self._engine = engine

    def run_message_handlers(self, peer: Peer) -> Tuple[asyncio.Task, asyncio.Task]:
        out_task_handler = Task.create_task(self._out_message_handler(peer),
                                            partial(self._out_message_handler, peer=peer))
        in_task_handler = Task.create_task(self._in_message_handler(peer),
                                           partial(self._in_message_handler_done, peer=peer,
                                                   out_task_handler=out_task_handler))
        return in_task_handler, out_task_handler

    async def _in_message_handler(self, peer: Peer) -> NoReturn:
        self._engine.create_tasks_queue(peer)
        async for message in peer:
            try:
                bit_msg = MessageDecoder.deserialize(message)
                self._engine.handle_bit_swap_message(peer, bit_msg)
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
            Task.create_task(self._peer_manager.remove_peer(peer.cid), Task.base_callback)
            self._engine.remove_tasks_queue(peer)

    async def _out_message_handler(self, peer: Peer) -> NoReturn:
        queue = self._engine.create_response_queue(peer)
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
            self._engine.remove_response_queue(peer)
