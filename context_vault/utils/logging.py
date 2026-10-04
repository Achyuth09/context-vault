"""Simple package logger."""

from __future__ import annotations

import logging

from context_vault import config


def get_logger(name: str = "context_vault") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, str(config.LOG_LEVEL).upper(), logging.INFO))
    return logger
