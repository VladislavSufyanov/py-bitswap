from logging import getLogger, Logger, Formatter

from concurrent_log_handler import ConcurrentRotatingFileHandler


def get_logger(logger_name: str, log_path: str, log_level: int,
               log_format: str = '%(asctime)s %(levelname)s %(message)s',
               max_bytes=512*1024, backup_count=5) -> Logger:
    log = getLogger(logger_name)
    rotate_handler = ConcurrentRotatingFileHandler(log_path, 'a', max_bytes, backup_count)
    formatter = Formatter(log_format)
    rotate_handler.setFormatter(formatter)
    log.addHandler(rotate_handler)
    log.setLevel(log_level)
    return log
