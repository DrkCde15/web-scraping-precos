"""Configuracao centralizada de logging."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configura o logging para o projeto.

    Args:
        level: Nivel de logging (default: INFO)
    """
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers[0] = handler
