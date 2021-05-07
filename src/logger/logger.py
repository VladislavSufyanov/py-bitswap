from logging import getLogger, Logger, Formatter, Handler, StreamHandler

from concurrent_log_handler import ConcurrentRotatingFileHandler


def _get_logger(logger_name: str, handler: Handler, log_level: int, log_format: str) -> Logger:
    logger = getLogger(logger_name)
    formatter = Formatter(log_format)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(log_level)
    return logger


def get_concurrent_logger(logger_name: str, log_path: str, log_level: int,
                          log_format: str = '%(asctime)s %(levelname)s %(name)s %(message)s',
                          max_bytes=512 * 1024, backup_count=5) -> Logger:
    return _get_logger(logger_name, ConcurrentRotatingFileHandler(log_path, 'a', max_bytes, backup_count),
                       log_level, log_format)


def get_stream_logger(logger_name: str, log_level: int,
                      log_format: str = '%(asctime)s %(levelname)s %(name)s %(message)s') -> Logger:
    return _get_logger(logger_name, StreamHandler(), log_level, log_format)
