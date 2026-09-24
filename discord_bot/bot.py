"""Classe principal do bot e registro automático dos cogs."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from discord_bot.config import Settings
from discord_bot.cogs.general import GeneralCog
from discord_bot.cogs.owner import OwnerCog
from discord_bot.cogs.whitelist import (
    WhitelistCog,
    WhitelistPanelView,
    WhitelistReviewView,
)
from discord_bot.restart_state import (
    clear_pending_restart,
    load_pending_restart,
)

logger = logging.getLogger(__name__)

SYNC_COMPLETE_MESSAGE = """[DEV OPS / SYNC COMPLETE]
The bot has been synchronized successfully.

Process replacement: COMPLETE
Discord gateway: RE-ESTABLISHED
Guild command sync: COMPLETE
Global command registry: PRUNED
Application command cache: REFRESHED
Runtime state: OPERATIONAL
Synchronization handshake: COMPLETE"""


class DiscordBot(commands.Bot):
    """Bot configurado para trabalhar com slash commands."""

    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(
            command_prefix="$",
            intents=intents,
            help_command=None,
        )
        self.settings = settings
        self._guild_commands_synced = False
        self._registered_commands: tuple[discord.app_commands.Command, ...] = ()

    async def setup_hook(self) -> None:
        """Carrega os módulos e sincroniza os slash commands automaticamente."""
        await self.add_cog(GeneralCog(self))
        await self.add_cog(OwnerCog(self))
        whitelist_cog = WhitelistCog(self)
        await self.add_cog(whitelist_cog)
        self.add_view(WhitelistPanelView(whitelist_cog))
        self.add_view(WhitelistReviewView(whitelist_cog))
        self._registered_commands = tuple(self.tree.get_commands())

    async def on_ready(self) -> None:
        """Registra no console quando a conexão com o Discord estiver pronta."""
        if not self._guild_commands_synced:
            for guild in self.guilds:
                synced_commands = await self.sync_guild_commands(guild)
                logger.info(
                    "Slash commands sincronizados no servidor %s: %s",
                    guild.name,
                    len(synced_commands),
                )
            await self.clear_global_commands()
            self._guild_commands_synced = True

        if self.user is None:
            logger.info("Bot conectado ao Discord.")
        else:
            logger.info("Bot online como %s (ID: %s)", self.user, self.user.id)

        await self._complete_pending_sync_notice()

    async def _complete_pending_sync_notice(self) -> None:
        """Atualiza a mensagem técnica quando a sincronização foi concluída."""
        pending_restart = load_pending_restart()
        if pending_restart is None:
            return

        try:
            channel = self.get_channel(pending_restart["channel_id"])
            if channel is None:
                channel = await self.fetch_channel(pending_restart["channel_id"])
            if not hasattr(channel, "fetch_message"):
                logger.warning("Canal do aviso de reinício não pode buscar mensagens.")
                return

            message = await channel.fetch_message(pending_restart["message_id"])
            await message.edit(content=SYNC_COMPLETE_MESSAGE)
        except (discord.Forbidden, discord.HTTPException, discord.NotFound):
            logger.exception("Não foi possível concluir o aviso de reinício.")
        finally:
            clear_pending_restart()

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Sincroniza comandos imediatamente ao entrar em um novo servidor."""
        synced_commands = await self.sync_guild_commands(guild)
        logger.info(
            "Servidor adicionado: %s; slash commands sincronizados: %s",
            guild.name,
            len(synced_commands),
        )

    async def sync_guild_commands(
        self,
        guild: discord.Guild,
    ) -> list[discord.app_commands.Command]:
        """Copia os comandos globais para um servidor sem esperar propagação."""
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        return await self.tree.sync(guild=guild)

    async def clear_global_commands(self) -> None:
        """Remove versões globais antigas que causavam comandos duplicados."""
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        for command in self._registered_commands:
            self.tree.add_command(command)
        logger.info("Comandos globais antigos removidos; usando apenas versões por servidor.")