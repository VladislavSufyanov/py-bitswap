from typing import Dict, Union, List, Iterator
from operator import attrgetter

from cid import CIDv0, CIDv1

from .entry import Entry
from ..message import ProtoBuff


class WantList:

    def __init__(self) -> None:
        self._entries: Dict[Union[CIDv0, CIDv1], Entry] = {}

    def __contains__(self, cid: Union[CIDv0, CIDv1]) -> bool:
        return cid in self._entries

    def __getitem__(self, cid: Union[CIDv0, CIDv1]) -> Entry:
        return self._entries[cid]

    def __iter__(self) -> Iterator[Entry]:
        return self._entries.values().__iter__()

    def add(self, cid: Union[CIDv0, CIDv1], priority: int,
            want_type: ProtoBuff.WantType) -> bool:
        entry = self._entries.get(cid)
        if entry is not None and (entry.want_type == ProtoBuff.WantType.Value('Block') or
                                  want_type == ProtoBuff.WantType.Value('Have')):
            return False
        self._entries[cid] = Entry(cid, priority, want_type)
        return True

    def remove(self, cid: Union[CIDv0, CIDv1]) -> bool:
        if cid in self._entries:
            del self._entries[cid]
            return True
        else:
            return False

    def remove_type(self, cid: Union[CIDv0, CIDv1], want_type: ProtoBuff.WantType) -> bool:
        entry = self._entries.get(cid)
        if entry is None or (entry.want_type == ProtoBuff.WantType.Value('Block') and
                             want_type == ProtoBuff.WantType.Value('Have')):
            return False
        del self._entries[cid]
        return True

    def entries(self) -> List[Entry]:
        return list(self._entries.values())

    def absorb(self, other_want_list: 'WantList') -> None:
        for entry in other_want_list:
            self.add(entry.cid, entry.priority, entry.want_type)

    @staticmethod
    def entries_sort_by_priority(entries: List[Entry]) -> None:
        entries.sort(key=attrgetter('priority'))
