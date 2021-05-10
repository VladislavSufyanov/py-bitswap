from typing import Union
from dataclasses import dataclass

from cid import CIDv0, CIDv1


@dataclass
class Block:

    _cid: Union[CIDv0, CIDv1]
    _data: bytes

    def __len__(self) -> int:
        return len(self._data)

    @property
    def data(self):
        return self._data

    @property
    def cid(self) -> Union[CIDv0, CIDv1]:
        return self._cid
