# symphony_toast.py
# TODO: Eventually to be replaced fully by a mult-pass processor.
# Lark transformer, parser wiring, CLI
from __future__ import annotations

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s %(filename)s:%(lineno)d — %(message)s"
)

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

from lark import Lark, Transformer, Token, Tree, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedInput, UnexpectedToken

from symphony.abstract_syntax_tree import (
    CategoryDeclaration,
    DeclarationNode,
    DeclarationType,
    DimensionDeclaration,
    DimensionsDeclaration,
    DomainDeclaration,
    EquationDeclaration,
    MemberDeclaration,
    ParameterDeclaration,
    Program,
    SourcePosition,
    VariableDeclaration,
    abstract_syntax_tree_to_text,
    program_to_summary_text,
)


# The content + position of a docstring for an entity.
Documentation = Tuple[str, SourcePosition]

# Internal structures used while transforming a dimension expression:
# ("list", List[Token])  -> a bracketed list of member names
# ("dimension reference", (name, SourcePosition)) -> reference to a dimension
DimensionTerm = Tuple[str, Any]
DimensionExpression = Tuple[str, DimensionTerm, List[Tuple[str, DimensionTerm]]]
# ("dimension_expression", first_term, [(op, term), ...])


@v_args(meta=True)
class ToAST(Transformer):
    """
    Parse-tree → AST transformer plus first-pass semantic checks.

    Transformer semantics & checks:
      1) Every NAME in a list must refer to a previously-declared member.
      2) No member may appear in more than one category.
      3) Every member must be in exactly one category by the end of the file.
      4) Every dimension expression evaluates to an ordered list of unique members:
         - '+' performs an order-preserving union
         - '-' removes any members appearing in the right-hand side
      5) All members in a dimension must belong to the same category.
      6) A dimension term may be either:
         - a bracketed member list, or
         - a reference to a previously-declared dimension.
    """

    def __init__(self) -> None:
        super().__init__()

        # Symbol tables used during transformation
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
        # TRIPLE_STRING token; strip the triple quotes
        token: Token = items[0]
        text = token.value[3:-3]
        return text, self._position(token)

    # --- dimension expression primitives ---

    def name_list(self, meta: Any, items: List[Token]) -> DimensionTerm:
        # Normalise tag to 'list' so downstream code only has to handle 'list'/'ref'
        return ("list", items)

    def dimension_reference(self, meta: Any, items: List[Token]) -> DimensionTerm:
        # Reference to a previously-declared dimension (or category)
        name_token: Token = items[0]
        return ("dimension reference", (str(name_token), self._position(name_token)))

    def dimension_expression(self, meta: Any, items: List[Any]) -> DimensionExpression:
        # items like: [term, Token('+'), term, Token('-'), term, ...]
        if not items:
            # Empty expression = empty list of members
            empty_term: DimensionTerm = ("list", [])
            return ("dimension_expression", empty_term, [])
        first_term: DimensionTerm = items[0]
        operator_tokens: List[Tuple[str, DimensionTerm]] = []
        i = 1
        while i < len(items):
            operator_token: Token = items[i]
            term: DimensionTerm = items[i + 1]
            operator_tokens.append((str(operator_token), term))
            i += 2
        return ("dimension_expression", first_term, operator_tokens)

    # --- declaration grouping rule ---

    def declaration(self, meta: Any, items: List[Any]) -> Any:
        # Grammar wraps each specific decl rule in a 'declaration' rule.
        return items[0]

    # --- helpers for pulling optional pieces from a decl ---

    @staticmethod
    def _pick_doc_and_expr(
        extra_items: List[Any],
    ) -> Tuple[Optional[Documentation], Optional[DimensionExpression]]:
        """
        Collect optional documentation and a dimension expression from an
        arbitrary list of extra_items (order-insensitive).
        """
        documentation: Optional[Documentation] = None
        expression: Optional[DimensionExpression] = None
        for item in extra_items:
            if isinstance(item, tuple):
                if len(item) >= 1 and isinstance(item[0], str) and item[0] == "dimension_expression":
                    expression = item  # type: ignore[assignment]
                elif documentation is None and len(item) == 2 and isinstance(item[0], str):
                    documentation = item  # type: ignore[assignment]
        return documentation, expression

    @staticmethod
    def _pick_doc_and_list(
        extra_items: List[Any],
    ) -> Tuple[Optional[Documentation], Optional[DimensionTerm]]:
        """
        Collect optional documentation and a name_list DimTerm from an
        arbitrary list of extra_items (order-insensitive).
        """
        documentation: Optional[Documentation] = None
        list_term: Optional[DimensionTerm] = None
        for item in extra_items:
            if isinstance(item, tuple):
                if len(item) >= 1 and isinstance(item[0], str) and item[0] == "list":
                    list_term = item  # type: ignore[assignment]
                elif documentation is None and len(item) == 2 and isinstance(item[0], str):
                    documentation = item  # type: ignore[assignment]
        return documentation, list_term

    # --- concrete declaration rules ---

    def category_decl(self, meta: Any, items: List[Any]) -> DeclarationNode:
        # "category" NAME ":" label name_list? doc?
        type_tok = Token("TYPE", "category")
        name_tok: Token = items[0]
        label_text, label_pos = items[1]

        documentation, list_term = self._pick_doc_and_list(items[2:])
        return self._build_category(type_tok, name_tok, label_text, label_pos, list_term, documentation)

    def dimension_decl(self, meta: Any, items: List[Any]) -> DeclarationNode:
        # "dimension" NAME ":" label dimension_expression? doc?
        type_tok = Token("TYPE", "dimension")
        name_tok: Token = items[0]
        label_text, label_pos = items[1]

        documentation, expression = self._pick_doc_and_expr(items[2:])

        return self._build_dimension(type_tok, name_tok, label_text, label_pos, expression, documentation)

    def other_decl(self, kind: str, meta: Any, items: List[Any]) -> DeclarationNode:
        """
        Helper used by all 'simple' declaration rules that only have an
        optional docstring after the label.
        """
        type_token: Token = Token("TYPE", kind)
        name_token: Token = items[0]
        label_text, label_position = items[1]

        documentation: Optional[Documentation] = None
        for item in items[2:]:
            if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str):
                documentation = item  # type: ignore[assignment]
                break
        return self._build_other(type_token, name_token, label_text, label_position, documentation)

    # Specific wrappers that match grammar rule names:

    def member_decl(self, meta: Any, items: List[Any]) -> DeclarationNode:
        # BUGFIX: this must be 'member', not 'variable'
        return self.other_decl("member", meta, items)

    def variable_decl(self, meta: Any, items: List[Any]) -> DeclarationNode:
        return self.other_decl("variable", meta, items)

    def parameter_decl(self, meta: Any, items: List[Any]) -> DeclarationNode:
        return self.other_decl("parameter", meta, items)

    def equation_decl(self, meta: Any, items: List[Any]) -> DeclarationNode:
        return self.other_decl("equation", meta, items)

    def dimensions_decl(self, meta: Any, items: List[Any]) -> DeclarationNode:
        return self.other_decl("dimensions", meta, items)

    def domain_decl(self, meta: Any, items: List[Any]) -> DeclarationNode:
        # DeclType.domain existed, but the transformer previously lacked this entry point.
        return self.other_decl("domain", meta, items)

    # ---- builders ----

    def _build_dimension(
        self,
        type_token: Token,
        name_token: Token,
        label_text: str,
        label_position: SourcePosition,
        expr: Optional[DimensionExpression],
        documentation: Optional[Documentation],
    ) -> DimensionDeclaration:
        type_position = self._position(type_token)
        name_position = self._position(name_token)
        name_str = str(name_token)

        # Evaluate the expression (or empty -> [])
        members: List[str] = self._evaluate_dimension_expression(expr) if expr else []

        # Check category membership constraints (must exist and be single category)
        missing: List[str] = [m for m in members if m not in self._member_category]
        if missing:
            raise ValueError(
                f"Dimension '{name_str}' lists members not assigned to any category: "
                f"{', '.join(sorted(missing))}. Declare a category including these members before this dimension."
            )

        cats = {self._member_category[m] for m in members}
        if len(cats) > 1:
            cats_str = ", ".join(sorted(cats))
            raise ValueError(
                f"Dimension '{name_str}' mixes members from multiple categories: {cats_str}"
            )

        node = DimensionDeclaration(
            declaration_type=DeclarationType.dimension,
            type_position=type_position,
            name=name_str,
            name_position=name_position,
            label=label_text,
            label_position=label_position,
            documentation=documentation[0] if documentation else None,
            documentation_position=documentation[1] if documentation else None,
            dimension_members=members,
        )
        # Register for future references
        self._declared_dimensions[name_str] = members
        return node

    def _build_category(
        self,
        type_token: Token,
        name_token: Token,
        label_text: str,
        label_position: SourcePosition,
        list_term: Optional[DimensionTerm],
        documentation: Optional[Documentation],
    ) -> CategoryDeclaration:
        type_position = self._position(type_token)
        name_position = self._position(name_token)
        name_str = str(name_token)

        members: List[str] = []
        if list_term is not None:
            tag, payload = list_term
            assert tag == "list"
            for token in payload:  # payload is List[Token]
                reference_name = str(token)
                if reference_name not in self._declared_members:
                    raise ValueError(
                        f"Undefined member '{reference_name}' referenced by category '{name_str}' "
                        f"at {token.line}:{token.column} — members must be declared earlier"
                    )
                if reference_name in self._member_category:
                    prev_cat = self._member_category[reference_name]
                    raise ValueError(
                        f"Member '{reference_name}' is already in category '{prev_cat}' "
                        f"and cannot also be in '{name_str}' (at {token.line}:{token.column})"
                    )
                self._member_category[reference_name] = name_str
                members.append(reference_name)

        node = CategoryDeclaration(
            declaration_type=DeclarationType.category,
            type_position=type_position,
            name=name_str,
            name_position=name_position,
            label=label_text,
            label_position=label_position,
            documentation=documentation[0] if documentation else None,
            documentation_position=documentation[1] if documentation else None,
            dimension_members=members,
        )
        self._declared_dimensions[name_str] = members
        return node

    def _build_other(
        self,
        type_token: Token,
        name_token: Token,
        label_text: str,
        label_position: SourcePosition,
        documentation: Optional[Documentation],
    ) -> DeclarationNode:
        type_text: str = str(type_token)
        if type_text != type_text.lower():
            raise ValueError(
                f"Declaration type must be lower-case, found '{type_text}' "
                f"at {type_token.line}:{type_token.column}"
            )
        # Map to DeclType
        try:
            declaration_type = DeclarationType(type_text)
        except ValueError as exc:
            raise ValueError(
                f"Unknown declaration type '{type_text}' at {type_token.line}:{type_token.column}"
            ) from exc

        type_position = self._position(type_token)
        name_position = self._position(name_token)
        name_str = str(name_token)

        if declaration_type == DeclarationType.member:
            if name_str in self._declared_members:
                raise ValueError(
                    f"Duplicate member declaration '{name_str}' at {name_position.line}:{name_position.column}"
                )
            self._declared_members.add(name_str)
            return MemberDeclaration(
                declaration_type=declaration_type,
                type_position=type_position,
                name=name_str,
                name_position=name_position,
                label=label_text,
                label_position=label_position,
                documentation=documentation[0] if documentation else None,
                documentation_position=documentation[1] if documentation else None,
            )

        if declaration_type == DeclarationType.dimensions:
            return DimensionsDeclaration(
                declaration_type=declaration_type,
                type_position=type_position,
                name=name_str,
                name_position=name_position,
                label=label_text,
                label_position=label_position,
                documentation=documentation[0] if documentation else None,
                documentation_position=documentation[1] if documentation else None,
            )

        if declaration_type == DeclarationType.domain:
            return DomainDeclaration(
                declaration_type=declaration_type,
                type_position=type_position,
                name=name_str,
                name_position=name_position,
                label=label_text,
                label_position=label_position,
                documentation=documentation[0] if documentation else None,
                documentation_position=documentation[1] if documentation else None,
            )

        if declaration_type == DeclarationType.parameter:
            return ParameterDeclaration(
                declaration_type=declaration_type,
                type_position=type_position,
                name=name_str,
                name_position=name_position,
                label=label_text,
                label_position=label_position,
                documentation=documentation[0] if documentation else None,
                documentation_position=documentation[1] if documentation else None,
            )

        if declaration_type == DeclarationType.variable:
            return VariableDeclaration(
                declaration_type=declaration_type,
                type_position=type_position,
                name=name_str,
                name_position=name_position,
                label=label_text,
                label_position=label_position,
                documentation=documentation[0] if documentation else None,
                documentation_position=documentation[1] if documentation else None,
            )

        if declaration_type == DeclarationType.equation:
            return EquationDeclaration(
                declaration_type=declaration_type,
                type_position=type_position,
                name=name_str,
                name_position=name_position,
                label=label_text,
                label_position=label_position,
                documentation=documentation[0] if documentation else None,
                documentation_position=documentation[1] if documentation else None,
            )

        raise AssertionError(f"Unhandled declaration type: {declaration_type}")

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
        return [x for x in base if x not in remove_set]

    def _eval_dimension_term(self, term: DimensionTerm, owner_dim: str) -> List[str]:
        tag, payload = term
        if tag == "list":
            return self._validate_member_tokens(payload, f"dimension '{owner_dim}'")
        if tag == "dimension reference":
            ref_name, ref_pos = payload
            if ref_name not in self._declared_dimensions:
                raise ValueError(
                    f"Dimension '{owner_dim}' references unknown dimension '{ref_name}' "
                    f"at {ref_pos.line}:{ref_pos.column}. Dimensions must be declared earlier to be referenced."
                )
            return list(self._declared_dimensions[ref_name])
        raise AssertionError(f"Unknown dim term tag: {tag}")

    def _evaluate_dimension_expression(self, expr: Optional[DimensionExpression]) -> List[str]:
        """
        Evaluate a dimension expression into a list of member names.
        """
        if expr is None:
            return []
        tag, first, ops = expr
        assert tag == "dimension_expression"
        # Start from first term
        result: List[str] = list(self._eval_dimension_term(first, owner_dim="(evaluating)"))
        # Apply operations in order
        for op, term in ops:
            values = self._eval_dimension_term(term, owner_dim="(evaluating)")
            if op == "+":
                result = self._union_preserving(result, values)
            elif op == "-":
                result = self._subtract(result, values)
            else:
                raise AssertionError(f"Unknown operator {op}")
        return result

    def dimension_term(self, meta: Any, items: List[Any]) -> DimensionTerm:
        # Just forward the inner DimensionTerm (from name_list or dimension_reference)
        assert len(items) == 1
        return items[0]

    # ---- top-level rule ----

    def start(self, meta: Any, items: List[DeclarationNode]) -> Program:
        # Final constraint: all declared members must be assigned to a category
        unassigned = [m for m in self._declared_members if m not in self._member_category]
        if unassigned:
            raise ValueError(
                "All members must be in a category, but the following member(s) are not assigned: "
                + ", ".join(sorted(unassigned))
            )
        return Program(declarations=items)


