from typing import Awaitable, Callable, Optional
import asyncio
from logging import Logger


class Task:

    @staticmethod
    def create_task(func: Awaitable, callback: Callable) -> asyncio.Task:
        task = asyncio.create_task(func)
        task.add_done_callback(callback)
        return task

    @staticmethod
    def base_callback(task: asyncio.Task, logger: Optional[Logger] = None) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if logger is not None:
                ...  # log
