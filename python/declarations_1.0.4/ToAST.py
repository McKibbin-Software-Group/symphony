# ToAST.py
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass, is_dataclass, fields
from enum import Enum
from typing import Any, List, Optional, Tuple, Union, Dict

from lark import Lark, Transformer, Token, Tree, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedToken, UnexpectedInput


# ========= AST node definitions =========

@dataclass(frozen=True)
class SourcePos:
    line: int
    column: int


class DeclType(str, Enum):
    member = "member"
    dimension = "dimension"
    dimensions = "dimensions"
    domain = "domain"
    parameter = "parameter"
    variable = "variable"
    equation = "equation"
    category = "category"


@dataclass(frozen=True)
class Decl:
    """Common fields shared by all declaration types."""
    decl_type: DeclType
    type_pos: SourcePos
    name: str
    name_pos: SourcePos
    label: str
    label_pos: SourcePos
    doc: Optional[str]
    doc_pos: Optional[SourcePos]


@dataclass(frozen=True)
class MemberDecl(Decl):
    pass


@dataclass(frozen=True)
class DimensionDecl(Decl):
    # Names of members in order
    dimension_values: List[str]


@dataclass(frozen=True)
class DimensionsDecl(Decl):
    # Currently grammar does not allow values here (kept for future use)
    dimension_values: List[str]


@dataclass(frozen=True)
class DomainDecl(Decl):
    pass


@dataclass(frozen=True)
class ParameterDecl(Decl):
    pass


@dataclass(frozen=True)
class VariableDecl(Decl):
    pass


@dataclass(frozen=True)
class EquationDecl(Decl):
    pass


@dataclass(frozen=True)
class CategoryDecl(Decl):
    # Names of members belonging to this category (order preserved)
    category_members: List[str]


DeclNode = Union[
    MemberDecl,
    DimensionDecl,
    DimensionsDecl,
    DomainDecl,
    ParameterDecl,
    VariableDecl,
    EquationDecl,
    CategoryDecl,
]


@dataclass(frozen=True)
class Program:
    decls: List[DeclNode]


# ========= Transformer =========

