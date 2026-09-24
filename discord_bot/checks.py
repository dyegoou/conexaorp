"""Checks reutilizáveis para autorização por cargo do Discord."""

from __future__ import annotations

import os
from collections.abc import Callable

import discord
from discord import app_commands
from discord.ext import commands

DEFAULT_PRIVILEGED_ROLES = ("Administrador", "Moderador", "Admin")


def configured_role_names() -> tuple[str, ...]:
    """Retorna os cargos autorizados, configuráveis sem alterar o código."""
    raw_roles = os.getenv("DISCORD_ADMIN_ROLES", "")
    roles = tuple(role.strip() for role in raw_roles.split(",") if role.strip())
    return roles or DEFAULT_PRIVILEGED_ROLES


def has_any_configured_role() -> Callable[[app_commands.Command], app_commands.Command]:
    """Restringe um slash command a qualquer cargo configurado."""
    role_names = configured_role_names()

    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return False
        return any(role.name in role_names for role in interaction.user.roles)

    return app_commands.check(predicate)


def is_configured_owner() -> Callable[[commands.Command], commands.Command]:
    """Permite um comando prefixado apenas ao proprietário configurado."""

    async def predicate(context: commands.Context[commands.Bot]) -> bool:
        settings = getattr(context.bot, "settings", None)
        return settings is not None and context.author.id == settings.owner_id

    return commands.check(predicate)


def has_configured_payment_role() -> Callable[[app_commands.Command], app_commands.Command]:
    """Permite pagamentos somente ao cargo de pagamentos configurado."""

    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return False
        settings = getattr(interaction.client, "settings", None)
        if settings is None:
            return False
        return any(
            role.id == settings.payment_role_id
            for role in interaction.user.roles
        )

    return app_commands.check(predicate)