# ========= Friendly error printing =========

def _safe_line_extract(src: str, line_no: int) -> str:
    lines: List[str] = src.splitlines()
    return lines[line_no - 1] if 1 <= line_no <= len(lines) else ""


def _underline_column(line_text: str, column: int) -> str:
    _ = line_text.expandtabs(4)
    prefix_expanded: str = line_text[: max(column - 1, 0)].expandtabs(4)
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
        # Fall back to simpler reporting
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


# ========= Parser wiring & CLI =========

def build_parser(grammar_file: pathlib.Path) -> Lark:
    """
    Build a Lark parser from the given grammar file.
    """
    return Lark.open(grammar_file, parser="lalr")


def parse_decls(parser: Lark, text: str) -> Program:
    """
    Parse the given source text into a Program AST.
    """
    tree: Tree = parser.parse(text)
    # ToAST.start returns a Program, so this cast is safe.
    return ToAST().transform(tree)  # type: ignore[return-value]


def main() -> int:
    cli = argparse.ArgumentParser(
        description="Parse declarations from a .sym file and print the AST.",
    )
    cli.add_argument("grammar", type=pathlib.Path, help="Path to the .lark grammar file.")
    cli.add_argument("input", type=pathlib.Path, help="Path to the .sym model file.")
    cli.add_argument(
        "--format",
        choices=("tree", "summary"),
        default="summary",
        help="Choose 'tree' for a full AST tree or 'summary' for one line per declaration.",
    )
    cli.add_argument(
        "--show-pos",
        action="store_true",
        help="Include line/column position fields in the output.",
    )
    args = cli.parse_args()

    try:
        parser = build_parser(args.grammar)
    except Exception as exc:
        sys.stderr.write(f"Failed to build parser from {args.grammar}: {exc}\n")
        return 1

    try:
        text = args.input.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"Failed to read input file {args.input}: {exc}\n")
        return 1

    try:
        program = parse_decls(parser, text)
    except UnexpectedInput as err:
        print_parse_error(err, text, args.input)
        return 1

    if args.format == "tree":
        output: str = abstract_syntax_tree_to_text(program, show_pos=args.show_pos)
    else:
        output = program_to_summary_text(program, show_pos=args.show_pos)

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
