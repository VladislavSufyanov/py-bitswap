from typing import Union, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass
import weakref

from cid import CIDv0, CIDv1

if TYPE_CHECKING:
    from message.proto_buff import ProtoBuff
    from session.session import Session


@dataclass
class Entry:

    cid: Union[CIDv0, CIDv1]
    priority: int
    want_type: 'ProtoBuff.WantType'
    block: Optional[bytes] = None
    sessions: Set['Session'] = weakref.WeakSet()

    def add_session(self, session: 'Session') -> None:
        self.sessions.add(session)
