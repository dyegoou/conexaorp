"""Estado temporário usado para concluir a mensagem de reinício após o exec."""

from __future__ import annotations

import json
from pathlib import Path

RESTART_STATE_PATH = Path("/tmp/discord_bot_restart_notice.json")


def save_pending_restart(channel_id: int, message_id: int) -> None:
    """Salva a mensagem que deverá ser atualizada após a reconexão."""
    temporary_path = RESTART_STATE_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps({"channel_id": channel_id, "message_id": message_id}),
        encoding="utf-8",
    )
    temporary_path.replace(RESTART_STATE_PATH)


def load_pending_restart() -> dict[str, int] | None:
    """Lê o aviso pendente, se houver uma sincronização em andamento."""
    try:
        data = json.loads(RESTART_STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None
    channel_id = data.get("channel_id")
    message_id = data.get("message_id")
    if not isinstance(channel_id, int) or not isinstance(message_id, int):
        return None
    return {"channel_id": channel_id, "message_id": message_id}


def clear_pending_restart() -> None:
    """Remove o estado temporário depois de tentar concluir o aviso."""
    try:
        RESTART_STATE_PATH.unlink()
    except FileNotFoundError:
        pass