from typing import Union, Dict, TYPE_CHECKING

from cid import CIDv0, CIDv1

from .proto_buff import ProtoBuff
from .message_entry import MessageEntry

if TYPE_CHECKING:
    from data_structure.block import Block


class BitswapMessage:

    def __init__(self, full: bool) -> None:
        self.full = full
        self.want_list: Dict[Union[CIDv0, CIDv1], MessageEntry] = {}
        self.payload: Dict[Union[CIDv0, CIDv1], 'Block'] = {}
        self.block_presences: Dict[Union[CIDv0, CIDv1], 'ProtoBuff.BlockPresenceType'] = {}

    def add_entry(self, cid: Union[CIDv0, CIDv1], priority: int, cancel: bool,
                  want_type: 'ProtoBuff.WantType', send_do_not_have: bool) -> None:
        entry = self.want_list.get(cid)
        if entry is not None and (entry.want_type == ProtoBuff.WantType.Block or
                                  want_type == ProtoBuff.WantType.Have):
            return
        if entry is not None:
            entry.priority = priority
            entry.cancel = cancel
            entry.want_type = want_type
            entry.send_do_not_have = send_do_not_have
        else:
            self.want_list[cid] = MessageEntry(cid, priority, cancel, want_type, send_do_not_have)

    def add_block(self, block: 'Block') -> None:
        self.payload[block.cid] = block

    def add_block_presence(self, cid: Union[CIDv0, CIDv1], presence_type: 'ProtoBuff.BlockPresenceType') -> None:
        self.block_presences[cid] = presence_type
