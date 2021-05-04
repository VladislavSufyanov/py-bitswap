from typing import Union, Dict, Optional

from cid import CIDv0, CIDv1

from .proto_buff import ProtoBuff
from .message_entry import MessageEntry
from data_structure import Block


class BitswapMessage:

    def __init__(self, peer_cid: Union[CIDv0, CIDv1], full: bool,
                 block_presence_cid: Optional[Union[CIDv0, CIDv1]] = None,
                 block_presence_type: Optional[ProtoBuff.BlockPresenceType] = None) -> None:
        self.peer_cid = peer_cid
        self.full = full
        self.want_list: Dict[Union[CIDv0, CIDv1], MessageEntry] = {}
        self.payload: Dict[Union[CIDv0, CIDv1], Block] = {}
        self.block_presence_cid = block_presence_cid
        self.block_presence_type = block_presence_type

    def add_entry(self, cid: Union[CIDv0, CIDv1], priority: int, cancel: bool,
                  want_type: ProtoBuff.WantType, send_do_not_have: bool) -> None:
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

    def add_block(self, block: Block):
        self.payload[block.cid] = block
