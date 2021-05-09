from typing import Union, Iterable, TYPE_CHECKING

from cid import CIDv0, CIDv1

from ..message.bitswap_message import BitswapMessage
from ..message.proto_buff import ProtoBuff

if TYPE_CHECKING:
    from ..data_structure.block import Block
    from ..wantlist.entry import Entry
    from ..peer.peer import Peer


class Sender:

    @staticmethod
    async def _send(b_message: BitswapMessage, peers: Iterable['Peer']) -> None:
        for peer in peers:
            await peer.response_queue.put(b_message)
            for cid in b_message.payload.keys():
                peer.ledger.cancel_want(cid)

    @staticmethod
    async def send_entries(entries: Iterable['Entry'], peers: Iterable['Peer'],
                           want_type: 'ProtoBuff.WantType', full: bool = False) -> None:
        entries_message = BitswapMessage(full)
        for entry in entries:
            entries_message.add_entry(entry.cid, entry.priority, False, want_type, True)
        await Sender._send(entries_message, peers)

    @staticmethod
    async def send_cancel(block_cid: Union[CIDv0, CIDv1], peers: Iterable['Peer'], priority=1) -> None:
        cancel_message = BitswapMessage(False)
        cancel_message.add_entry(block_cid, priority, True, ProtoBuff.WantType.Block, False)
        await Sender._send(cancel_message, peers)

    @staticmethod
    async def send_presence(block_cid: Union[CIDv0, CIDv1], peers: Iterable['Peer'],
                            presence_type: 'ProtoBuff.BlockPresenceType') -> None:
        presence_message = BitswapMessage(False)
        presence_message.add_block_presence(block_cid, presence_type)
        await Sender._send(presence_message, peers)

    @staticmethod
    async def send_blocks(peers: Iterable['Peer'], blocks: Iterable['Block']) -> None:
        blocks_message = BitswapMessage(False)
        for block in blocks:
            blocks_message.add_block(block)
        await Sender._send(blocks_message, peers)
