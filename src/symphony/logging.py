# symphony_logging.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from lark import UnexpectedInput


def configure_logging(level: str = "DEBUG") -> None:
    """
    Configure root logging once, with filename and line number.
    """
    numeric_level = getattr(logging, level.upper(), logging.DEBUG)

    root = logging.getLogger()
    if root.handlers:
        root.setLevel(numeric_level)
        return

    logging.basicConfig(
        level=numeric_level,
        format="%(levelname)s %(filename)s:%(lineno)d — %(message)s",
    )


def _safe_line_extract(src: str, line_no: int) -> str:
    lines: List[str] = src.splitlines()
    if 1 <= line_no <= len(lines):
        return lines[line_no - 1]
    return ""


def _underline_column(line_text: str, column: int) -> str:
    # Tabs expanded for alignment
    prefix_expanded = line_text[: max(column - 1, 0)].expandtabs(4)
    caret_pos = len(prefix_expanded)
    return " " * caret_pos + "^"


def print_parse_error(err: UnexpectedInput, src: str, file_path: Path) -> None:
    """
    Pretty-print a parse error with context and an underline at the error column.
    """
    line = getattr(err, "line", -1)
    column = getattr(err, "column", -1)

    try:
        line_text = _safe_line_extract(src, line)
        pointer = _underline_column(line_text, column)

        msg = f"{file_path}:{line}:{column}: parse error\n{line_text}\n{pointer}\n"
        logging.error(msg.rstrip("\n"))
    except Exception:
        # Fall back to simpler reporting if anything goes wrong.
        logging.error("%s: parse error at line %s, column %s", file_path, line, column)
