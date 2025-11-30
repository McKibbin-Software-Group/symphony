from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
import logging
from pathlib import Path
from typing import Any, List

import json
from lark import Lark, Tree, Token
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


def convert_tree_to_jsonable(node) -> Any:
    """
    Convert the Abstract Syntax Tree produced by the parser into a JSON-serializable structure.

    ### Arguments

    - `node`: The AST node to convert.

    ### Returns
    A JSON-serializable representation of the AST node.
    """
    if is_dataclass(node):
        return {f.name: convert_tree_to_jsonable(getattr(node, f.name)) for f in fields(node)}
    if isinstance(node, Enum):
        return node.value
    if isinstance(node, list):
        return [convert_tree_to_jsonable(x) for x in node]
    if isinstance(node, tuple):
        return [convert_tree_to_jsonable(x) for x in node]
    return node