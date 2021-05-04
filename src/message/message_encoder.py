from typing import Union

from cid import CIDv0, CIDv1
from multicodec import get_prefix
from varint import encode
from multihash import decode

from .proto_buff import ProtoBuff
from .bitswap_message import BitswapMessage


class MessageEncoder:

    @staticmethod
    def _cid_prefix(cid: Union[CIDv0, CIDv1]):
        version_bytes = encode(cid.version)
        codec_bytes = get_prefix(cid.codec)
        hash_alg_bytes = encode(decode(cid.multihash).func.value)
        hash_length = encode(cid.multihash[1])
        return version_bytes + codec_bytes + hash_alg_bytes + hash_length

    @staticmethod
    def _serialize_entries(bitswap_message: BitswapMessage) -> 'ProtoBuff.Message':
        message = ProtoBuff.Message()
        wantlist = message.wantlist
        entries = wantlist.entries
        wantlist.full = bitswap_message.full
        block_presences = message.blockPresences
        for entry in bitswap_message.want_list.values():
            msg_entry = entries.add()
            msg_entry.block, msg_entry.priority, msg_entry.cancel, \
                msg_entry.wantType, msg_entry.sendDontHave = entry.dump_fields()
        for cid, presence_type in bitswap_message.block_presences.items():
            msg_presence = block_presences.add()
            msg_presence.cid = cid.encode()
            msg_presence.type = presence_type
        return message

    @staticmethod
    def serialize_1_0_0(bitswap_message: BitswapMessage) -> bytes:
        message = MessageEncoder._serialize_entries(bitswap_message)
        blocks = message.blocks
        for block in bitswap_message.payload.values():
            msg_block = blocks.add()
            msg_block.data = block.data
        return message.SerializeToString()

    @staticmethod
    def serialize_1_1_0(bitswap_message: BitswapMessage) -> bytes:
        message = MessageEncoder._serialize_entries(bitswap_message)
        payload = message.payload
        for block in bitswap_message.payload.values():
            msg_payload = payload.add()
            msg_payload.prefix = MessageEncoder._cid_prefix(block.cid)
            msg_payload.data = block.data
        return message.SerializeToString()
