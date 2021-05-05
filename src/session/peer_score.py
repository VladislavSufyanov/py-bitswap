from dataclasses import dataclass

from peer import Peer


@dataclass
class PeerScore:

    peer: Peer
    score: int = 0

    def change_score(self, diff: int) -> int:
        self.score += diff
        return self.score
