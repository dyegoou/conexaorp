"""Configurações carregadas exclusivamente do ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Indica que uma configuração obrigatória não foi fornecida."""


def _split_roles(value: str) -> tuple[str, ...]:
    """Converte uma lista de cargos separada por vírgulas em nomes limpos."""
    roles = tuple(role.strip() for role in value.split(",") if role.strip())
    return roles or ("Administrador", "Moderador", "Admin")


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuração imutável usada pelo bot durante toda a execução."""

    discord_token: str
    owner_id: int
    payment_role_id: int
    payment_log_channel_id: int
    whitelist_panel_channel_id: int
    whitelist_ticket_category_id: int
    whitelist_staff_role_id: int
    whitelist_unverified_role_id: int
    whitelist_verified_role_id: int
    whitelist_second_role_id: int
    whitelist_website_url: str
    privileged_roles: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> Settings:
        """Carrega e valida as configurações necessárias para iniciar o bot."""
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise ConfigurationError(
                "A variável de ambiente DISCORD_TOKEN não foi configurada. "
                "Adicione-a como Secret antes de iniciar o bot."
            )

        owner_id_raw = os.getenv("DISCORD_OWNER_ID", "").strip()
        try:
            owner_id = int(owner_id_raw)
        except ValueError as exc:
            raise ConfigurationError(
                "A variável DISCORD_OWNER_ID precisa conter o ID numérico "
                "do proprietário do bot."
            ) from exc

        payment_role_id_raw = os.getenv("DISCORD_PAYMENT_ROLE_ID", "").strip()
        try:
            payment_role_id = int(payment_role_id_raw)
        except ValueError as exc:
            raise ConfigurationError(
                "A variável DISCORD_PAYMENT_ROLE_ID precisa conter o ID "
                "numérico do cargo autorizado para pagamentos."
            ) from exc

        payment_log_channel_id_raw = os.getenv(
            "DISCORD_PAYMENT_LOG_CHANNEL_ID",
            "",
        ).strip()
        try:
            payment_log_channel_id = int(payment_log_channel_id_raw)
        except ValueError as exc:
            raise ConfigurationError(
                "A variável DISCORD_PAYMENT_LOG_CHANNEL_ID precisa conter o ID "
                "numérico do canal que recebe os logs de pagamentos."
            ) from exc

        whitelist_ids: dict[str, int] = {}
        whitelist_id_labels = {
            "DISCORD_WHITELIST_PANEL_CHANNEL_ID": "canal do painel de whitelist",
            "DISCORD_WHITELIST_TICKET_CATEGORY_ID": "categoria dos tickets de whitelist",
            "DISCORD_WHITELIST_STAFF_ROLE_ID": "cargo da staff de whitelist",
            "DISCORD_WHITELIST_UNVERIFIED_ROLE_ID": "cargo Unverified",
            "DISCORD_WHITELIST_VERIFIED_ROLE_ID": "primeiro cargo após aprovação",
            "DISCORD_WHITELIST_SECOND_ROLE_ID": "segundo cargo após aprovação",
        }
        for env_name, label in whitelist_id_labels.items():
            raw_id = os.getenv(env_name, "").strip()
            try:
                whitelist_ids[env_name] = int(raw_id)
            except ValueError as exc:
                raise ConfigurationError(
                    f"A variável {env_name} precisa conter o ID numérico do "
                    f"{label}."
                ) from exc

        whitelist_website_url = os.getenv(
            "DISCORD_WHITELIST_WEBSITE_URL",
            "",
        ).strip()
        if not whitelist_website_url.startswith(("http://", "https://")):
            raise ConfigurationError(
                "A variável DISCORD_WHITELIST_WEBSITE_URL precisa conter um "
                "link http:// ou https:// válido."
            )

        roles = _split_roles(
            os.getenv(
                "DISCORD_ADMIN_ROLES",
                "Administrador,Moderador,Admin",
            )
        )
        return cls(
            discord_token=token,
            owner_id=owner_id,
            payment_role_id=payment_role_id,
            payment_log_channel_id=payment_log_channel_id,
            whitelist_panel_channel_id=whitelist_ids[
                "DISCORD_WHITELIST_PANEL_CHANNEL_ID"
            ],
            whitelist_ticket_category_id=whitelist_ids[
                "DISCORD_WHITELIST_TICKET_CATEGORY_ID"
            ],
            whitelist_staff_role_id=whitelist_ids["DISCORD_WHITELIST_STAFF_ROLE_ID"],
            whitelist_unverified_role_id=whitelist_ids[
                "DISCORD_WHITELIST_UNVERIFIED_ROLE_ID"
            ],
            whitelist_verified_role_id=whitelist_ids[
                "DISCORD_WHITELIST_VERIFIED_ROLE_ID"
            ],
            whitelist_second_role_id=whitelist_ids[
                "DISCORD_WHITELIST_SECOND_ROLE_ID"
            ],
            whitelist_website_url=whitelist_website_url,
            privileged_roles=roles,
        )