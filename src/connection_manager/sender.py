from typing import Union, Iterable, Optional, TYPE_CHECKING
from logging import Logger

from cid import CIDv0, CIDv1

from message.bitswap_message import BitswapMessage
from message.message_encoder import MessageEncoder
from message.proto_buff import ProtoBuff

if TYPE_CHECKING:
    from peer.peer import Peer
    from data_structure.block import Block
    from wantlist.entry import Entry


class Sender:

    @staticmethod
    async def _send(msg: bytes, peers: Iterable['Peer'], logger: Optional[Logger] = None):
        for peer in peers:
            try:
                await peer.send(msg)
            except Exception as e:
                if logger is not None:
                    ...  # log

    @staticmethod
    async def send_entries(entries: Iterable['Entry'], peers: Iterable['Peer'],
                           want_type: 'ProtoBuff.WantType', full: bool = False) -> None:
        message = BitswapMessage(full)
        for entry in entries:
            message.add_entry(entry.cid, entry.priority, False, want_type, True)
        msg = MessageEncoder.serialize_1_1_0(message)
        await Sender._send(msg, peers)

    @staticmethod
    async def send_cancel(block_cid: Union[CIDv0, CIDv1], peers: Iterable['Peer'], priority=1) -> None:
        cancel_message = BitswapMessage(False)
        cancel_message.add_entry(block_cid, priority, True, ProtoBuff.WantType.Block, False)
        msg = MessageEncoder.serialize_1_1_0(cancel_message)
        await Sender._send(msg, peers)

    @staticmethod
    async def send_presence(block_cid: Union[CIDv0, CIDv1], peers: Iterable['Peer'],
                            presence_type: 'ProtoBuff.BlockPresenceType') -> None:
        presence_message = BitswapMessage(False)
        presence_message.add_block_presence(block_cid, presence_type)
        msg = MessageEncoder.serialize_1_1_0(presence_message)
        await Sender._send(msg, peers)

    @staticmethod
    async def send_blocks(peers: Iterable['Peer'], blocks: Iterable['Block'],
                          logger: Optional[Logger] = None) -> None:
        bit_swap_message = BitswapMessage(False)
        for block in blocks:
            bit_swap_message.add_block(block)
        msg = MessageEncoder.serialize_1_1_0(bit_swap_message)
        for peer in peers:
            try:
                await peer.send(msg)
            except Exception as e:
                if logger is not None:
                    ...  # log
            for cid in bit_swap_message.payload.keys():
                peer.ledger.cancel_want(cid)
