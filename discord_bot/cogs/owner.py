"""Comandos prefixados exclusivos do proprietário do bot."""

from __future__ import annotations

import asyncio
import os
import sys

import discord
from discord.ext import commands

from discord_bot.checks import is_configured_owner
from discord_bot.restart_state import save_pending_restart

SYNCING_MESSAGE = """[DEV OPS / SYNC]
Synchronization sequence initiated.

Reinitializing.....
Replacing the current Python process.
Rebuilding the Discord gateway session.
Refreshing the guild command registry.
Pruning stale global application commands.

Stand by. Do not issue duplicate synchronization commands."""

class OwnerCog(commands.Cog):
    """Comandos operacionais que não devem ficar disponíveis ao público."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="sync")
    @commands.guild_only()
    @is_configured_owner()
    async def sync(self, context: commands.Context[commands.Bot]) -> None:
        """Sincroniza os comandos após reiniciar completamente o processo."""
        notice = await context.send(SYNCING_MESSAGE)
        save_pending_restart(context.channel.id, notice.id)
        await asyncio.sleep(1)
        os.execv(sys.executable, [sys.executable, "-m", "discord_bot"])

    @commands.command(name="kick")
    @commands.guild_only()
    @is_configured_owner()
    async def kick_member(
        self,
        context: commands.Context[commands.Bot],
        member: discord.Member,
    ) -> None:
        """Expulsa um membro; disponível somente para o proprietário."""
        if member == context.guild.me:
            await context.send("Não posso expulsar a mim mesmo.")
            return
        if member == context.author:
            await context.send("Você não pode usar o comando para se expulsar.")
            return

        try:
            await member.kick(reason=f"Owner kick by {context.author}")
        except discord.Forbidden:
            await context.send(
                "Não foi possível expulsar esse membro. "
                "Verifique a permissão Kick Members e a hierarquia de cargos."
            )
            return
        except discord.HTTPException:
            await context.send("O Discord recusou a expulsão. Tente novamente.")
            return

        await context.send(f"✅ {member} foi expulso do servidor.")
