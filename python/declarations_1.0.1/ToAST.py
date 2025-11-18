# decls_parser.py

# Run options:
# python decls_parser.py sample.sym
# python decls_parser.py sample.sym --show-pos

from __future__ import annotations

from enum import Enum
import json
import pathlib
from pathlib import Path
import argparse
import sys
from dataclasses import dataclass
from typing import Any, Optional, Tuple, List

from lark import Lark, Transformer, Token, Tree, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedToken, UnexpectedInput

from dataclasses import is_dataclass, fields

# ---------- AST node definitions ----------
@dataclass(frozen=True)
class SourcePos:
    line: int
    column: int


class DeclKind(str, Enum):
    VALUE = "VALUE"
    SET = "SET"
    SETLIST = "SETLIST"
    DOMAIN = "DOMAIN"
    PARAMETER = "PARAMETER"
    VARIABLE = "VARIABLE"
    EQUATION = "EQUATION"
    
@dataclass(frozen=True)
class NameDecl:
    kind: DeclKind
    kind_pos: SourcePos
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
        # STRICT grammar order: KIND NAME ":" label doc?
        # items[0] -> KIND token
        # items[1] -> NAME token
        # items[2] -> (label_text, label_pos)
        # items[3] -> (optional) (doc_text, doc_pos)
        kind_tok: Token = items[0]
        name_tok: Token = items[1]
        label_text, label_pos = items[2]
        doc_pair: Optional[Tuple[str, SourcePos]] = items[3] if len(items) > 3 else None

        kind_text: str = str(kind_tok).upper()
        try:
            kind = DeclKind(kind_text)
        except ValueError:
            # Defensive: shouldn’t happen with the fixed KIND terminal,
            # but keeps a helpful error if the grammar changes later.
            raise ValueError(f"Unknown declaration kind: {kind_text} at "
                             f"{kind_tok.line}:{kind_tok.column}")

        return NameDecl(
            kind=kind,
            kind_pos=SourcePos(kind_tok.line, kind_tok.column),
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


# --- AST visualisation utilities (add to ToAST.py) ---
def _is_pos_like(field_name: str, value: Any) -> bool:
    """
    Heuristic: treat fields as 'position-like' if
    - field name ends with '_pos', or
    - value is a dataclass whose type name ends with 'Pos' and has 'line' and 'column' fields.
    """
    if field_name.endswith("_pos"):
        return True
    if is_dataclass(value):
        tname = type(value).__name__
        if tname.lower().endswith("pos"):
            value_field_names = {f.name for f in fields(value)}
            return {"line", "column"}.issubset(value_field_names)
    return False

def _dc_to_tree(node: Any, show_pos: bool) -> Tuple[str, List[Tuple[str, List[Tuple[str, list]]]]]:
    """
    Convert a dataclass-based AST node into (label, children) tuples.
    - label: e.g. 'NameDecl kind=<...> name=<...> label=<...>'
    - children: list of (edge_label, [ (child_label, child_children), ... ])
    If show_pos is False, any fields that look like position info are omitted.
    """
    if not is_dataclass(node):
        return (repr(node), [])

    tname = type(node).__name__
    inline_bits: List[str] = [tname]
    child_slots: List[Tuple[str, Any]] = []

    for f in fields(node):
        val = getattr(node, f.name)

        # Skip position-like fields entirely if show_pos is False
        if not show_pos and _is_pos_like(f.name, val):
            continue

        if is_dataclass(val):
            child_slots.append((f.name, val))
        elif isinstance(val, list):
            child_slots.append((f.name, val))
        else:
            sval = repr(val)
            if isinstance(val, str) and len(val) > 60:
                sval = repr(val[:57] + "...")
            inline_bits.append(f"{f.name}={sval}")

    label = " ".join(inline_bits)

    children: List[Tuple[str, List[Tuple[str, list]]]] = []
    for name, val in child_slots:
        if isinstance(val, list):
            kids = [_dc_to_tree(v, show_pos) for v in val]
            children.append((f"{name}[]", kids))
        else:
            klabel, kchildren = _dc_to_tree(val, show_pos)
            children.append((name, [(klabel, kchildren)]))
    return (label, children)

def ast_to_text(root: Any, show_pos: bool = False) -> str:
    root_label, root_children = _dc_to_tree(root, show_pos)

    def walk(label: str, kids: List[Tuple[str, List[Tuple[str, list]]]], indent: str = "") -> List[str]:
        lines: List[str] = [f"{indent}{label}"]
        for edge_label, gc in kids:
            lines.append(f"{indent}├─ {edge_label}")
            for i, (cl, ck) in enumerate(gc):
                prefix = "│   " if i < len(gc) - 1 else "    "
                lines.append(f"{indent}{prefix}{cl}")
                if ck:
                    lines.extend(walk(cl, ck, indent + prefix)[1:])
        return lines

    return "\n".join(walk(root_label, root_children))

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
    cli.add_argument(
        "--show-pos",
        action="store_true",
        help="Include line/column position fields in the AST text output",
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


    txt = ast_to_text(program, show_pos=args.show_pos)
    # Path("abstract_syntax_tree.txt").write_text(txt, encoding="utf-8")
    print(f"Wrote abstract_syntax_tree.txt\n{txt}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
