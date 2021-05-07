from typing import Tuple, NoReturn, Optional, TYPE_CHECKING
import asyncio
from functools import partial
from logging import Logger, INFO

from .base_connection_manager import BaseConnectionManager
from ..message.message_decoder import MessageDecoder
from ..message.message_encoder import MessageEncoder
from ..task.task import Task
from ..logger import get_stream_logger_colored, get_concurrent_logger

if TYPE_CHECKING:
    from ..peer.peer import Peer
    from ..peer.base_peer_manager import BasePeerManager
    from ..session.base_session_manager import BaseSessionManager
    from ..decision.base_engine import BaseEngine
    from ..network.base_network import BaseNetwork


class ConnectionManager(BaseConnectionManager):

    def __init__(self, session_manager: 'BaseSessionManager', engine: 'BaseEngine',
                 log_level: int = INFO, log_path: Optional[str] = None) -> None:
        if log_path is None:
            self._logger = get_stream_logger_colored(__name__, log_level)
        else:
            self._logger = get_concurrent_logger(__name__, log_path, log_level)
        self._session_manager = session_manager
        self._engine = engine
        self._new_connections_task: Optional[asyncio.Task] = None

    def run_handle_conn(self, network: 'BaseNetwork', peer_manager: 'BasePeerManager') -> None:
        self._new_connections_task = Task.create_task(ConnectionManager._handle_new_connections(network, peer_manager,
                                                                                                self._logger),
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
    async def _handle_new_connections(network: 'BaseNetwork', peer_manager: 'BasePeerManager',
                                      logger: Optional[Logger] = None) -> NoReturn:
        logger.debug('Start handle new connections')
        async for peer_cid, network_peer in network.new_connections():
            if logger is not None:
                logger.debug(f'New connection request, peer_cid: {peer_cid}')
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
                self._logger.exception(f'Handle message exception, peer_cid: {peer.cid}, e: {e}')

    def _in_message_handler_done(self, task: asyncio.Task, peer: 'Peer', peer_manager: 'BasePeerManager',
                                 out_task_handler: asyncio.Task) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            self._logger.debug(f'Cancel _in_message_handler, peer_cid: {peer.cid}')
        except Exception as e:
            self._logger.debug(f'Exception _in_message_handler_done, peer_cid: {peer.cid}, e: {e}')
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
                self._logger.exception(f'Send message exception, peer_cid: {peer.cid}, e: {e}')

    async def _out_message_handler_done(self, task: asyncio.Task, peer: 'Peer') -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            self._logger.debug(f'Cancel _out_message_handler, peer_cid: {peer.cid}')
        except Exception as e:
            self._logger.debug(f'Exception _out_message_handler_done, peer_cid: {peer.cid}, e: {e}')
        finally:
            self._engine.remove_response_queue(peer)
