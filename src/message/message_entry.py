from typing import Union, Tuple

from cid import CIDv0, CIDv1

from wantlist import Entry
from .proto_buff import ProtoBuff


class MessageEntry:

    def __init__(self, cid: Union[CIDv0, CIDv1], priority: int, cancel: bool,
                 want_type: ProtoBuff.WantType, send_do_not_have: bool) -> None:
        self.entry = Entry(cid, priority, want_type)
        self.cancel = cancel
        self.send_do_not_have = send_do_not_have

    def dump_fields(self) -> Tuple[bytes, int, bool, ProtoBuff.WantType, bool]:
        return self.entry.cid.buffer, self.priority, self.cancel, self.entry.want_type, self.send_do_not_have

    @property
    def cid(self) -> Union[CIDv0, CIDv1]:
        return self.entry.cid

    @property
    def priority(self) -> int:
        return self.entry.priority

    @priority.setter
    def priority(self, priority: int) -> None:
        self.entry.priority = priority

    @property
    def want_type(self) -> ProtoBuff.WantType:
        return self.entry.want_type

    @want_type.setter
    def want_type(self, want_type: ProtoBuff.WantType) -> None:
        self.entry.want_type = want_type
