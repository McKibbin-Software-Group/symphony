from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple

from lark import Lark, Transformer, Token, Tree, v_args

from symphony.abstract_syntax_tree import (
    CategoryDeclaration,
    DeclarationNode,
    DeclarationType,
    DimensionDeclaration,
    DimensionExpression,
    DimensionTerm,
    DimensionsDeclaration,
    DomainDeclaration,
    DomainExpression,
    DomainTerm,
    EquationDeclaration,
    MemberDeclaration,
    ParameterDeclaration,
    Program,
    SourcePosition,
    VariableDeclaration,
)

# Builds the Pass 1 parser and transformer for Symphony.
# It loads the packaged grammar, parses the model declaration into a Lark parse tree,
# and produces a raw abstract syntax tree without semantic validation; later passes
# handle ordering and cross-reference checks and other semantic analysis.

# The content + position of a docstring for an entity.
Documentation = Tuple[str, SourcePosition]

@v_args(meta=True)
class ConvertToAbstractSyntaxTree(Transformer):
    """
    Pass 1: parse-tree → raw AST, with no semantic validation.

    Responsibilities:
      - Build AST nodes for all top-level declarations.
      - Preserve dimension expressions in DimensionDeclaration.dimension_expression.
      - Do NOT:
          * check declaration order,
          * check that dimensions / categories / domains exist,
          * check category coverage or uniqueness,
          * check for duplicate names.
    """

    # ---------- low-level helpers ----------

    @staticmethod
    def _position(token: Token) -> SourcePosition:
        return SourcePosition(line=token.line, column=token.column)

    @staticmethod
    def _parse_escaped_string(token: Token) -> str:
        """
        Convert an ESCAPED_STRING token into its Python string content.
        """
        # Token.value includes the quotes; strip and unescape.
        raw = token.value
        return raw[1:-1].encode("utf-8").decode("unicode_escape")

    # ---------- leaf grammar rules ----------

    def label(self, meta: Any, items: List[Token]) -> Tuple[str, SourcePosition]:
        assert len(items) == 1
        tok = items[0]
        return self._parse_escaped_string(tok), self._position(tok)

    def documentation(self, meta: Any, items: List[Token]) -> Documentation:
        assert len(items) == 1
        tok = items[0]
        text = tok.value[3:-3]  # strip leading and trailing """ of TRIPLE_STRING
        return text, self._position(tok)

    def name_list(self, meta: Any, items: List[Token]) -> DimensionTerm:
        # The grammar has "[ NAME (',' NAME)* ]"; here we see only NAME tokens.
        return ("list", list(items))

    def dimension_reference(self, meta: Any, items: List[Token]) -> DimensionTerm:
        assert len(items) == 1
        tok = items[0]
        name = tok.value
        pos = self._position(tok)
        return ("dimension reference", (name, pos))

    def dimension_expression(self, meta: Any, items: List[Any]) -> DimensionExpression:
        """
        Build a raw DimensionExpression:
            ("dimension_expression", first_term, [(op, term), ...])
        """
        if not items:
            empty: DimensionTerm = ("list", [])
            return ("dimension_expression", empty, [])

        first_term: DimensionTerm = items[0]
        rest: List[Tuple[str, DimensionTerm]] = []
        i = 1
        while i < len(items):
            op_token: Token = items[i]
            term: DimensionTerm = items[i + 1]
            rest.append((op_token.value, term))
            i += 2
        return ("dimension_expression", first_term, rest)

    def dimension_term(self, meta: Any, items: List[Any]) -> DimensionTerm:
        # Forward the term built by name_list or dimension_reference
        assert len(items) == 1
        return items[0]


    def domain_reference(self, meta: Any, items: List[Token]) -> DomainTerm:
        assert len(items) == 1
        tok = items[0]
        name = tok.value
        pos = self._position(tok)
        return ("domain reference", (name, pos))

    def domain_expression(self, meta: Any, items: List[Any]) -> DomainExpression:
        """
        Build a raw DomainExpression:
            ("domain_expression", first_term, [(op, term), ...])
        """
        if not items:
            empty: DomainTerm = ("list", [])
            return ("domain_expression", empty, [])

        first_term: DomainTerm = items[0]
        rest: List[Tuple[str, DomainTerm]] = []
        i = 1
        while i < len(items):
            op_token: Token = items[i]
            term: DomainTerm = items[i + 1]
            rest.append((op_token.value, term))
            i += 2
        return ("domain_expression", first_term, rest)

    def domain_term(self, meta: Any, items: List[Any]) -> DomainTerm:
        assert len(items) == 1
        return items[0]

    # ---------- declaration wrapper ----------

    def declaration(self, meta: Any, items: List[Any]) -> Any:
        # The 'declaration' rule just wraps a more specific *_decl rule.
        assert len(items) == 1
        return items[0]

    # ---------- helper extractors ----------

    @staticmethod
    def _pick_doc_and_expr(
        extra_items: List[Any],
    ) -> Tuple[Optional[Documentation], Optional[DimensionExpression]]:
        documentation: Optional[Documentation] = None
        expression: Optional[DimensionExpression] = None

        for item in extra_items:
            if not isinstance(item, tuple):
                continue
            # Dimension expressions are tagged by the first element.
            if (
                len(item) >= 1
                and isinstance(item[0], str)
                and item[0] == "dimension_expression"
            ):
                expression = item  # type: ignore[assignment]
            elif documentation is None and len(item) == 2 and isinstance(item[0], str):
                documentation = item  # type: ignore[assignment]

        return documentation, expression

    @staticmethod
    def _pick_doc_and_list(
        extra_items: List[Any],
    ) -> Tuple[Optional[Documentation], Optional[DimensionTerm]]:
        documentation: Optional[Documentation] = None
        list_term: Optional[DimensionTerm] = None

        for item in extra_items:
            if not isinstance(item, tuple):
                continue
            if list_term is None and len(item) >= 1 and item[0] == "list":
                list_term = item  # type: ignore[assignment]
            elif documentation is None and len(item) == 2 and isinstance(item[0], str):
                documentation = item  # type: ignore[assignment]

        return documentation, list_term

    # ---------- declaration rules ----------

    def category_declaration(self, meta: Any, items: List[Any]) -> DeclarationNode:
        # "category" NAME ":" label name_list doc?
        type_token = Token("TYPE", "category")
        name_token: Token = items[0]
        label_text, label_pos = items[1]
        documentation, list_term = self._pick_doc_and_list(items[2:])
        return self._build_category(
            type_token, name_token, label_text, label_pos, list_term, documentation
        )

    def dimension_declaration(self, meta: Any, items: List[Any]) -> DeclarationNode:
        # "dimension" NAME ":" label dimension_expression doc?
        type_token = Token("TYPE", "dimension")
        name_token: Token = items[0]
        label_text, label_pos = items[1]
        documentation, expression = self._pick_doc_and_expr(items[2:])
        return self._build_dimension(
            type_token, name_token, label_text, label_pos, expression, documentation
        )

    def other_declaration(self, kind: str, meta: Any, items: List[Any]) -> DeclarationNode:
        """
        Helper for declarations with just NAME ":" label doc?.
        """
        type_token = Token("TYPE", kind)
        name_token: Token = items[0]
        label_text, label_pos = items[1]

        documentation: Optional[Documentation] = None
        for item in items[2:]:
            if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str):
                documentation = item  # type: ignore[assignment]
                break

        return self._build_other(type_token, name_token, label_text, label_pos, documentation)

    # Rule-specific wrappers:

    def member_declaration(self, meta: Any, items: List[Any]) -> DeclarationNode:
        return self.other_declaration("member", meta, items)

    def parameter_declaration(self, meta: Any, items: List[Any]) -> DeclarationNode:
        return self.other_declaration("parameter", meta, items)

    def variable_declaration(self, meta: Any, items: List[Any]) -> DeclarationNode:
        return self.other_declaration("variable", meta, items)

    def equation_declaration(self, meta: Any, items: List[Any]) -> DeclarationNode:
        return self.other_declaration("equation", meta, items)

    def dimensions_declaration(self, meta: Any, items: List[Any]) -> DeclarationNode:
        type_token = Token("TYPE", "dimensions")
        name_token: Token = items[0]
        label_text, label_pos = items[1]
        documentation, list_term = self._pick_doc_and_list(items[2:])
        return self._build_dimensions(
            type_token, name_token, label_text, label_pos, list_term, documentation
        )
    


    def domain_declaration(self, meta: Any, items: List[Any]) -> DeclarationNode:
        # Domain expressions are not yet implemented in the grammar
        # beyond a placeholder, so we treat this like a simple decl.
        return self.other_declaration("domain", meta, items)

    # ---------- builders ----------

    def _build_dimension(
        self,
        type_token: Token,
        name_token: Token,
        label_text: str,
        label_position: SourcePosition,
        expression: Optional[DimensionExpression],
        documentation: Optional[Documentation],
    ) -> DimensionDeclaration:
        """
        Build a DimensionDeclaration without evaluating the expression.
        """
        type_position = self._position(type_token)
        name_position = self._position(name_token)
        name_str = name_token.value

        # Pass 1 leaves members empty; a later pass will fill them.
        empty_members: List[str] = []

        return DimensionDeclaration(
            declaration_type=DeclarationType.dimension,
            type_position=type_position,
            name=name_str,
            name_position=name_position,
            label=label_text,
            label_position=label_position,
            documentation=documentation[0] if documentation else None,
            documentation_position=documentation[1] if documentation else None,
            dimension_members=empty_members,
            dimension_expression=expression,
        )

    def _build_dimensions(
        self,
        type_token: Token,
        name_token: Token,
        label_text: str,
        label_position: SourcePosition,
        list_term: Optional[DimensionTerm],
        documentation: Optional[Documentation],
    ) -> DimensionsDeclaration:
        """
        Build a DimensionsDeclaration, preserving the dimension list syntactically.
        No dimensions-membership validation happens here.
        """
        type_position = self._position(type_token)
        name_position = self._position(name_token)
        name_str = name_token.value

        dimensions: List[str] = []
        if list_term is not None:
            tag, payload = list_term
            if tag != "list":
                raise ValueError("Internal error: expected list term for dimensions.")
            tokens: Iterable[Token] = payload
            dimensions = [tok.value for tok in tokens]

        return DimensionsDeclaration(
            declaration_type=DeclarationType.dimensions,
            type_position=type_position,
            name=name_str,
            name_position=name_position,
            label=label_text,
            label_position=label_position,
            documentation=documentation[0] if documentation else None,
            documentation_position=documentation[1] if documentation else None,
            tuples=[],
            dimensions=dimensions,
        )

    def _build_category(
        self,
        type_token: Token,
        name_token: Token,
        label_text: str,
        label_position: SourcePosition,
        list_term: Optional[DimensionTerm],
        documentation: Optional[Documentation],
    ) -> CategoryDeclaration:
        """
        Build a CategoryDeclaration, preserving the member list syntactically.
        No category-membership validation happens here.
        """
        type_position = self._position(type_token)
        name_position = self._position(name_token)
        name_str = name_token.value

        members: List[str] = []
        if list_term is not None:
            tag, payload = list_term
            if tag != "list":
                raise ValueError("Internal error: expected list term for category.")
            tokens: Iterable[Token] = payload
            members = [tok.value for tok in tokens]

        return CategoryDeclaration(
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

    def _build_other(
        self,
        type_token: Token,
        name_token: Token,
        label_text: str,
        label_position: SourcePosition,
        documentation: Optional[Documentation],
    ) -> DeclarationNode:
        """
        Build all other declaration types that do not carry expressions in Pass 1.
        """
        type_text = type_token.value
        if type_text != type_text.lower():
            raise ValueError(
                f"Declaration type must be lower-case, found '{type_text}' "
                f"at {type_token.line}:{type_token.column}"
            )

        try:
            declaration_type = DeclarationType(type_text)
        except ValueError as exc:
            raise ValueError(
                f"Unknown declaration type '{type_text}' at {type_token.line}:{type_token.column}"
            ) from exc

        type_position = self._position(type_token)
        name_position = self._position(name_token)
        name_str = name_token.value

        common_keyword_arguments = dict(
            declaration_type=declaration_type,
            type_position=type_position,
            name=name_str,
            name_position=name_position,
            label=label_text,
            label_position=label_position,
            documentation=documentation[0] if documentation else None,
            documentation_position=documentation[1] if documentation else None,
        )

        if declaration_type == DeclarationType.member:
            return MemberDeclaration(**common_keyword_arguments)  # type: ignore[arg-type]
        if declaration_type == DeclarationType.parameter:
            return ParameterDeclaration(**common_keyword_arguments)  # type: ignore[arg-type]
        if declaration_type == DeclarationType.variable:
            return VariableDeclaration(**common_keyword_arguments)  # type: ignore[arg-type]
        if declaration_type == DeclarationType.equation:
            return EquationDeclaration(**common_keyword_arguments)  # type: ignore[arg-type]
        if declaration_type == DeclarationType.dimensions:
            return DimensionsDeclaration(**common_keyword_arguments)  # type: ignore[arg-type]
        if declaration_type == DeclarationType.domain:
            return DomainDeclaration(**common_keyword_arguments)  # type: ignore[arg-type]

        raise AssertionError(f"Unhandled declaration type {declaration_type}")

    # ---------- top-level rule ----------

    def start(self, meta: Any, items: List[DeclarationNode]) -> Program:
        """
        Top-level grammar rule: wrap all declarations into a Program.
        No semantic checks here.
        """
        return Program(declarations=items)


# ---------- parser helpers for Pass 1 - creating the abstract syntax tree ---------

def build_parser(grammar_file: Path) -> Lark:
    """
    Build a Lark parser from the given grammar file.
    """
    return Lark.open(grammar_file, parser="lalr")


def parse_declarations(parser: Lark, text: str) -> Program:
    """
    Parse source text into a Program AST using the Pass 1 transformer.
    """
    tree: Tree = parser.parse(text)
    program: Program = ConvertToAbstractSyntaxTree().transform(tree)  # type: ignore[assignment]
    return program
