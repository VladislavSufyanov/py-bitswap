from typing import Union, Iterable

from cid import CIDv0, CIDv1

from peer import Peer
from data_structure import Block
from message import BitswapMessage, MessageEncoder
from message import ProtoBuff


class Sender:

    @staticmethod
    async def send_cancel(block_cid: Union[CIDv0, CIDv1], peers: Iterable[Peer], priority=1) -> None:
        cancel_message = BitswapMessage(False)
        cancel_message.add_entry(block_cid, priority, True, ProtoBuff.WantType.Block, False)
        msg = MessageEncoder.serialize_1_1_0(cancel_message)
        for peer in peers:
            await peer.send(msg)

    @staticmethod
    async def send_presence(block_cid: Union[CIDv0, CIDv1], peers: Iterable[Peer],
                            presence_type: 'ProtoBuff.BlockPresenceType') -> None:
        presence_message = BitswapMessage(False)
        presence_message.add_block_presence(block_cid, presence_type)
        msg = MessageEncoder.serialize_1_1_0(presence_message)
        for peer in peers:
            await peer.send(msg)

    @staticmethod
    async def send_blocks(peers: Iterable[Peer], blocks: Iterable[Block]) -> None:
        bit_swap_message = BitswapMessage(False)
        for block in blocks:
            bit_swap_message.add_block(block)
        msg = MessageEncoder.serialize_1_1_0(bit_swap_message)
        for peer in peers:
            await peer.send(msg)
            for cid in bit_swap_message.payload.keys():
                peer.ledger.cancel_want(cid)