@v_args(meta=True)
class ToAST(Transformer):
    """
    Transforms the parse tree into typed dataclasses.
    Grammar enforces:
      - only 'dimension' and 'category' declarations may include bracketed lists
      - lists are NAMEs only (no strings)
    Transformer additionally enforces:
      - every NAME listed in a dimension/category list must be a 'member' declared earlier
      - no member may appear in more than one category
    """

    def __init__(self) -> None:
        super().__init__()
        # Symbol table of declared members (names), in document order
        self._declared_members: set[str] = set()
        # Track which category a member has been assigned to (uniqueness check)
        self._member_category: Dict[str, str] = {}

    def declaration(self, meta: Any, items: list[Any]) -> Any:
        # Unwrap the single child produced by dim_or_cat_decl/other_decl
        return items[0]

    @staticmethod
    def _parse_escaped_string(tok: Token) -> str:
        # tok.value includes quotes; json.loads() decodes escapes safely
        return json.loads(tok.value)

    def label(self, meta: Any, items: List[Token]) -> Tuple[str, SourcePos]:
        tok: Token = items[0]
        return self._parse_escaped_string(tok), SourcePos(tok.line, tok.column)

    # Return the list of NAME tokens (keep tokens so we can report exact positions on bad refs)
    def dimension_values(self, meta: Any, items: List[Token]) -> List[Token]:
        return items

    def doc(self, meta: Any, items: List[Token]) -> Tuple[str, SourcePos]:
        tok: Token = items[0]
        # Strip the triple quotes: """ ... """
        return tok.value[3:-3], SourcePos(tok.line, tok.column)

    def decl(self, meta: Any, items: List[Any]) -> DeclNode:
        # Two shapes arrive here (via -> decl in grammar):
        #  - (TYPE_DIMENSION | TYPE_CATEGORY) NAME ":" label [dimension_values] [doc]
        #  - TYPE_*                              NAME ":" label [doc]
        if len(items) < 3:
            raise ValueError("Internal: decl received too few items")

        type_tok: Token = items[0]
        name_tok: Token = items[1]
        label_text, label_pos = items[2]

        dim_value_toks: List[Token] = []
        doc_pair: Optional[Tuple[str, SourcePos]] = None

        # Optional suffixes: either [dimension_values] then [doc], or just [doc]
        if len(items) >= 4:
            fourth = items[3]
            if isinstance(fourth, list):           # dimension_values present
                dim_value_toks = fourth            # list[Token] (NAMEs)
                if len(items) >= 5:
                    doc_pair = items[4]
            else:
                doc_pair = fourth

        # Convert terminal type token text to enum
        type_text: str = str(type_tok)
        if type_text != type_text.lower():
            raise ValueError(
                f"Declaration type must be lower-case, found '{type_text}' "
                f"at {type_tok.line}:{type_tok.column}"
            )

        # Map to DeclType
        try:
            decl_type = DeclType(type_text)
        except ValueError:
            raise ValueError(
                f"Unknown declaration type '{type_text}' at "
                f"{type_tok.line}:{type_tok.column}"
            )

        type_pos = SourcePos(type_tok.line, type_tok.column)
        name_pos = SourcePos(name_tok.line, name_tok.column)
        name_str = str(name_tok)

        # dimension or category: validate references against previously-declared members
        if decl_type in (DeclType.dimension, DeclType.category):
            values_list: List[str] = []
            for vt in dim_value_toks:
                ref_name = str(vt)
                if ref_name not in self._declared_members:
                    raise ValueError(
                        f"Undefined member '{ref_name}' referenced by {decl_type.value} '{name_str}' "
                        f"at {vt.line}:{vt.column} — members must be declared earlier"
                    )
                if decl_type is DeclType.category:
                    # uniqueness constraint: a member can appear in at most one category
                    prev = self._member_category.get(ref_name)
                    if prev is not None and prev != name_str:
                        raise ValueError(
                            f"Member '{ref_name}' is already assigned to category '{prev}' "
                            f"and cannot also be in '{name_str}' (at {vt.line}:{vt.column})"
                        )
                    self._member_category[ref_name] = name_str
                values_list.append(ref_name)

            if decl_type is DeclType.dimension:
                node: DimensionDecl = DimensionDecl(
                    decl_type=decl_type,
                    type_pos=type_pos,
                    name=name_str,
                    name_pos=name_pos,
                    label=label_text,
                    label_pos=label_pos,
                    doc=doc_pair[0] if doc_pair else None,
                    doc_pos=doc_pair[1] if doc_pair else None,
                    dimension_values=values_list,
                )
                return node
            else:
                node: CategoryDecl = CategoryDecl(
                    decl_type=decl_type,
                    type_pos=type_pos,
                    name=name_str,
                    name_pos=name_pos,
                    label=label_text,
                    label_pos=label_pos,
                    doc=doc_pair[0] if doc_pair else None,
                    doc_pos=doc_pair[1] if doc_pair else None,
                    category_members=values_list,
                )
                return node

        # 'dimensions' (plural) currently does not allow values in grammar
        if decl_type == DeclType.dimensions:
            return DimensionsDecl(
                decl_type=decl_type,
                type_pos=type_pos,
                name=name_str,
                name_pos=name_pos,
                label=label_text,
                label_pos=label_pos,
                doc=doc_pair[0] if doc_pair else None,
                doc_pos=doc_pair[1] if doc_pair else None,
                dimension_values=[],
            )

        # Any other type: no dimension_values permitted
        if dim_value_toks:
            raise ValueError(
                f"member lists are only valid for 'dimension' or 'category' declarations "
                f"at {type_pos.line}:{type_pos.column} (in '{name_str}')"
            )

        # Add declared members to the symbol table
        if decl_type == DeclType.member:
            if name_str in self._declared_members:
                raise ValueError(
                    f"Duplicate member declaration '{name_str}' at {name_pos.line}:{name_pos.column}"
                )
            self._declared_members.add(name_str)
            return MemberDecl(
                decl_type=decl_type,
                type_pos=type_pos,
                name=name_str,
                name_pos=name_pos,
                label=label_text,
                label_pos=label_pos,
                doc=doc_pair[0] if doc_pair else None,
                doc_pos=doc_pair[1] if doc_pair else None,
            )

        if decl_type == DeclType.domain:
            return DomainDecl(
                decl_type=decl_type,
                type_pos=type_pos,
                name=name_str,
                name_pos=name_pos,
                label=label_text,
                label_pos=label_pos,
                doc=doc_pair[0] if doc_pair else None,
                doc_pos=doc_pair[1] if doc_pair else None,
            )
        if decl_type == DeclType.parameter:
            return ParameterDecl(
                decl_type=decl_type,
                type_pos=type_pos,
                name=name_str,
                name_pos=name_pos,
                label=label_text,
                label_pos=label_pos,
                doc=doc_pair[0] if doc_pair else None,
                doc_pos=doc_pair[1] if doc_pair else None,
            )
        if decl_type == DeclType.variable:
            return VariableDecl(
                decl_type=decl_type,
                type_pos=type_pos,
                name=name_str,
                name_pos=name_pos,
                label=label_text,
                label_pos=label_pos,
                doc=doc_pair[0] if doc_pair else None,
                doc_pos=doc_pair[1] if doc_pair else None,
            )
        if decl_type == DeclType.equation:
            return EquationDecl(
                decl_type=decl_type,
                type_pos=type_pos,
                name=name_str,
                name_pos=name_pos,
                label=label_text,
                label_pos=label_pos,
                doc=doc_pair[0] if doc_pair else None,
                doc_pos=doc_pair[1] if doc_pair else None,
            )

        raise AssertionError(f"Unhandled declaration type: {decl_type}")

    def start(self, meta: Any, items: List[DeclNode]) -> Program:
        return Program(decls=items)


