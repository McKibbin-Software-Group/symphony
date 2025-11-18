# decls_parser.py
from __future__ import annotations

import json
import pathlib
import argparse
import sys
from dataclasses import dataclass
from typing import Any, Optional, Tuple, List

from lark import Lark, Transformer, Token, Tree, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedToken, UnexpectedInput


# ---------- AST node definitions ----------
@dataclass(frozen=True)
class SourcePos:
    line: int
    column: int

@dataclass(frozen=True)
class NameDecl:
    name: str
    name_pos: SourcePos
    label: str
    label_pos: SourcePos
    doc: Optional[str]
    doc_pos: Optional[SourcePos]

@dataclass(frozen=True)
class Program:
    decls: List[NameDecl]


# ---------- Transformer ----------
@v_args(meta=True)
class ToAST(Transformer):
    @staticmethod
    def _parse_escaped_string(tok: Token) -> str:
        return json.loads(tok.value)

    def label(self, meta: Any, items: List[Token]) -> Tuple[str, SourcePos]:
        tok: Token = items[0]
        return self._parse_escaped_string(tok), SourcePos(tok.line, tok.column)

    def doc(self, meta: Any, items: List[Token]) -> Tuple[str, SourcePos]:
        tok: Token = items[0]
        return tok.value[3:-3], SourcePos(tok.line, tok.column)

    def decl(self, meta: Any, items: List[Any]) -> NameDecl:
        name_tok: Token = items[0]
        label_text, label_pos = items[1]
        doc_pair: Optional[Tuple[str, SourcePos]] = items[2] if len(items) > 2 else None

        return NameDecl(
            name=str(name_tok),
            name_pos=SourcePos(name_tok.line, name_tok.column),
            label=label_text,
            label_pos=label_pos,
            doc=doc_pair[0] if doc_pair else None,
            doc_pos=doc_pair[1] if doc_pair else None,
        )

    def start(self, meta: Any, items: List[NameDecl]) -> Program:
        return Program(decls=items)


# ---------- Utility functions for friendly errors ----------
def _safe_line_extract(src: str, line_no: int) -> str:
    lines = src.splitlines()
    return lines[line_no - 1] if 1 <= line_no <= len(lines) else ""

def _underline_column(line_text: str, column: int) -> str:
    expanded = line_text.expandtabs(4)
    prefix_expanded = line_text[:max(column - 1, 0)].expandtabs(4)
    caret_pos = len(prefix_expanded)
    return " " * caret_pos + "^"

def print_parse_error(err: UnexpectedInput, src: str, file_path: pathlib.Path) -> None:
    line = getattr(err, "line", -1)
    column = getattr(err, "column", -1)

    try:
        context = err.get_context(src, span=60)
        sys.stderr.write(f"{file_path}:{line}:{column}: parse error\n")
        sys.stderr.write(context + "\n")
        return
    except Exception:
        pass

    sys.stderr.write(f"{file_path}:{line}:{column}: parse error\n")
    line_text = _safe_line_extract(src, line)
    if line_text:
        sys.stderr.write(line_text + "\n")
        sys.stderr.write(_underline_column(line_text, column) + "\n")

    if isinstance(err, UnexpectedCharacters):
        allowed = ", ".join(sorted(err.allowed)) if getattr(err, "allowed", None) else "—"
        sys.stderr.write(f"Unexpected character. Expected one of: {allowed}\n")
    elif isinstance(err, UnexpectedToken):
        expected = ", ".join(err.expected) if getattr(err, "expected", None) else "—"
        sys.stderr.write(f"Unexpected token {err.token!r}. Expected: {expected}\n")
    else:
        sys.stderr.write(str(err) + "\n")


# ---------- Parser setup ----------
def build_parser(grammar_file: pathlib.Path) -> Lark:
    return Lark.open(grammar_file, parser="lalr")


def parse_decls(parser: Lark, text: str) -> Program:
    tree: Tree = parser.parse(text)
    return ToAST().transform(tree)


# ---------- CLI ----------
def main() -> int:
    cli = argparse.ArgumentParser(description="Parse name/label declarations with friendly errors.")
    cli.add_argument("file", type=pathlib.Path, help="Declarations file to parse")
    cli.add_argument(
        "--grammar",
        type=pathlib.Path,
        default=pathlib.Path(__file__).with_name("grammar.lark"),
        help="Path to grammar file (default: grammar.lark in same directory)",
    )
    args = cli.parse_args()

    if not args.file.exists():
        sys.stderr.write(f"File not found: {args.file}\n")
        return 2
    if not args.grammar.exists():
        sys.stderr.write(f"Grammar file not found: {args.grammar}\n")
        return 2

    text = args.file.read_text(encoding="utf-8")
    parser = build_parser(args.grammar)

    try:
        program = parse_decls(parser, text)
    except (UnexpectedCharacters, UnexpectedToken, UnexpectedInput) as err:
        print_parse_error(err, text, args.file)
        return 1

    for d in program.decls:
        doc_at = f"{d.doc_pos.line}:{d.doc_pos.column}" if d.doc_pos else "None"
        print(
            f"{d.name}@{d.name_pos.line}:{d.name_pos.column} "
            f'label="{d.label}"@{d.label_pos.line}:{d.label_pos.column} '
            f"doc_at={doc_at}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
