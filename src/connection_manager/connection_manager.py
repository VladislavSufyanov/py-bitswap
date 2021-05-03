import asyncio
from functools import partial

from peer import Peer, BasePeerManager
from session import BaseSessionManager
from .base_connection_manager import BaseConnectionManager


class ConnectionManager(BaseConnectionManager):

    def __init__(self, peer_manager: BasePeerManager, session_manager: BaseSessionManager) -> None:
        self._peer_manager = peer_manager
        self._session_manager = session_manager

    def run_message_handler(self, peer: Peer) -> asyncio.Task:
        task = asyncio.create_task(self._message_handler(peer))
        task.add_done_callback(partial(self._message_handler_done, peer=peer))
        return task

    async def _message_handler(self, peer: Peer) -> None:
        async for message in peer:
            ...

    def _message_handler_done(self, task: asyncio.Task, peer: Peer) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            ...
        finally:
            for session in self._session_manager:
                session.remove_peer(peer.cid)
            self._peer_manager.remove_peer(peer.cid)