# ========= Friendly error printing =========

def _safe_line_extract(src: str, line_no: int) -> str:
    lines: List[str] = src.splitlines()
    return lines[line_no - 1] if 1 <= line_no <= len(lines) else ""

def _underline_column(line_text: str, column: int) -> str:
    expanded: str = line_text.expandtabs(4)
    prefix_expanded: str = line_text[:max(column - 1, 0)].expandtabs(4)
    caret_pos: int = len(prefix_expanded)
    return " " * caret_pos + "^"

def print_parse_error(err: UnexpectedInput, src: str, file_path: pathlib.Path) -> None:
    line: int = getattr(err, "line", -1)
    column: int = getattr(err, "column", -1)
    try:
        context: str = err.get_context(src, span=60)
        sys.stderr.write(f"{file_path}:{line}:{column}: parse error\\n")
        sys.stderr.write(context + "\\n")
        return
    except Exception:
        pass

    sys.stderr.write(f"{file_path}:{line}:{column}: parse error\\n")
    line_text: str = _safe_line_extract(src, line)
    if line_text:
        sys.stderr.write(line_text + "\\n")
        sys.stderr.write(_underline_column(line_text, column) + "\\n")

    if isinstance(err, UnexpectedCharacters):
        allowed = ", ".join(sorted(err.allowed)) if getattr(err, "allowed", None) else "—"
        sys.stderr.write(f"Unexpected character. Expected one of: {allowed}\\n")
    elif isinstance(err, UnexpectedToken):
        expected = ", ".join(err.expected) if getattr(err, "expected", None) else "—"
        sys.stderr.write(f"Unexpected token {err.token!r}. Expected: {expected}\\n")
    else:
        sys.stderr.write(str(err) + "\\n")


# ========= AST text view (optional positions) =========

def _is_pos_like(field_name: str, value: Any) -> bool:
    if field_name.endswith("_pos"):
        return True
    if is_dataclass(value):
        tname = type(value).__name__
        if tname.lower().endswith("pos"):
            value_field_names = {f.name for f in fields(value)}
            return {"line", "column"}.issubset(value_field_names)
    return False

def _format_inline_value(val: Any) -> str:
    # Make enums display their raw value (e.g., 'category') instead of 'DeclType.category'
    if isinstance(val, Enum):
        return repr(val.value)
    sval = repr(val)
    if isinstance(val, str) and len(val) > 60:
        sval = repr(val[:57] + "...")
    return sval

