from typing import Union, Optional

from cid import CIDv0, CIDv1

from wantlist import WantList, Entry
from message import ProtoBuff


class Ledger:

    def __init__(self, want_list: WantList) -> None:
        self._want_list = want_list

    def __contains__(self, cid: Union[CIDv0, CIDv1]) -> bool:
        return cid in self._want_list

    def wants(self, cid: Union[CIDv0, CIDv1], priority: int,
              want_type: 'ProtoBuff.WantType') -> None:
        self._want_list.add(cid, priority, want_type)

    def cancel_want(self, cid: Union[CIDv0, CIDv1]) -> bool:
        return self._want_list.remove(cid)

    def get_entry(self, cid: Union[CIDv0, CIDv1]) -> Optional[Entry]:
        try:
            entry = self._want_list[cid]
        except KeyError:
            return
        else:
            return entry
