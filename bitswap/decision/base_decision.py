from abc import ABCMeta, abstractmethod
from typing import Any


class BaseDecision(metaclass=ABCMeta):

    @abstractmethod
    def run(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def __enter__(self) -> 'BaseDecision':
        pass

    @abstractmethod
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass
