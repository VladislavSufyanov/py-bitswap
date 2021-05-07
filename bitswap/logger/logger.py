from logging import getLogger, Logger, Formatter, Handler, StreamHandler
from typing import Optional
import os

import colorlog
from concurrent_log_handler import ConcurrentRotatingFileHandler


def _get_logger(logger_name: str, handler: Handler, log_level: int, formatter: Formatter) -> Logger:
    logger = getLogger(logger_name)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(log_level)
    return logger


def get_concurrent_logger(logger_name: str, log_path: str, log_level: int,
                          log_format: str = '%(asctime)s %(levelname)s %(name)s %(message)s',
                          max_bytes=512 * 1024, backup_count=5) -> Logger:
    if not os.path.exists(log_path):
        raise FileNotFoundError(f'log_path: {log_path}')
    return _get_logger(logger_name, ConcurrentRotatingFileHandler(log_path, 'a', max_bytes, backup_count),
                       log_level, Formatter(log_format))


def get_stream_logger(logger_name: str, log_level: int,
                      log_format: str = '%(asctime)s %(levelname)s %(name)s %(message)s') -> Logger:
    return _get_logger(logger_name, StreamHandler(), log_level, Formatter(log_format))


def get_stream_logger_colored(logger_name: str, log_level: int,
                              log_format: str = '%(log_color)s%(asctime)s %(levelname)s %(name)s %(message)s',
                              log_colors: Optional[dict] = None) -> Logger:
    if log_colors is None:
        log_colors = {
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    formatter = colorlog.ColoredFormatter(log_format, log_colors=log_colors, style='%')
    return _get_logger(logger_name, colorlog.StreamHandler(), log_level, formatter)
