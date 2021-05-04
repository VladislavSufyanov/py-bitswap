from typing import List, Union
from io import BytesIO

from cid import make_cid
import multihash
from multicodec.constants import CODE_TABLE
from varint import decode_stream
from cid import CIDv0, CIDv1

from . import ProtoBuff
from .bitswap_message import BitswapMessage
from data_structure import Block


class MessageDecoder:

    @staticmethod
    def _decode_var_int(buffer: bytes) -> List[int]:
        bytes_stream = BytesIO(buffer)
        res = []
        while bytes_stream.tell() < len(buffer):
            res.append(decode_stream(bytes_stream))
        return res

    @staticmethod
    def deserialize(peer_cid: Union[CIDv0, CIDv1], raw_message: bytes) -> BitswapMessage:
        decoded_message = ProtoBuff.Message.ParseFromString(raw_message)
        full = decoded_message.wantlist and decoded_message.wantlist.full
        block_presence_cid, block_presence_type = None, None
        if decoded_message.blockPresences.cid:
            block_presence_cid = make_cid(decoded_message.blockPresences.cid)
        if decoded_message.blockPresences.type:
            block_presence_type = decoded_message.blockPresences.type
        bitswap_message = BitswapMessage(peer_cid, full, block_presence_cid, block_presence_type)
        if decoded_message.wantlist:
            for entry in decoded_message.wantlist.entries:
                cid = make_cid(entry.block)
                bitswap_message.add_entry(cid, entry.priority, entry.cancel, entry.wantType, entry.sendDontHave)
        if len(decoded_message.blocks) > 0:
            for block in decoded_message.blocks:
                bitswap_message.add_block(Block(make_cid(multihash.digest(block, 'sha2-256')), block))
        if len(decoded_message.payload) > 0:
            for payload in decoded_message.payload:
                cid_version, multi_codec, hash_func, _ = MessageDecoder._decode_var_int(payload.prefix)
                multi_hash = multihash.digest(payload.data, hash_func).encode()
                cid = make_cid(cid_version, CODE_TABLE[multi_codec], multi_hash)
                bitswap_message.add_block(Block(cid, payload.data))
        return bitswap_message
