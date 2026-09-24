"""Comandos gerais do bot."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.checks import (
    has_any_configured_role,
    has_configured_payment_role,
)
from discord_bot.embeds import (
    BRAND_COLOR,
    ERROR_COLOR,
    SUCCESS_COLOR,
    WARNING_COLOR,
    create_embed,
)
from discord_bot.money import MoneyFormatError, format_brl

BRAZIL_TIMEZONE = ZoneInfo("America/Sao_Paulo")


class GeneralCog(commands.Cog):
    """Comandos públicos e de administração básica."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _get_payment_log_channel(
        self,
        guild: discord.Guild,
    ) -> discord.abc.Messageable | None:
        """Busca o canal configurado e garante que ele pertence ao servidor atual."""
        channel_id = self.bot.settings.payment_log_channel_id
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except (discord.Forbidden, discord.HTTPException):
                return None

        channel_guild = getattr(channel, "guild", None)
        if (
            channel_guild is not None
            and channel_guild.id != guild.id
        ):
            return None
        if not isinstance(channel, discord.abc.Messageable):
            return None
        return channel

    @app_commands.command(name="ping", description="Verifica a latência do bot.")
    async def ping(self, interaction: discord.Interaction) -> None:
        """Responde com a latência atual do bot."""
        latency_ms = round(self.bot.latency * 1000)
        embed = create_embed(
            "Pong!",
            f"A conexão está estável.\n\n**{latency_ms} ms** de latência atual.",
            color=SUCCESS_COLOR,
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="ajuda",
        description="Exibe os comandos disponíveis e suas permissões.",
    )
    async def ajuda(self, interaction: discord.Interaction) -> None:
        """Lista os comandos disponíveis para os membros do servidor."""
        embed = create_embed(
            "Central de ajuda",
            "Use os slash commands abaixo para interagir com o bot.",
            guild=interaction.guild,
        )
        embed.add_field(
            name="/ping",
            value="Verifica se o bot está respondendo e mostra a latência.",
            inline=False,
        )
        embed.add_field(
            name="/ajuda",
            value="Exibe esta lista de comandos.",
            inline=False,
        )
        embed.add_field(
            name="/status",
            value="Mostra informações operacionais do bot. "
            "Disponível apenas para cargos autorizados.",
            inline=False,
        )
        embed.add_field(
            name="/pagamento",
            value="Publica uma confirmação de pagamento para um usuário ou cargo. "
            "Disponível apenas para cargos autorizados.",
            inline=False,
        )
        embed.add_field(
            name="$sync",
            value="Reinicia e sincroniza o bot. Disponível somente para o "
            "proprietário.",
            inline=False,
        )
        embed.add_field(
            name="$kick @usuário",
            value="Expulsa um membro do servidor. Disponível somente para o "
            "proprietário.",
            inline=False,
        )
        embed.add_field(
            name="/close",
            value="Fecha e remove o ticket atual. Disponível somente para a staff.",
            inline=False,
        )
        embed.add_field(
            name="/add e /remove",
            value="Adiciona ou remove uma pessoa do ticket atual. "
            "Disponível somente para a staff.",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="status",
        description="Exibe o status operacional do bot.",
    )
    @has_any_configured_role()
    async def status(self, interaction: discord.Interaction) -> None:
        """Mostra informações operacionais para a equipe autorizada."""
        guild_count = len(self.bot.guilds)
        latency_ms = round(self.bot.latency * 1000)
        embed = create_embed(
            "Status operacional",
            "O bot está online e pronto para receber comandos.",
            color=BRAND_COLOR,
            guild=interaction.guild,
        )
        embed.add_field(name="Latência", value=f"{latency_ms} ms", inline=True)
        embed.add_field(name="Servidores", value=str(guild_count), inline=True)
        embed.add_field(
            name="Comandos",
            value=str(len(self.bot.tree.get_commands())),
            inline=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="pagamento",
        description="Publica uma confirmação de pagamento recebido.",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        valor="Valor do pagamento, por exemplo: R$ 150,00",
        usuario="Usuário que recebeu o pagamento",
        cargo="Cargo que recebeu o pagamento",
        observacao="Observação opcional sobre o pagamento",
    )
    @has_configured_payment_role()
    async def pagamento(
        self,
        interaction: discord.Interaction,
        valor: str,
        usuario: discord.Member | None = None,
        cargo: discord.Role | None = None,
        observacao: str | None = None,
    ) -> None:
        """Publica uma confirmação para um usuário ou cargo, nunca para os dois."""
        try:
            valor = format_brl(valor)
        except MoneyFormatError:
            embed = create_embed(
                "Pagamento inválido",
                "Informe um valor positivo válido, como `10`, `10,50` ou "
                "`R$ 1.250,00`.",
                color=ERROR_COLOR,
                guild=interaction.guild,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if (usuario is None) == (cargo is None):
            embed = create_embed(
                "Pagamento inválido",
                "Mencione **um usuário ou um cargo**, mas não os dois.",
                color=ERROR_COLOR,
                guild=interaction.guild,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        recipient = (
            usuario.mention
            if usuario is not None
            else f"`{cargo.name}`"
        )
        recipient_name = (
            usuario.display_name if usuario is not None else cargo.name
        )
        guild = interaction.guild
        if guild is None:
            return

        log_channel = await self._get_payment_log_channel(guild)
        if log_channel is None:
            embed = create_embed(
                "Canal de logs indisponível",
                "Não foi possível acessar o canal configurado para os logs "
                "de pagamentos. Verifique o ID e as permissões do bot.",
                color=ERROR_COLOR,
                guild=guild,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if usuario is not None:
            recipients = [usuario]
        else:
            recipients = [
                member
                for member in cargo.members
                if not member.bot
            ]

        payment_date = datetime.now(BRAZIL_TIMEZONE).strftime(
            "%d/%m/%Y às %H:%M"
        )

        await interaction.response.defer(ephemeral=True)

        dm_embed = create_embed(
            None,
            "# :flag_br: Conexão Roleplay | Brasil\n"
            "## :moneybag: PAGAMENTO RECEBIDO\n\n"
            "> ***Comprovante digital de recebimento processado com sucesso.***\n\n"
            f"## **{valor}**\n"
            "🤑 Parabéns pelo recebimento!",
            color=SUCCESS_COLOR,
            guild=guild,
            include_brand_title=False,
            include_server_field=False,
        )
        dm_embed.add_field(
            name="👤 Beneficiário",
            value=f"{usuario.mention if usuario is not None else 'Membros do cargo'}"
            f"\n`{recipient_name}`",
            inline=True,
        )
        if cargo is not None:
            dm_embed.add_field(
                name="🏷️ Cargo contemplado",
                value=f"`{cargo.name}`",
                inline=True,
            )
        dm_embed.add_field(
            name="📅 Data do pagamento",
            value=f"`{payment_date}`\nHorário de Brasília",
            inline=True,
        )
        dm_embed.add_field(
            name="✅ Status",
            value="**PAGAMENTO APROVADO**",
            inline=True,
        )
        dm_embed.add_field(
            name="🧾 Documento",
            value="Holerite digital • Conexão RP",
            inline=True,
        )
        dm_embed.add_field(
            name="🔐 Processado por",
            value=interaction.user.mention,
            inline=True,
        )
        if observacao:
            dm_embed.add_field(
                name="📝 Observação",
                value=observacao[:1024],
                inline=False,
            )

        delivered = 0
        failed = 0
        for member in recipients:
            try:
                await member.send(embed=dm_embed)
                delivered += 1
            except (discord.Forbidden, discord.HTTPException):
                failed += 1

        embed = create_embed(
            None,
            "# :flag_br: Conexão Roleplay | Brasil\n"
            "## :moneybag: PAGAMENTO RECEBIDO\n\n"
            "> ***Comprovante digital de recebimento processado com sucesso.***\n\n"
            f"## **{valor}**\n"
            f"Parabéns, {recipient}! 🤑",
            color=SUCCESS_COLOR,
            guild=interaction.guild,
            include_brand_title=False,
            include_server_field=False,
        )
        embed.add_field(
            name="👤 Beneficiário",
            value=(
                f"{recipient}\n`{recipient_name}`"
                if usuario is not None
                else f"Membros do cargo\n`{recipient_name}`"
            ),
            inline=True,
        )
        if cargo is not None:
            embed.add_field(
                name="🏷️ Cargo contemplado",
                value=f"`{cargo.name}`",
                inline=True,
            )
        embed.add_field(
            name="📅 Data do pagamento",
            value=f"`{payment_date}`\nHorário de Brasília",
            inline=True,
        )
        embed.add_field(
            name="✅ Status",
            value="**PAGAMENTO APROVADO**",
            inline=True,
        )
        embed.add_field(
            name="🔐 Processado por",
            value=interaction.user.mention,
            inline=True,
        )
        if observacao:
            embed.add_field(
                name="📝 Observação",
                value=observacao[:1024],
                inline=False,
            )
        embed.add_field(
            name="📩 Notificações privadas",
            value=f"✅ {delivered} DM(s) enviada(s)"
            + (f"\n⚠️ {failed} não pôde(ram) ser enviada(s)." if failed else ""),
            inline=False,
        )

        try:
            await log_channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            error_embed = create_embed(
                "Log não enviado",
                "As DMs foram processadas, mas não foi possível publicar o "
                "registro no canal configurado. Verifique as permissões do bot.",
                color=ERROR_COLOR,
                guild=guild,
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        confirmation_embed = create_embed(
            None,
            "# :flag_br: Conexão Roleplay | Brasil\n"
            "## :white_check_mark: PAGAMENTO ENVIADO\n\n"
            "> ***O comando foi executado e o registro foi enviado para o "
            "canal de logs.***\n\n"
            f"📩 **{delivered}** DM(s) enviada(s)"
            + (
                f"\n⚠️ **{failed}** DM(s) não pôde(ram) ser enviada(s)."
                if failed
                else ""
            ),
            color=SUCCESS_COLOR,
            guild=guild,
            include_brand_title=False,
            include_server_field=False,
        )
        await interaction.followup.send(embed=confirmation_embed, ephemeral=True)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Responde de forma amigável a erros de permissão dos slash commands."""
        if isinstance(error, app_commands.errors.CheckFailure):
            message = (
                "Você não possui um cargo autorizado para usar este comando."
            )
            color = WARNING_COLOR
        else:
            message = "Não foi possível executar o comando. Tente novamente."
            color = ERROR_COLOR

        embed = create_embed(
            "Acesso não autorizado" if color == WARNING_COLOR else "Erro",
            message,
            color=color,
            guild=interaction.guild,
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)