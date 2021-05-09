from typing import Union, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass, field
import weakref
from asyncio import Event

from cid import CIDv0, CIDv1

if TYPE_CHECKING:
    from ..message.proto_buff import ProtoBuff
    from ..session.session import Session


@dataclass
class Entry:

    cid: Union[CIDv0, CIDv1]
    priority: int
    want_type: 'ProtoBuff.WantType'
    _block: Optional[bytes] = field(init=False, default=None)
    block_event: Event = field(init=False, default=Event())
    sessions: Set['Session'] = field(init=False, default=weakref.WeakSet())

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
