"""Fluxo de whitelist com validação Roblox, tickets e análise da staff."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.checks import is_configured_owner
from discord_bot.embeds import (
    BRAND_COLOR,
    ERROR_COLOR,
    SUCCESS_COLOR,
    create_embed,
)

logger = logging.getLogger(__name__)

PANEL_FOOTER = "Conexão RP • Whitelist Panel"
TICKET_TOPIC_PREFIX = "WL|"


def _lookup_roblox_username(username: str) -> dict[str, Any] | None:
    """Consulta o nome na API pública do Roblox sem armazenar credenciais."""
    payload = json.dumps(
        {
            "usernames": [username.strip()],
            "excludeBannedUsers": False,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://users.roblox.com/v1/usernames/users",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ConexaoRP-DiscordBot/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (
        OSError,
        urllib.error.HTTPError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ):
        logger.exception("Falha ao consultar o nome do Roblox.")
        return None

    users = result.get("data", [])
    return users[0] if users else None


def _channel_slug(name: str) -> str:
    """Transforma o nome do Discord em um nome válido para canal."""
    slug = re.sub(r"[^a-z0-9-]+", "-", name.casefold()).strip("-")
    return (slug or "usuario")[:80] + "-wl"


def _topic_data(topic: str | None) -> dict[str, str] | None:
    """Extrai os dados mínimos da candidatura do tópico do ticket."""
    if not topic or not topic.startswith(TICKET_TOPIC_PREFIX):
        return None
    values: dict[str, str] = {}
    for part in topic.removeprefix(TICKET_TOPIC_PREFIX).split("|"):
        key, separator, value = part.partition("=")
        if separator and key and value:
            values[key] = value
    return values if "user_id" in values and "roblox_name" in values else None


class WhitelistPanelView(discord.ui.View):
    """View persistente do painel público de whitelist."""

    def __init__(self, cog: WhitelistCog) -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Faça WL",
        style=discord.ButtonStyle.success,
        custom_id="whitelist:start",
    )
    async def start_whitelist(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[WhitelistPanelView],
    ) -> None:
        """Abre o formulário completo da candidatura."""
        await interaction.response.send_modal(WhitelistApplicationModal(self.cog))


class WhitelistReviewView(discord.ui.View):
    """Botões persistentes de decisão da staff."""

    def __init__(self, cog: WhitelistCog, disabled: bool = False) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = disabled

    @discord.ui.button(
        label="Aprove",
        style=discord.ButtonStyle.success,
        custom_id="whitelist:approve",
    )
    async def approve(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[WhitelistReviewView],
    ) -> None:
        await self.cog.review_application(interaction, approved=True)

    @discord.ui.button(
        label="Reprovar",
        style=discord.ButtonStyle.danger,
        custom_id="whitelist:reject",
    )
    async def reject(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[WhitelistReviewView],
    ) -> None:
        await interaction.response.send_modal(RejectReasonModal(self.cog))


class RejectReasonModal(discord.ui.Modal, title="Motivo da reprovação"):
    """Modal obrigatório para registrar o motivo enviado ao candidato."""

    reason = discord.ui.TextInput(
        label="Motivo da reprovação",
        placeholder="Explique ao candidato o que precisa ser corrigido.",
        style=discord.TextStyle.paragraph,
        min_length=5,
        max_length=1000,
        required=True,
    )

    def __init__(self, cog: WhitelistCog) -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.review_application(
            interaction,
            approved=False,
            rejection_reason=self.reason.value.strip(),
        )


class WhitelistApplicationModal(discord.ui.Modal, title="Whitelist • Conexão RP"):
    """Modal com o Roblox e as perguntas básicas de roleplay."""

    roblox_username = discord.ui.TextInput(
        label="Nick do Roblox",
        placeholder="Digite seu nome exato do Roblox",
        min_length=3,
        max_length=20,
        required=True,
    )
    rdm = discord.ui.TextInput(
        label="O que é RDM?",
        placeholder="Explique com suas palavras.",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True,
    )
    pg = discord.ui.TextInput(
        label="O que é PG?",
        placeholder="Explique com suas palavras.",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True,
    )
    mg = discord.ui.TextInput(
        label="O que é MG?",
        placeholder="Explique com suas palavras.",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True,
    )

    def __init__(self, cog: WhitelistCog) -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        roblox_username = self.roblox_username.value.strip()
        roblox_user = await asyncio.to_thread(
            _lookup_roblox_username,
            roblox_username,
        )
        if roblox_user is None:
            embed = create_embed(
                "Roblox não encontrado",
                "Não foi possível achar esse nome do Roblox. "
                "Confira a grafia e envie a whitelist novamente.",
                color=ERROR_COLOR,
                guild=interaction.guild,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        answers = {
            "RDM": self.rdm.value.strip(),
            "PG": self.pg.value.strip(),
            "MG": self.mg.value.strip(),
        }
        await self.cog.create_ticket(
            interaction,
            roblox_user,
            answers,
        )


class WhitelistCog(commands.Cog):
    """Painel, tickets e decisões do processo de whitelist."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._panel_checked = False

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Aplica Unverified automaticamente a cada novo membro."""
        unverified = member.guild.get_role(
            self.bot.settings.whitelist_unverified_role_id
        )
        if unverified is None:
            logger.error(
                "Cargo Unverified %s não foi encontrado no servidor %s.",
                self.bot.settings.whitelist_unverified_role_id,
                member.guild.id,
            )
            return

        try:
            await member.add_roles(unverified, reason="Automatic unverified on join")
            logger.info(
                "Cargo Unverified aplicado ao novo membro %s (%s).",
                member,
                member.id,
            )
        except (discord.Forbidden, discord.HTTPException):
            logger.exception(
                "Não foi possível aplicar Unverified ao novo membro %s (%s).",
                member,
                member.id,
            )

    async def _get_panel_channel(
        self,
    ) -> discord.TextChannel | None:
        channel_id = self.bot.settings.whitelist_panel_channel_id
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except (discord.Forbidden, discord.HTTPException):
                return None
        return channel if isinstance(channel, discord.TextChannel) else None

    def panel_embed(self, guild: discord.Guild | None) -> discord.Embed:
        """Cria a apresentação pública da whitelist."""
        embed = create_embed(
            None,
            "# :flag_br: Conexão Roleplay | Brasil\n"
            "## :shield: SISTEMA DE WHITELIST\n\n"
            "> ***Este servidor é exclusivo para jogadores aprovados na "
            "Whitelist.***\n\n"
            "Para começar, clique no botão verde **Faça WL** e responda "
            "todas as perguntas com atenção.\n\n"
            "Seu Roblox será validado automaticamente antes da criação do "
            "ticket de análise.",
            color=SUCCESS_COLOR,
            guild=guild,
            include_brand_title=False,
            include_server_field=False,
        )
        embed.add_field(
            name="📋 Como funciona",
            value=(
                "1. Informe seu nick exato do Roblox.\n"
                "2. Responda às perguntas de roleplay.\n"
                "3. Aguarde a análise da equipe."
            ),
            inline=False,
        )
        embed.set_footer(text=PANEL_FOOTER)
        return embed

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Publica o painel uma vez no canal configurado."""
        if self._panel_checked:
            return
        self._panel_checked = True
        channel = await self._get_panel_channel()
        if channel is None or self.bot.user is None:
            logger.error("Canal do painel de whitelist indisponível.")
            return

        try:
            async for message in channel.history(limit=100):
                if (
                    message.author.id == self.bot.user.id
                    and message.embeds
                    and message.embeds[0].footer.text == PANEL_FOOTER
                ):
                    return
            await channel.send(
                embed=self.panel_embed(channel.guild),
                view=WhitelistPanelView(self),
            )
            logger.info("Painel de whitelist publicado no canal %s.", channel.id)
        except (discord.Forbidden, discord.HTTPException):
            logger.exception("Não foi possível publicar o painel de whitelist.")

    @commands.command(name="setupwl")
    @commands.guild_only()
    @is_configured_owner()
    async def setup_panel(self, context: commands.Context[commands.Bot]) -> None:
        """Publica manualmente um novo painel no canal configurado."""
        channel = await self._get_panel_channel()
        if channel is None:
            await context.send("Whitelist panel channel is unavailable.")
            return
        await channel.send(
            embed=self.panel_embed(context.guild),
            view=WhitelistPanelView(self),
        )
        await context.send("Whitelist panel published.", delete_after=10)

    def _staff_can_manage(self, interaction: discord.Interaction) -> bool:
        """Verifica se a pessoa possui o cargo de staff da whitelist."""
        return (
            isinstance(interaction.user, discord.Member)
            and self.bot.settings.whitelist_staff_role_id
            in {role.id for role in interaction.user.roles}
        )

    def _ticket_data_for(
        self,
        interaction: discord.Interaction,
    ) -> dict[str, str] | None:
        """Retorna os dados somente quando a interação veio de um ticket WL."""
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return None
        return _topic_data(channel.topic)

    @app_commands.command(
        name="close",
        description="Fecha e remove este ticket de whitelist.",
    )
    @app_commands.guild_only()
    async def close_ticket(self, interaction: discord.Interaction) -> None:
        """Remove um ticket quando a staff terminar o atendimento."""
        channel = interaction.channel
        if not self._staff_can_manage(interaction):
            await interaction.response.send_message(
                "Somente o cargo de staff configurado pode fechar tickets.",
                ephemeral=True,
            )
            return
        if not isinstance(channel, discord.TextChannel) or (
            self._ticket_data_for(interaction) is None
        ):
            await interaction.response.send_message(
                "Este comando só pode ser usado dentro de um ticket de whitelist.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "🔒 Ticket fechado. Este canal será removido em instantes.",
            ephemeral=True,
        )
        await asyncio.sleep(1)
        try:
            await channel.delete(reason=f"Whitelist ticket closed by {interaction.user}")
        except (discord.Forbidden, discord.HTTPException):
            logger.exception("Não foi possível fechar o ticket %s.", channel.id)

    @app_commands.command(
        name="add",
        description="Adiciona uma pessoa ao ticket de whitelist.",
    )
    @app_commands.guild_only()
    @app_commands.describe(membro="Pessoa que poderá ver e escrever no ticket.")
    async def add_to_ticket(
        self,
        interaction: discord.Interaction,
        membro: discord.Member,
    ) -> None:
        """Concede acesso de leitura e escrita a uma pessoa no ticket."""
        channel = interaction.channel
        if not self._staff_can_manage(interaction):
            await interaction.response.send_message(
                "Somente o cargo de staff configurado pode adicionar pessoas.",
                ephemeral=True,
            )
            return
        if not isinstance(channel, discord.TextChannel) or (
            self._ticket_data_for(interaction) is None
        ):
            await interaction.response.send_message(
                "Este comando só pode ser usado dentro de um ticket de whitelist.",
                ephemeral=True,
            )
            return

        try:
            await channel.set_permissions(
                membro,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                reason=f"Added by {interaction.user}",
            )
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message(
                "Não foi possível adicionar essa pessoa ao ticket.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"✅ {membro.mention} foi adicionado ao ticket.",
            ephemeral=True,
        )

    @app_commands.command(
        name="remove",
        description="Remove uma pessoa deste ticket de whitelist.",
    )
    @app_commands.guild_only()
    @app_commands.describe(membro="Pessoa que perderá acesso ao ticket.")
    async def remove_from_ticket(
        self,
        interaction: discord.Interaction,
        membro: discord.Member,
    ) -> None:
        """Remove o acesso de uma pessoa ao ticket."""
        channel = interaction.channel
        if not self._staff_can_manage(interaction):
            await interaction.response.send_message(
                "Somente o cargo de staff configurado pode remover pessoas.",
                ephemeral=True,
            )
            return
        if not isinstance(channel, discord.TextChannel) or (
            self._ticket_data_for(interaction) is None
        ):
            await interaction.response.send_message(
                "Este comando só pode ser usado dentro de um ticket de whitelist.",
                ephemeral=True,
            )
            return

        try:
            await channel.set_permissions(
                membro,
                overwrite=None,
                reason=f"Removed by {interaction.user}",
            )
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message(
                "Não foi possível remover essa pessoa do ticket.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"✅ {membro.mention} foi removido do ticket.",
            ephemeral=True,
        )

    async def create_ticket(
        self,
        interaction: discord.Interaction,
        roblox_user: dict[str, Any],
        answers: dict[str, str],
    ) -> None:
        """Cria um ticket privado para a equipe avaliar a candidatura."""
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.followup.send(
                "A whitelist só pode ser aberta dentro do servidor.",
                ephemeral=True,
            )
            return

        category = guild.get_channel(self.bot.settings.whitelist_ticket_category_id)
        staff_role = guild.get_role(self.bot.settings.whitelist_staff_role_id)
        if not isinstance(category, discord.CategoryChannel) or staff_role is None:
            await interaction.followup.send(
                "A configuração da categoria ou do cargo da staff está inválida.",
                ephemeral=True,
            )
            return

        for existing in category.text_channels:
            data = _topic_data(existing.topic)
            if data and data.get("user_id") == str(member.id):
                await interaction.followup.send(
                    f"Você já possui uma whitelist em análise: {existing.mention}",
                    ephemeral=True,
                )
                return

        roblox_name = str(roblox_user.get("name", "")).strip()
        roblox_id = str(roblox_user.get("id", "")).strip()
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
            ),
            staff_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            ),
        }
        if guild.me is not None:
            overwrites[guild.me] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            )

        try:
            ticket = await guild.create_text_channel(
                name=_channel_slug(member.name),
                category=category,
                topic=(
                    f"{TICKET_TOPIC_PREFIX}user_id={member.id}"
                    f"|roblox_id={roblox_id}|roblox_name={roblox_name}"
                ),
                overwrites=overwrites,
                reason="Whitelist application ticket",
            )
            await ticket.send(
                content=f"{member.mention} {staff_role.mention}",
                embed=self.review_embed(
                    guild,
                    member,
                    roblox_name,
                    answers,
                    status="AGUARDANDO ANÁLISE",
                ),
                view=WhitelistReviewView(self),
            )
        except (discord.Forbidden, discord.HTTPException):
            logger.exception("Não foi possível criar o ticket de whitelist.")
            await interaction.followup.send(
                "Não foi possível criar o ticket. Verifique as permissões do bot.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"✅ Sua whitelist foi enviada para análise em {ticket.mention}.",
            ephemeral=True,
        )

    def review_embed(
        self,
        guild: discord.Guild,
        member: discord.Member,
        roblox_name: str,
        answers: dict[str, str],
        *,
        status: str,
        reviewer: discord.Member | None = None,
        rejection_reason: str | None = None,
    ) -> discord.Embed:
        """Cria a embed privada que a staff usa para decidir."""
        embed = create_embed(
            None,
            "# :flag_br: Conexão Roleplay | Brasil\n"
            "## :shield: ANÁLISE DE WHITELIST",
            color=(
                SUCCESS_COLOR
                if status == "APROVADA"
                else ERROR_COLOR
                if status == "REPROVADA"
                else BRAND_COLOR
            ),
            guild=guild,
            include_brand_title=False,
            include_server_field=False,
        )
        embed.add_field(
            name="👤 Discord",
            value=f"{member.mention}\n`{member.display_name}`",
            inline=True,
        )
        embed.add_field(
            name="🎮 Roblox",
            value=f"`{roblox_name}`",
            inline=True,
        )
        embed.add_field(name="📌 Status", value=f"**{status}**", inline=True)
        for question, answer in answers.items():
            embed.add_field(
                name=f"❓ {question}",
                value=answer[:1024] or "`Sem resposta`",
                inline=False,
            )
        if rejection_reason:
            embed.add_field(
                name="📝 Motivo da reprovação",
                value=rejection_reason[:1024],
                inline=False,
            )
        if reviewer is not None:
            embed.add_field(
                name="🛡️ Analisado por",
                value=reviewer.mention,
                inline=False,
            )
        return embed

    async def _find_review_message(
        self,
        channel: discord.TextChannel,
    ) -> discord.Message | None:
        """Encontra a mensagem da candidatura dentro do ticket atual."""
        bot_user = self.bot.user
        if bot_user is None:
            return None
        async for message in channel.history(limit=100):
            if message.author.id != bot_user.id or not message.embeds:
                continue
            if any(
                field.name == "📌 Status"
                for field in message.embeds[0].fields
            ):
                return message
        return None

    async def _process_application(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        message: discord.Message,
        reviewer: discord.Member,
        *,
        approved: bool,
        rejection_reason: str | None = None,
    ) -> str:
        """Executa a mesma decisão usada pelos botões e pelos comandos."""
        data = _topic_data(channel.topic)
        if data is None:
            raise ValueError("Este canal não possui uma candidatura válida.")
        if not approved and not rejection_reason:
            raise ValueError("A reprovação precisa de um motivo.")

        status_field = next(
            (
                field
                for field in message.embeds[0].fields
                if field.name == "📌 Status"
            ),
            None,
        )
        if status_field is None or "AGUARDANDO ANÁLISE" not in status_field.value:
            current_status = (
                status_field.value.strip("* ")
                if status_field is not None
                else "sem status"
            )
            raise ValueError(
                f"Esta whitelist já foi decidida ({current_status}). "
                "Abra um novo ticket para uma nova análise."
            )

        applicant = guild.get_member(int(data["user_id"]))
        if applicant is None:
            applicant = await guild.fetch_member(int(data["user_id"]))
        roblox_name = data["roblox_name"]
        answers = {
            field.name.removeprefix("❓ "): field.value
            for field in message.embeds[0].fields
            if field.name.startswith("❓ ")
        }
        if approved:
            await self._approve_member(guild, applicant, roblox_name)
            status = "APROVADA"
        else:
            status = "REPROVADA"

        await message.edit(
            embed=self.review_embed(
                guild,
                applicant,
                roblox_name,
                answers,
                status=status,
                reviewer=reviewer,
                rejection_reason=rejection_reason,
            ),
            view=WhitelistReviewView(self, disabled=True),
        )
        if approved:
            dm_sent = await self._send_approval_dm(applicant, roblox_name)
            return (
                "✅ Whitelist aprovada. Cargos atualizados e instruções "
                + (
                    "enviadas por DM."
                    if dm_sent
                    else "não puderam ser enviadas por DM."
                )
            )

        dm_sent = await self._send_rejection_dm(
            applicant,
            roblox_name,
            rejection_reason or "A staff não informou um motivo.",
        )
        return (
            "Whitelist reprovada e registrada neste ticket. "
            + (
                "O motivo foi enviado por DM."
                if dm_sent
                else "Não foi possível enviar o motivo por DM."
            )
        )

    async def review_application(
        self,
        interaction: discord.Interaction,
        *,
        approved: bool,
        rejection_reason: str | None = None,
    ) -> None:
        """Valida a staff e aprova ou reprova a candidatura."""
        guild = interaction.guild
        reviewer = interaction.user
        if (
            guild is None
            or not isinstance(reviewer, discord.Member)
            or self.bot.settings.whitelist_staff_role_id
            not in {role.id for role in reviewer.roles}
        ):
            await interaction.response.send_message(
                "Somente o cargo de staff configurado pode decidir esta whitelist.",
                ephemeral=True,
            )
            return

        channel = interaction.channel
        data = _topic_data(getattr(channel, "topic", None))
        if data is None or not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Este canal não possui uma candidatura de whitelist válida.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            if not isinstance(interaction.message, discord.Message):
                raise ValueError("Mensagem de análise indisponível.")
            message = await self._process_application(
                guild,
                channel,
                interaction.message,
                reviewer,
                approved=approved,
                rejection_reason=rejection_reason,
            )
            await interaction.followup.send(message, ephemeral=True)
        except (discord.Forbidden, discord.HTTPException, RuntimeError, ValueError):
            logger.exception("Falha ao processar a decisão da whitelist.")
            await interaction.followup.send(
                "Não foi possível concluir a decisão. Verifique cargos, permissões "
                "e se o usuário ainda está no servidor.",
                ephemeral=True,
            )

    async def _approve_member(
        self,
        guild: discord.Guild,
        member: discord.Member,
        roblox_name: str,
    ) -> None:
        """Troca os cargos e tenta sincronizar o nick do Discord com o Roblox."""
        unverified = guild.get_role(self.bot.settings.whitelist_unverified_role_id)
        verified = guild.get_role(self.bot.settings.whitelist_verified_role_id)
        second = guild.get_role(self.bot.settings.whitelist_second_role_id)
        if unverified is None or verified is None or second is None:
            raise RuntimeError("Whitelist roles are unavailable")
        await member.remove_roles(unverified, reason="Whitelist approved")
        await member.add_roles(verified, second, reason="Whitelist approved")
        try:
            await member.edit(nick=roblox_name, reason="Whitelist approved")
        except (discord.Forbidden, discord.HTTPException):
            logger.warning("Não foi possível atualizar o nick de %s.", member.id)

    async def _send_approval_dm(
        self,
        member: discord.Member,
        roblox_name: str,
    ) -> bool:
        """Envia as instruções de cadastro após a aprovação."""
        embed = create_embed(
            None,
            "# :flag_br: Conexão Roleplay | Brasil\n"
            "## :white_check_mark: WHITELIST APROVADA\n\n"
            f"Parabéns, **{roblox_name}**! Sua whitelist foi aprovada.\n\n"
            f"Crie sua conta pelo link: {self.bot.settings.whitelist_website_url}",
            color=SUCCESS_COLOR,
            guild=member.guild,
            include_brand_title=False,
            include_server_field=False,
        )
        try:
            await member.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            logger.warning("Não foi possível enviar a aprovação por DM para %s.", member.id)
            return False
        return True

    async def _send_rejection_dm(
        self,
        member: discord.Member,
        roblox_name: str,
        reason: str,
    ) -> bool:
        """Envia o motivo da reprovação diretamente ao candidato."""
        embed = create_embed(
            None,
            "# :flag_br: Conexão Roleplay | Brasil\n"
            "## :x: WHITELIST REPROVADA\n\n"
            f"Sua whitelist para o Roblox **{roblox_name}** foi reprovada.\n\n"
            "Confira o motivo abaixo e tente novamente quando a staff orientar.",
            color=ERROR_COLOR,
            guild=member.guild,
            include_brand_title=False,
            include_server_field=False,
        )
        embed.add_field(
            name="📝 Motivo da reprovação",
            value=reason[:1024],
            inline=False,
        )
        try:
            await member.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            logger.warning("Não foi possível enviar a reprovação por DM para %s.", member.id)
            return False
        return True