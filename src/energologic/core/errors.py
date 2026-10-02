from __future__ import annotations


class ModelDecodeError(ValueError):
    """Raised when input does not conform to the structural model contract."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")
