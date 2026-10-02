from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .core import (
    ModelDecodeError,
    canonical_bytes,
    fingerprint,
    load_model,
    validate_model,
)


def _write_bytes(data: bytes, *, error: bool = False) -> None:
    stream = sys.stderr.buffer if error else sys.stdout.buffer
    stream.write(data)
    stream.flush()


def _write_json(data: object, *, error: bool = False) -> None:
    payload = (
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    _write_bytes(payload, error=error)


def _load_valid(path: Path):
    try:
        model = load_model(path)
    except (OSError, ModelDecodeError) as exc:
        if isinstance(exc, ModelDecodeError):
            issue = {"code": "decode_error", "path": exc.path, "message": exc.message}
        else:
            issue = {"code": "io_error", "path": str(path), "message": str(exc)}
        _write_json({"valid": False, "issues": [issue]}, error=True)
        return None, 2

    issues = validate_model(model)
    if issues:
        _write_json(
            {
                "valid": False,
                "issues": [
                    {"code": issue.code, "path": issue.path, "message": issue.message}
                    for issue in issues
                ],
            },
            error=True,
        )
        return None, 2
    return model, 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="energologic")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("validate", "canonicalize", "fingerprint"):
        command = subparsers.add_parser(name)
        command.add_argument("path", type=Path)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    model, status = _load_valid(args.path)
    if model is None:
        return status

    if args.command == "validate":
        _write_json(
            {
                "valid": True,
                "schema_version": model.schema_version,
                "model_id": model.model_id,
            }
        )
        return 0

    if args.command == "canonicalize":
        _write_bytes(canonical_bytes(model))
        return 0

    if args.command == "fingerprint":
        _write_bytes((fingerprint(model) + "\n").encode("ascii"))
        return 0

    raise AssertionError(f"unhandled command: {args.command}")
