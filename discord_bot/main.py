"""Ponto de entrada para execução do bot."""

from __future__ import annotations

import logging

from discord_bot.bot import DiscordBot
from discord_bot.config import ConfigurationError, Settings
from discord_bot.logging_config import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Valida a configuração e inicia a conexão com o Discord."""
    configure_logging()
    try:
        settings = Settings.from_environment()
    except ConfigurationError as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc

    bot = DiscordBot(settings)
    bot.run(settings.discord_token)