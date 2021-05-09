from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..peer.peer import Peer


@dataclass
class PeerScore:

    peer: 'Peer'
    score: int = 0

    def __hash__(self) -> int:
        return str(self.peer.cid).__hash__()

    def change_score(self, diff: int) -> int:
        self.score += diff
        return self.score
