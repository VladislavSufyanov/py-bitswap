from typing import Tuple, NoReturn, Optional, TYPE_CHECKING
import asyncio
from functools import partial

from .base_connection_manager import BaseConnectionManager
from message.message_decoder import MessageDecoder
from message.message_encoder import MessageEncoder
from task.task import Task

if TYPE_CHECKING:
    from peer.peer import Peer
    from peer.base_peer_manager import BasePeerManager
    from session.base_session_manager import BaseSessionManager
    from decision.base_engine import BaseEngine
    from network.base_network import BaseNetwork


class ConnectionManager(BaseConnectionManager):

    def __init__(self, session_manager: 'BaseSessionManager', engine: 'BaseEngine') -> None:
        self._session_manager = session_manager
        self._engine = engine
        self._new_connections_task: Optional[asyncio.Task] = None

    def run_handle_conn(self, network: 'BaseNetwork', peer_manager: 'BasePeerManager') -> None:
        self._new_connections_task = Task.create_task(ConnectionManager._handle_new_connections(network, peer_manager),
                                                      Task.base_callback)

    def stop_handle_conn(self) -> None:
        self._new_connections_task.cancel()
        self._new_connections_task = None

    def run_message_handlers(self, peer: 'Peer', peer_manager: 'BasePeerManager') -> Tuple[asyncio.Task, asyncio.Task]:
        out_task_handler = Task.create_task(self._out_message_handler(peer),
                                            partial(self._out_message_handler, peer=peer))
        in_task_handler = Task.create_task(self._in_message_handler(peer, peer_manager),
                                           partial(self._in_message_handler_done, peer=peer,
                                                   peer_manager=peer_manager, out_task_handler=out_task_handler))
        return in_task_handler, out_task_handler

    @staticmethod
    async def _handle_new_connections(network: 'BaseNetwork', peer_manager: 'BasePeerManager') -> NoReturn:
        async for peer_cid, network_peer in network.new_connections():
            await peer_manager.connect(peer_cid, network_peer)

    async def _in_message_handler(self, peer: 'Peer', peer_manager: 'BasePeerManager') -> NoReturn:
        self._engine.create_tasks_queue(peer)
        async for message in peer:
            try:
                bit_msg = MessageDecoder.deserialize(message)
                self._engine.handle_bit_swap_message(peer, bit_msg, peer_manager)
            except asyncio.exceptions.CancelledError:
                raise
            except Exception as e:
                ...  # log

    def _in_message_handler_done(self, task: asyncio.Task, peer: 'Peer', peer_manager: 'BasePeerManager',
                                 out_task_handler: asyncio.Task) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            ...  # log
        finally:
            out_task_handler.cancel()
            for session in self._session_manager:
                session.remove_peer(peer.cid)
            Task.create_task(peer_manager.remove_peer(peer.cid), Task.base_callback)
            self._engine.remove_tasks_queue(peer)

    async def _out_message_handler(self, peer: 'Peer') -> NoReturn:
        queue = self._engine.create_response_queue(peer)
        while True:
            bit_message = await queue.get()
            try:
                message = MessageEncoder.serialize_1_1_0(bit_message)
                await peer.send(message)
            except asyncio.exceptions.CancelledError:
                raise
            except Exception as e:
                ...  # log

    async def _out_message_handler_done(self, task: asyncio.Task, peer: 'Peer') -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            ...  # log
        finally:
            self._engine.remove_response_queue(peer)
