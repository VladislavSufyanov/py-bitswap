from typing import Union, Optional, List
from dataclasses import dataclass

from cid import CIDv0, CIDv1

from message import ProtoBuff
from session import Session


@dataclass
class Entry:

    cid: Union[CIDv0, CIDv1]
    priority: int
    want_type: ProtoBuff.WantType
    block: Optional[bytes] = None
    sessions: Optional[List[Session]] = None
