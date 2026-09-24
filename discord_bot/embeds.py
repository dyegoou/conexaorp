"""Fábrica de embeds com a identidade visual do bot."""

from __future__ import annotations

from datetime import UTC, datetime

import discord

BRAND_COLOR = discord.Color.from_rgb(88, 101, 242)
SUCCESS_COLOR = discord.Color.from_rgb(87, 242, 135)
WARNING_COLOR = discord.Color.from_rgb(254, 231, 92)
ERROR_COLOR = discord.Color.from_rgb(237, 66, 69)
BRAND_TITLE = "🇧🇷 Conexão Roleplay | Brasil"


def create_embed(
    section: str | None,
    description: str,
    *,
    color: discord.Color = BRAND_COLOR,
    guild: discord.Guild | None = None,
    include_brand_title: bool = True,
    include_server_field: bool = True,
) -> discord.Embed:
    """Cria embeds consistentes com marca, servidor e contexto visual."""
    embed = discord.Embed(
        title=BRAND_TITLE if include_brand_title else None,
        description=description,
        color=color,
        timestamp=datetime.now(UTC),
    )
    if section:
        embed.set_author(name=section)

    if guild is not None:
        server_name = discord.utils.escape_markdown(guild.name)
        if include_server_field:
            embed.add_field(
                name="Servidor",
                value=f"**{server_name}**",
                inline=True,
            )
        if guild.icon is not None:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"{BRAND_TITLE} • {guild.name}")
    else:
        embed.set_footer(text=BRAND_TITLE)

    return embed