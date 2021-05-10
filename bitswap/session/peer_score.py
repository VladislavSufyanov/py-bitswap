from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..peer.peer import Peer


@dataclass
class PeerScore:

    peer: 'Peer'
    _score: float = 0

    def __hash__(self) -> int:
        return str(self.peer.cid).__hash__()

    @property
    def score(self):
        return self._score

    def change_score(self, new: float, alpha: float = 0.5) -> float:
        self._score = self._ewma(self._score, new, alpha)
        return self._score

    @staticmethod
    def _ewma(old: float, new: float, alpha: float) -> float:
        return new * alpha + (1 - alpha) * old