def _dc_to_tree(node: Any, show_pos: bool) -> Tuple[str, List[Tuple[str, List[Tuple[str, list]]]]]:
    if not is_dataclass(node):
        return (repr(node), [])

    tname: str = type(node).__name__
    inline_bits: List[str] = [tname]
    child_slots: List[Tuple[str, Any]] = []

    for f in fields(node):
        val = getattr(node, f.name)

        # Hide position-like fields when show_pos is False
        if not show_pos and _is_pos_like(f.name, val):
            continue

        if is_dataclass(val):
            child_slots.append((f.name, val))
        elif isinstance(val, list):
            child_slots.append((f.name, val))
        else:
            inline_bits.append(f"{f.name}={_format_inline_value(val)}")

    label: str = " ".join(inline_bits)

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
                prefix: str = "│   " if i < len(gc) - 1 else "    "
                lines.append(f"{indent}{prefix}{cl}")
                if ck:
                    lines.extend(walk(cl, ck, indent + prefix)[1:])
        return lines

    return "\\n".join(walk(root_label, root_children))



# ========= Concise summary printer =========

def _decl_summary_line(d: DeclNode, show_pos: bool = False) -> str:
    pos = f" ({d.name_pos.line}:{d.name_pos.column})" if show_pos else ""
    if isinstance(d, DimensionDecl):
        vals = f" [{', '.join(d.dimension_values)}]" if d.dimension_values else ""
        return f"dimension {d.name}:{pos} {d.label!r}{vals}"
    if isinstance(d, CategoryDecl):
        vals = f" [{', '.join(d.category_members)}]" if d.category_members else ""
        return f"category {d.name}:{pos} {d.label!r}{vals}"
    if isinstance(d, MemberDecl):
        return f"member {d.name}:{pos} {d.label!r}"
    if isinstance(d, DimensionsDecl):
        return f"dimensions {d.name}:{pos} {d.label!r}"
    if isinstance(d, DomainDecl):
        return f"domain {d.name}:{pos} {d.label!r}"
    if isinstance(d, ParameterDecl):
        return f"parameter {d.name}:{pos} {d.label!r}"
    if isinstance(d, VariableDecl):
        return f"variable {d.name}:{pos} {d.label!r}"
    if isinstance(d, EquationDecl):
        return f"equation {d.name}:{pos} {d.label!r}"
    return repr(d)

def program_to_summary_text(prog: Program, show_pos: bool = False) -> str:
    lines = [_decl_summary_line(d, show_pos) for d in prog.decls]
    return "\n".join(lines)

# ========= Parser wiring =========

def build_parser(grammar_file: pathlib.Path) -> Lark:
    # Loads external grammar.lark
    return Lark.open(grammar_file, parser="lalr")

def parse_decls(parser: Lark, text: str) -> Program:
    tree: Tree = parser.parse(text)
    return ToAST().transform(tree)


# ========= CLI =========

def main() -> int:
    cli = argparse.ArgumentParser(
        description="Parse declarations with semantic checks: member lists must reference previously-declared members; categories are unique."
    )
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
        help="Include line/column position fields in the output",
    )
    cli.add_argument(
        "--format",
        choices=["summary", "tree"],
        default="summary",
        help="Output format: compact declaration summary (default) or full tree",
    )
    args = cli.parse_args()

    if not args.file.exists():
        sys.stderr.write(f"File not found: {args.file}\\n")
        return 2
    if not args.grammar.exists():
        sys.stderr.write(f"Grammar file not found: {args.grammar}\\n")
        return 2

    text: str = args.file.read_text(encoding="utf-8")
    parser: Lark = build_parser(args.grammar)

    try:
        program: Program = parse_decls(parser, text)
    except (UnexpectedCharacters, UnexpectedToken, UnexpectedInput) as err:
        print_parse_error(err, text, args.file)
        return 1
    except ValueError as err:
        # Semantic errors raised by the transformer
        sys.stderr.write(str(err) + "\\n")
        return 1

    # Print a concise AST text view (toggle positions with --show-pos)
    if args.format == "tree":
        txt: str = ast_to_text(program, show_pos=args.show_pos)
    else:
        txt = program_to_summary_text(program, show_pos=args.show_pos)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
