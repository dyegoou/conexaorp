"""Configuração centralizada de logs do bot."""

from __future__ import annotations

import logging
import sys


def configure_logging() -> None:
    """Configura logs legíveis no console sem expor configurações sensíveis."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )