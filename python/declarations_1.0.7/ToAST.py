from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass, is_dataclass, fields
from enum import Enum
from typing import Any, List, Optional, Tuple, Union, Dict, Iterable

from lark import Lark, Transformer, Token, Tree, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedToken, UnexpectedInput


# ========= AST node definitions =========

@dataclass(frozen=True)
class SourcePosition:
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
    type_pos: SourcePosition
    name: str
    name_pos: SourcePosition
    label: str
    label_pos: SourcePosition
    doc: Optional[str]
    doc_pos: Optional[SourcePosition]


@dataclass(frozen=True)
class MemberDecl(Decl):
    pass


@dataclass(frozen=True)
class DimensionDecl(Decl):
    # Names of members in order (duplicates removed by union-like semantics)
    dimension_values: List[str]


@dataclass(frozen=True)
class DimensionsDecl(Decl):
    pass


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

# Internal structures used while transforming a dimension expression
DimTerm = Tuple[str, Any]   # ("list", List[Token]) | ("ref", Tuple[str, SourcePos])
DimExpr = Tuple[str, Any, List[Tuple[str, Any]]]  # ("expr", first_term, [(op, term), ...])


@v_args(meta=True)
class ToAST(Transformer):
    """
    Transforms the parse tree into typed dataclasses.

    Grammar enforces:
      - 'category' must be a bracketed list of member references
      - 'dimension' may carry an expression: lists and references to other dimension(s) combined with '+' or '-'

    Transformer semantics & checks:
      1) Every NAME listed in a list must be a 'reference to something' that was declared earlier (e.g. a member or a dimension).
      2) No member may appear in more than one category.
      3) Every member must be in a (single) category by the end of the file.
      4) Every dimension evaluates to an ordered, list of unique members where:
         - '+' performs an order-preserving union of the two arguments
         - '-' removes any occurrences of members in the second argument from those in the first argument
      5) Every member in a dimension's *final* list must belong to the SAME category.
      6) Arguments to the expressions used to determine a dimension can be lists of members or references to other dimensions.
    """

    def __init__(self) -> None:
        super().__init__()
        # Symbol tables
        self._declared_members: set[str] = set()
        self._member_category: Dict[str, str] = {}
        self._declared_dimensions: Dict[str, List[str]] = {}

    # ---- low-level helpers ----

    @staticmethod
    def _position(token: Token) -> SourcePosition:
        return SourcePosition(token.line, token.column)

    @staticmethod
    def _parse_escaped_string(token: Token) -> str:
        # token.value includes quotes; json.loads() decodes escapes safely
        return json.loads(token.value)

    # ---- grammar rule handlers ----

    def label(self, meta: Any, items: List[Token]) -> Tuple[str, SourcePosition]:
        token: Token = items[0]
        return self._parse_escaped_string(token), self._position(token)

    def doc(self, meta: Any, items: List[Token]) -> Tuple[str, SourcePosition]:
        # Accept triple-quoted docstrings when present; do not require them
        token: Token = items[0]
        # Strip the triple quotes:
        return token.value[3:-3], self._position(token)

    # Dimension expression pieces
    def dimension_list(self, meta: Any, items: List[Token]) -> DimTerm:
        # Keep tokens so we have accurate error positions
        return ("dimension_list", items)

    def dimension_reference(self, meta: Any, items: List[Token]) -> DimTerm:
        name_token: Token = items[0]
        return ("dimension_reference", (str(name_token), self._position(name_token)))

    def dimension_expression(self, meta: Any, items: List[Any]) -> DimExpr:
        # items like: [term, Token('+'), term, Token('-'), term, ...]
        if not items:
            return ("dimension_expression", ("dimension_list", []), [])
        first = items[0]
        operator_tokens: List[Tuple[str, Any]] = []
        i = 1
        while i < len(items):
            operator_token: Token = items[i]
            term = items[i + 1]
            operator_tokens.append((str(operator_token), term))
            i += 2
        return ("dimension_expression", first, operator_tokens)

    # Declarations

    def declaration(self, meta: Any, items: list[Any]) -> Any:
        return items[0]

    # Utilities to robustly extract optional pieces regardless of order/presence
    @staticmethod
    def _pick_doc_and_expr(extra: List[Any]) -> Tuple[Optional[Tuple[str, SourcePosition]], Optional[DimExpr]]:
        doc_pair: Optional[Tuple[str, SourcePosition]] = None
        expr: Optional[DimExpr] = None
        for it in extra:
            if isinstance(it, tuple):
                # expr tuples are marked with first element "expr"
                if len(it) >= 1 and isinstance(it[0], str) and it[0] == "expr":
                    expr = it  # type: ignore[assignment]
                else:
                    # treat as doc payload (text, pos)
                    if doc_pair is None and len(it) == 2 and isinstance(it[0], str):
                        doc_pair = it  # type: ignore[assignment]
        return doc_pair, expr

    @staticmethod
    def _pick_doc_and_list(extra: List[Any]) -> Tuple[Optional[Tuple[str, SourcePosition]], Optional[DimTerm]]:
        doc_pair: Optional[Tuple[str, SourcePosition]] = None
        list_term: Optional[DimTerm] = None
        for it in extra:
            if isinstance(it, tuple):
                if len(it) >= 1 and isinstance(it[0], str) and it[0] == "list":
                    list_term = it  # type: ignore[assignment]
                else:
                    if doc_pair is None and len(it) == 2 and isinstance(it[0], str):
                        doc_pair = it  # type: ignore[assignment]
        return doc_pair, list_term

    def other_decl(self, meta: Any, items: list[Any]) -> DeclNode:
        # TYPE_OTHER NAME ":" label (doc)?
        type_token: Token = items[0]
        name_token: Token = items[1]
        label_text, label_pos = items[2]

        # Everything after the label is optional; take the first (text, pos) tuple as doc if present
        doc_pair: Optional[Tuple[str, SourcePosition]] = None
        for it in items[3:]:
            if isinstance(it, tuple) and len(it) == 2 and isinstance(it[0], str):
                doc_pair = it  # type: ignore[assignment]
                break
        return self._build_other(type_token, name_token, label_text, label_pos, doc_pair)

    def category_decl(self, meta: Any, items: list[Any]) -> DeclNode:
        # "category" NAME ":" label (dim_list)? (doc)?
        type_tok = Token("TYPE", "category")
        name_tok: Token = items[0]
        label_text, label_pos = items[1]

        doc_pair, list_term = self._pick_doc_and_list(items[2:])
        return self._build_category(type_tok, name_tok, label_text, label_pos, list_term, doc_pair)

    def dimension_decl(self, meta: Any, items: list[Any]) -> DeclNode:
        # "dimension" NAME ":" label (dim_expr)? (doc)?
        type_tok = Token("TYPE", "dimension")
        name_tok: Token = items[0]
        label_text, label_pos = items[1]

        # The rest (if any) can appear in any order; both are optional
        doc_pair, expr = self._pick_doc_and_expr(items[2:])
        return self._build_dimension(type_tok, name_tok, label_text, label_pos, expr, doc_pair)

    # ---- builders ----

    def _build_dimension(
        self,
        type_tok: Token,
        name_tok: Token,
        label_text: str,
        label_pos: SourcePosition,
        expr: Optional[DimExpr],
        doc_pair: Optional[Tuple[str, SourcePosition]],
    ) -> DimensionDecl:
        type_pos = self._position(type_tok)
        name_pos = self._position(name_tok)
        name_str = str(name_tok)

        # Evaluate the expression (or empty -> [])
        values_list: List[str] = self._evaluate_dim_expr(expr) if expr else []

        # Check category membership constraints (must exist and be single category)
        missing: List[str] = [m for m in values_list if m not in self._member_category]
        if missing:
            raise ValueError(
                f"Dimension '{name_str}' lists members not assigned to any category: "
                f"{', '.join(missing)}. Declare a category including these members before this dimension."
            )

        cats = {self._member_category[m] for m in values_list}
        if len(cats) > 1:
            by_cat: Dict[str, List[str]] = {}
            for m in values_list:
                c = self._member_category.get(m, "<none>")
                by_cat.setdefault(c, []).append(m)
            parts = [f"{c}: [{', '.join(ms)}]" for c, ms in by_cat.items()]
            detail = "; ".join(parts)
            raise ValueError(
                f"Dimension '{name_str}' must consist of members from a single category, "
                f"but members span multiple categories: {detail}"
            )

        node: DimensionDecl = DimensionDecl(
            decl_type=DeclType.dimension,
            type_pos=type_pos,
            name=name_str,
            name_pos=name_pos,
            label=label_text,
            label_pos=label_pos,
            doc=doc_pair[0] if doc_pair else None,
            doc_pos=doc_pair[1] if doc_pair else None,
            dimension_values=values_list,
        )
        # Register for future references
        self._declared_dimensions[name_str] = values_list
        return node

    def _build_category(
        self,
        type_tok: Token,
        name_tok: Token,
        label_text: str,
        label_pos: SourcePosition,
        list_term: Optional[DimTerm],
        doc_pair: Optional[Tuple[str, SourcePosition]],
    ) -> CategoryDecl:
        type_pos = self._position(type_tok)
        name_pos = self._position(name_tok)
        name_str = str(name_tok)

        # Validate and extract members
        members: List[str] = []
        if list_term is not None:
            tag, payload = list_term
            assert tag == "list"
            for vt in payload:  # payload is List[Token]
                ref_name = str(vt)
                if ref_name not in self._declared_members:
                    raise ValueError(
                        f"Undefined member '{ref_name}' referenced by category '{name_str}' "
                        f"at {vt.line}:{vt.column} — members must be declared earlier"
                    )
                # uniqueness: a member can be in at most one category
                prev = self._member_category.get(ref_name)
                if prev is not None and prev != name_str:
                    raise ValueError(
                        f"Member '{ref_name}' is already assigned to category '{prev}' "
                        f"and cannot also be in '{name_str}' (at {vt.line}:{vt.column})"
                    )
                self._member_category[ref_name] = name_str
                members.append(ref_name)

        node: CategoryDecl = CategoryDecl(
            decl_type=DeclType.category,
            type_pos=type_pos,
            name=name_str,
            name_pos=name_pos,
            label=label_text,
            label_pos=label_pos,
            doc=doc_pair[0] if doc_pair else None,
            doc_pos=doc_pair[1] if doc_pair else None,
            category_members=members,
        )
        return node

    def _build_other(
        self,
        type_tok: Token,
        name_tok: Token,
        label_text: str,
        label_pos: SourcePosition,
        doc_pair: Optional[Tuple[str, SourcePosition]],
    ) -> DeclNode:
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

        type_pos = self._position(type_tok)
        name_pos = self._position(name_tok)
        name_str = str(name_tok)

        # Lists/expressions are not permitted here
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

    # ---- dimension expression evaluation ----

    def _validate_member_tokens(self, toks: Iterable[Token], owner: str) -> List[str]:
        out: List[str] = []
        for vt in toks:
            ref_name = str(vt)
            if ref_name not in self._declared_members:
                raise ValueError(
                    f"Undefined member '{ref_name}' referenced by {owner} "
                    f"at {vt.line}:{vt.column} — members must be declared earlier"
                )
            out.append(ref_name)
        return out

    @staticmethod
    def _union_preserving(base: List[str], to_add: Iterable[str]) -> List[str]:
        seen = set(base)
        for x in to_add:
            if x not in seen:
                base.append(x)
                seen.add(x)
        return base

    @staticmethod
    def _subtract(base: List[str], to_remove: Iterable[str]) -> List[str]:
        remove_set = set(to_remove)
        if not remove_set:
            return base
        # Keep order, drop anything in remove_set
        return [x for x in base if x not in remove_set]

    def _eval_term(self, term: DimTerm, owner_dim: str) -> List[str]:
        tag, payload = term
        if tag == "list":
            # payload: List[Token]
            return self._validate_member_tokens(payload, f"dimension '{owner_dim}'")
        elif tag == "ref":
            ref_name, ref_pos = payload
            if ref_name not in self._declared_dimensions:
                raise ValueError(
                    f"Dimension '{owner_dim}' references unknown dimension '{ref_name}' "
                    f"at {ref_pos.line}:{ref_pos.column}. Dimensions must be declared earlier to be referenced."
                )
            return list(self._declared_dimensions[ref_name])
        else:
            raise AssertionError(f"Unknown dim term tag: {tag}")

    def _evaluate_dim_expr(self, expr: Optional[DimExpr]) -> List[str]:
        if not expr:
            return []
        _tag, first, ops = expr
        # Start from first term
        # Use a copy to avoid aliasing stored dimensions
        result: List[str] = list(self._eval_term(first, owner_dim="(evaluating)"))
        # Apply operations in order
        for op, term in ops:
            values = self._eval_term(term, owner_dim="(evaluating)")
            if op == "+":
                result = self._union_preserving(result, values)
            elif op == "-":
                result = self._subtract(result, values)
            else:
                raise AssertionError(f"Unknown operator {op}")
        return result

    def start(self, meta: Any, items: List[DeclNode]) -> Program:
        # Final constraint: all declared members must be assigned to a category
        unassigned = [m for m in self._declared_members if m not in self._member_category]
        if unassigned:
            raise ValueError(
                "All members must be in a category, but the following member(s) are not assigned: "
                + ", ".join(sorted(unassigned))
            )
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
        sys.stderr.write(f"{file_path}:{line}:{column}: parse error\n")
        sys.stderr.write(context + "\n")
        return
    except Exception:
        pass

    sys.stderr.write(f"{file_path}:{line}:{column}: parse error\n")
    line_text: str = _safe_line_extract(src, line)
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


# ========= AST text/summary printers =========

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

    return "\n".join(walk(root_label, root_children))


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
    return Lark.open(grammar_file, parser="lalr")

def parse_decls(parser: Lark, text: str) -> Program:
    tree: Tree = parser.parse(text)
    return ToAST().transform(tree)

# ========= CLI =========

def main() -> int:
    cli = argparse.ArgumentParser(
        description=(
            "Parse declarations with semantic checks & dimension expressions: "
            "(1) all members must be in exactly one category; "
            "(2) categories cannot share members; "
            "(3) dimension members must all come from the same category; "
            "(4) dimension values may be lists and/or previously-declared dimensions "
            "combined with '+' (order-preserving union) and '-' (remove). "
            "(5) Triple-quoted docstrings are optional for all declarations."
        )
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
        sys.stderr.write(f"File not found: {args.file}\n")
        return 2
    if not args.grammar.exists():
        sys.stderr.write(f"Grammar file not found: {args.grammar}\n")
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
        sys.stderr.write(str(err) + "\n")
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
