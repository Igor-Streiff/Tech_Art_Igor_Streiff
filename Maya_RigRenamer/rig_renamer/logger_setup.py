"""Configuración de logging para el renamer."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


def setup_logger(log_dir: Path, verbose: bool = False) -> logging.Logger:
    """Crea logger con salida a consola y archivo."""
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"rig_renamer_{timestamp}.log"

    logger = logging.getLogger("rig_renamer")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("Log file: %s", log_file)
    return logger
