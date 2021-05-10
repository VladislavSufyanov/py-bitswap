from typing import Union, Optional, Set, TYPE_CHECKING
import weakref
from asyncio import Event

from cid import CIDv0, CIDv1

if TYPE_CHECKING:
    from ..message.proto_buff import ProtoBuff
    from ..session.session import Session


class Entry:

    def __init__(self, cid: Union[CIDv0, CIDv1], priority: int, want_type: 'ProtoBuff.WantType'):
        self.cid = cid
        self.priority = priority
        self.want_type = want_type
        self._block: Optional[bytes] = None
        self.block_event = Event()
        self.sessions = weakref.WeakSet()

    @property
    def block(self) -> Optional[bytes]:
        return self._block

    @block.setter
    def block(self, data: bytes) -> None:
        if isinstance(data, bytes):
            self._block = data
            self.block_event.set()

    @block.deleter
    def block(self) -> None:
        self._block = None
        self.block_event.clear()

    def add_session(self, session: 'Session') -> None:
        self.sessions.add(session)
