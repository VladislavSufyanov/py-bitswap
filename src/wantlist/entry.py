from typing import Union
from dataclasses import dataclass

from cid import CIDv0, CIDv1

from ..message import ProtoBuff


@dataclass
class Entry:

    cid: Union[CIDv0, CIDv1]
    priority: int
    want_type: ProtoBuff.WantType
