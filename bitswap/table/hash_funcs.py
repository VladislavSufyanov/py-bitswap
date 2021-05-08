import hashlib


HASH_TABLE = {
    0x11: hashlib.sha1,
    0x12: hashlib.sha256,
    0x13: hashlib.sha512,
    0x14: hashlib.sha3_512,
    0x15: hashlib.sha3_384,
    0x16: hashlib.sha3_256,
    0x17: hashlib.sha3_224,
    0xd5: hashlib.md5
}
