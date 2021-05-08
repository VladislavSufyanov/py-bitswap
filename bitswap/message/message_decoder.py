from typing import List
from io import BytesIO

from cid import make_cid
import multihash
from multicodec.constants import CODE_TABLE
from varint import decode_stream

from .proto_buff import ProtoBuff
from .bitswap_message import BitswapMessage
from ..data_structure.block import Block
from ..table import HASH_TABLE


class MessageDecoder:

    @staticmethod
    def _decode_var_int(buffer: bytes) -> List[int]:
        bytes_stream = BytesIO(buffer)
        res = []
        while bytes_stream.tell() < len(buffer):
            res.append(decode_stream(bytes_stream))
        return res

    @staticmethod
    def deserialize(raw_message: bytes) -> BitswapMessage:
        decoded_message = ProtoBuff.Message()
        decoded_message.ParseFromString(raw_message)
        full = decoded_message.wantlist and decoded_message.wantlist.full
        bitswap_message = BitswapMessage(full)
        if decoded_message.wantlist:
            for entry in decoded_message.wantlist.entries:
                cid = make_cid(entry.block)
                bitswap_message.add_entry(cid, entry.priority, entry.cancel, entry.wantType, entry.sendDontHave)
        if decoded_message.blocks:
            hash_func = HASH_TABLE[multihash.coerce_code('sha2-256')]
            for block in decoded_message.blocks:
                mh = multihash.encode(hash_func(block).digest(), 'sha2-256')
                bitswap_message.add_block(Block(make_cid(multihash.to_b58_string(mh)), block))
        for payload in decoded_message.payload:
            cid_version, multi_codec, hash_func_prefix, _ = MessageDecoder._decode_var_int(payload.prefix)
            hash_func = HASH_TABLE[multihash.coerce_code(hash_func_prefix)]
            multi_hash = multihash.encode(hash_func(payload.data).digest(), hash_func_prefix)
            cid = make_cid(cid_version, CODE_TABLE[multi_codec], multi_hash)
            bitswap_message.add_block(Block(cid, payload.data))
        for block_presence in decoded_message.blockPresences:
            bitswap_message.add_block_presence(make_cid(block_presence.cid), block_presence.type)
        return bitswap_message
