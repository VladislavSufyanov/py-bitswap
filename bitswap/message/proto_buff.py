from .pb.message_pb2 import Message


class ProtoBuff:
    Message = Message
    WantList = Message.Wantlist
    WantType = Message.Wantlist.WantType
    BlockPresenceType = Message.BlockPresenceType
