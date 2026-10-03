from __future__ import annotations

import re
from typing import Mapping


CELL_ID_USER_CELL = "EnergoLogicCellId"
_CELL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class VisioIdentityError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def decode_user_literal(value: object) -> str:
    """Decode the bounded subset of User.* literals used by the Visio adapter."""

    text = str(value).strip()
    if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
        return text[1:-1].replace('""', '"')
    if text.startswith("="):
        return text[1:].strip()
    return text


def validate_cell_id(value: object) -> str:
    cell_id = decode_user_literal(value)
    if _CELL_ID.fullmatch(cell_id) is None:
        raise VisioIdentityError(
            "invalid_energologic_cell_id",
            (
                "EnergoLogicCellId must be 1..128 characters using only "
                "ASCII letters, digits, dot, underscore, colon or hyphen"
            ),
        )
    return cell_id


def projection_cell_id(user_cells: Mapping[str, str]) -> str | None:
    for name, raw in user_cells.items():
        if str(name).casefold() == CELL_ID_USER_CELL.casefold():
            decoded = decode_user_literal(raw)
            if not decoded:
                return None
            return validate_cell_id(decoded)
    return None
