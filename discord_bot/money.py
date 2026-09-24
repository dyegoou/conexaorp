"""Formatação e validação de valores em reais brasileiros."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


class MoneyFormatError(ValueError):
    """Indica que o valor informado não pode ser convertido em reais."""


def format_brl(value: str) -> str:
    """Converte um valor livre para o formato brasileiro de moeda."""
    normalized = value.strip().replace("R$", "").replace(" ", "")
    if not normalized or not re.fullmatch(r"\d[\d.,]*", normalized):
        raise MoneyFormatError

    if normalized.count(",") > 1:
        raise MoneyFormatError

    if "," in normalized:
        integer_part, decimal_part = normalized.rsplit(",", maxsplit=1)
        if not decimal_part.isdigit() or len(decimal_part) > 2:
            raise MoneyFormatError
        integer_part = integer_part.replace(".", "")
    elif "." in normalized:
        parts = normalized.split(".")
        if len(parts) > 2:
            if any(len(part) != 3 for part in parts[1:]):
                raise MoneyFormatError
            integer_part = "".join(parts)
            decimal_part = "00"
        else:
            integer_part, decimal_part = parts
            if len(decimal_part) == 3:
                integer_part += decimal_part
                decimal_part = "00"
    else:
        integer_part, decimal_part = normalized, "00"

    if not integer_part.isdigit() or not decimal_part.isdigit():
        raise MoneyFormatError

    try:
        amount = Decimal(f"{integer_part}.{decimal_part or '0'}").quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    except InvalidOperation as exc:
        raise MoneyFormatError from exc

    if amount <= 0:
        raise MoneyFormatError

    formatted = f"{amount:,.2f}".replace(",", "_").replace(".", ",").replace(
        "_", "."
    )
    return f"R$ {formatted}"