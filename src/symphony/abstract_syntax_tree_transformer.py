from __future__ import annotations

from dataclasses import dataclass
import logging
import ast
from pathlib import Path
from tkinter.font import names
from turtle import position
from typing import Any, Iterable, List, Optional, Sequence, Tuple
from lark import Discard, Token, UnexpectedInput, v_args
from symphony import (
    Diagnostic,
    DiagnosticBag,
    DiagnosticLabel,
    DiagnosticSeverity,
    SourcePosition,
    SymphonyDiagnosticsException,
    SymphonyFiles,
    errors,
    report_diagnostics,
    symphony_position,
)
from symphony.abstract_syntax_tree import (
    BinaryOperation,
    BooleanLiteral,
    DeclarationType,
    DeviationUnitReference,
    DeviationUnitSpecification,
    DimensionExpression,
    DimensionListTerm,
    DimensionReference,
    DimensionDeclaration,
    DomainDeclaration,
    DomainExpression,
    Expression,
    NameList,
    DomainTerm,
    EquationDeclaration,
    EquationExpression,
    Expectation,
    FunctionCall,
    LhsExpectation,
    LhsLead,
    LhsVariableReference,
    LhsWrappedVariable,
    Modules,
    AnyDeclaration,
    MemberDeclaration,
    CategoryDeclaration,
    Module,
    NumberLiteral,
    ParameterDeclaration,
    Product,
    StringWithPosition,
    DocumentationWithPosition,
    Summation,
    TupleCondition,
    TuplePosition,
    UnaryMinus,
    UnitDeclaration,
    UnitReference,
    UnitSpecification,
    VariableDeclaration,
    VariableExpression,
    VariableReference,
)
from symphony.base_transformer import BaseTransformer
from symphony.loader import Loader, LoaderResult

# Builds the Pass 1 parser and transformer for Symphony.
# It loads the packaged grammar, parses the model declaration into a Lark parse tree,
# and produces a raw abstract syntax tree without semantic validation; later passes
# handle ordering and cross-reference checks and other semantic analysis.


@v_args(meta=True)
class AbstractSyntaxTreeTransformer(BaseTransformer):
    """
    Pass 1: parse-tree → raw abstract syntax tree tokens, with no semantic validation.

    Responsibilities:
      - Build AST nodes for all top-level declarations.
      - Preserve dimension expressions in DimensionDeclaration.dimension_expression.
      - Do NOT:
          * check declaration order,
          * check that dimensions / categories / domains exist,
          * check category coverage or uniqueness,
          * check for duplicate names.
    """

    # ---------- leaf grammar rules ----------

    # ---------------------------------------------------------------------
    # Terminal helpers
    # ---------------------------------------------------------------------

    def boolean(self, meta: Any, token: Token) -> bool:
        text: str = str(token)
        return text.lower() == "true"

    def number(self, meta: Any, token: Token) -> float:
        return float(str(token))

    # ---------------------------------------------------------------------
    # Simple list rules
    # ---------------------------------------------------------------------

    def name_list(self, meta: Any, children: List[Token]) -> NameList:
        """
        ### Overview

        Name list handler.
        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        names: List[str] = []
        for child in children:
            if isinstance(child, Token) and child.type == "NAME":
                names.append(str(child.value))
            elif isinstance(child, str):
                names.append(child)
        return NameList(position=position, kind="name", items=tuple(names))

    def member_list(self, meta: Any, children: List[Token]) -> NameList:
        """
        ### Overview

        Member list handler.
        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        names: NameList = children[0]
        return NameList(position=position, kind="member", items=names.items)

    def dimension_list(self, meta: Any, children: List[Token]) -> NameList:
        """
        ### Overview

        Dimension list handler.
        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        names: NameList = children[0]
        return NameList(position=position, kind="dimension", items=names.items)

    # ---------- rule handlers ----------

    def label(self, meta: Any, children: List[Token]) -> StringWithPosition:
        token: Token = children[0]
        value: str = self.parse_escaped_string(token)
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=token
        )
        return StringWithPosition(value=value, position=position)

    def documentation(
        self, meta: Any, children: List[Token]
    ) -> DocumentationWithPosition:
        token: Token = children[0]
        value: str = self.triple_string_value(token)
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=token
        )
        return DocumentationWithPosition(value=value, position=position)

    # ---------- dimension expression handlers ----------

    def dimension_reference(
        self, meta: Any, children: List[Token]
    ) -> DimensionReference:
        token: Token = children[0]
        referenced_dimension: str = token.value
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return DimensionReference(position=position, dimension=referenced_dimension)

    def dimension_term(self, meta: Any, child: Any) -> Any:
        # The grammar typically routes either member_list or dimension_reference here.
        return child

    def dimension_expression(
        self, meta: Any, children: List[Any]
    ) -> DimensionExpression:
        """
        ### Overview
        Dimension expression handler.
        
        The children are a list of either member lists (NameList) or dimension references (DimensionReference),
        combined using '+' and '-' operators (Tokens).
        
        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return DimensionExpression(
            position=position, elements=tuple(children)
        )

    # ---------- domain expression handlers ----------

    def domain_list(self, meta: Any, children: List[Any]) -> NameList:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        names: NameList = children[0]
        return NameList(position=position, kind="domain", items=names.items)

    def tuple_condition(self, meta: Any, children: List[Token]) -> TupleCondition:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return TupleCondition(
            position=position,
            left_position=int(str(children[0])),
            operator=str(children[1]),
            right_position=int(str(children[2])),
        )

    def tuple_conditions(
        self, meta: Any, children: List[Any]
    ) -> Tuple[TupleCondition, ...]:
        conditions: List[TupleCondition] = [
            c for c in children if isinstance(c, TupleCondition)
        ]
        return tuple(conditions)

    def domain_term(
        self,
        meta: Any,
        domain_list: NameList,
        tuple_conditions: Optional[Tuple[TupleCondition, ...]] = None,
    ) -> DomainTerm:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return DomainTerm(
            position=position,
            domain_list=domain_list,
            tuple_conditions=tuple_conditions or (),
        )

    def domain_expression(
        self, meta: Any, children: List[Any]
    ) -> DomainExpression:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        rest_pairs: List[Tuple[str, DomainTerm]] = []
        if len(children) > 1:
            rest_items: Tuple[Any, ...] = tuple(children[1:])
            i: int = 0
            while i + 1 < len(rest_items):
                operator: str = str(rest_items[i])
                term: DomainTerm = rest_items[i + 1]
                rest_pairs.append((operator, term))
                i += 2
        return DomainExpression(
            position=position, first=children[0], rest=tuple(rest_pairs)
        )

    # ---------- declaration rules ----------
    def get_name(self, token: Token) -> str:
        """
        ### Overview

        Extract name from a NAME token.

        ### Exceptions
        Raises an assertion error if the token is not a NAME token.
        """
        assert (
            isinstance(token, Token) and token.type == "NAME"
        ), "Expected a NAME token"
        return token.value

    def get_label(self, label_with_position: StringWithPosition) -> str:
        """
        ### Overview

        Extract label string generated by the `label` grammar rule.

        ### Exceptions
        Raises an assertion error if the label child is not a string.
        """
        assert isinstance(label_with_position, tuple) and isinstance(
            label_with_position[0], str
        ), "Expected a label string"
        return label_with_position[0]

    def include_declaration(self, meta: Any, children: List[Any]) -> MemberDeclaration:
        """
        ### Overview

        Include declaration handler.
        """
        return Discard

    def member_declaration(self, meta: Any, children: List[Any]) -> MemberDeclaration:
        """
        ### Overview

        Member declaration handler.
        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        name: str = self.get_name(children[1])
        label: StringWithPosition = children[2]
        documentation: DocumentationWithPosition = (
            children[3] if len(children) == 4 else None
        )

        return MemberDeclaration(
            position=position,
            name=name,
            label=label,
            documentation=documentation,
        )

    def category_declaration(
        self, meta: Any, children: List[Any]
    ) -> CategoryDeclaration:
        """
        ### Overview

        Category declaration handler.
        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        name: str = self.get_name(children[1])
        label: StringWithPosition = children[2]
        members_name_list: NameList = children[3]
        members: Tuple[str, ...] = members_name_list.items
        documentation: StringWithPosition = children[4] if len(children) == 5 else None
        return CategoryDeclaration(
            position=position,
            name=name,
            label=label,
            documentation=documentation,
            members=members,
        )

    def dimension_declaration(
        self, meta: Any, children: List[Any]
    ) -> DimensionDeclaration:
        """
        ### Overview

        Dimension declaration handler.
        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        name: str = self.get_name(children[1])
        label: StringWithPosition = children[2]
        dimension_expression = children[3]
        documentation = children[4] if len(children) == 5 else None
        return DimensionDeclaration(
            position=position,
            name=name,
            label=label,
            documentation=documentation,
            expression=dimension_expression,
        )

    def domain_declaration(self, meta: Any, children: List[Any]) -> DomainDeclaration:
        """
        ### Overview

        Domain declaration handler.
        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        name: str = self.get_name(children[1])
        label: StringWithPosition = children[2]
        domain_expression = children[3]
        documentation = children[4] if len(children) == 5 else None
        return DomainDeclaration(
            position=position,
            name=name,
            label=label,
            documentation=documentation,
            expression=domain_expression,
        )

    def unit_declaration(self, meta: Any, children: List[Any]) -> UnitDeclaration:
        """
        ### Overview

        Member declaration handler.
        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        name: str = self.get_name(children[1])
        label: StringWithPosition = children[2]
        documentation: StringWithPosition = children[3] if len(children) == 4 else None

        return UnitDeclaration(
            position=position,
            name=name,
            label=label,
            documentation=documentation,
        )

    def parameter_declaration(
        self, meta: Any, children: List[Any]
    ) -> ParameterDeclaration:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        name: str = self.get_name(children[1])
        label: StringWithPosition = children[2]

        return ParameterDeclaration(
            position=position,
            name=name,
            label=label,
            domain_expression=None,
            unit=None,
            documentation=None,
        )

    def variable_declaration(
        self, meta: Any, children: List[Any]
    ) -> VariableDeclaration:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        name: str = self.get_name(children[1])
        label: StringWithPosition = children[2]

        return VariableDeclaration(
            position=position,
            name=name,
            label=label,
            domain_expression=None,
            unit=None,
            deviation_unit=None,
            logged=False,
            intertemporal=False,
            documentation=None,
        )

    def unit(self, meta: Any, children: List[Any]) -> UnitSpecification:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        unit_reference: UnitReference = children[1]
        return UnitSpecification(position=position, unit_name=unit_reference.unit)

    def unit_reference(self, meta: Any, children: List[Token]) -> UnitReference:
        token: Token = children[0]
        referenced_unit: str = token.value
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return UnitReference(position=position, unit=referenced_unit)

    def deviation_unit(
        self, meta: Any, children: List[Any]
    ) -> DeviationUnitSpecification:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        unit_reference: UnitReference = children[1]
        return DeviationUnitSpecification(
            position=position, deviation_unit_name=unit_reference.unit
        )

    def logged(self, meta: Any, children: List[Any]) -> bool:
        return bool(children[1])

    def intertemporal(self, meta: Any, children: List[Any]) -> bool:
        return bool(children[1])

    # ---------------------------------------------------------------------
    # Equation declaration
    # ---------------------------------------------------------------------

    def equation_declaration(
        self, meta: Any, children: List[Any]
    ) -> EquationDeclaration:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )

        remaining_children = children[1:]
        while len(remaining_children) > 0:
            first_child: Any = remaining_children[0]
            remaining_children = remaining_children[1:]

            label: StringWithPosition = StringWithPosition(value="", position=position)
            documentation = None
            equation_expression = None
            domain_expression = None
            if isinstance(first_child, StringWithPosition):
                label: StringWithPosition = first_child
            elif isinstance(first_child, DomainExpression):
                domain_expression: DomainExpression = first_child
            elif isinstance(first_child, EquationExpression):
                equation_expression: EquationExpression = first_child
            elif isinstance(first_child, DocumentationWithPosition):
                documentation: DocumentationWithPosition = first_child

        return EquationDeclaration(
            position=position,
            label=label,
            domain_expression=domain_expression,
            equation_expression=equation_expression,
            documentation=documentation,
        )

    # ---------------------------------------------------------------------
    # RHS Variables
    # ---------------------------------------------------------------------=

    def rhs_domain_restriction(
        self, meta: Any, children: List[Any]
    ) -> Tuple[str, DomainExpression]:
        assert isinstance(children[0], DomainExpression)
        domain_expression: DomainExpression = children[0]
        return ("domain restriction", domain_expression)

    def tuple_position(self, meta: Any, children: List[Any]) -> TuplePosition:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        dimension_reference: DimensionReference = children[0]
        tuple_position: int = children[1]
        return TuplePosition(
            position=position,
            dimension_reference=dimension_reference,
            tuple_position=int(str(tuple_position)),
        )

    def tuple_position_list(
        self, meta: Any, children: List[Any]
    ) -> Tuple[TuplePosition, ...]:
        return tuple(children)

    def rhs_dimension_matches(
        self, meta: Any, children: List[Any]
    ) -> Tuple[str, Tuple[TuplePosition]]:
        assert isinstance(children[0], tuple)
        tuple_positions: TuplePosition = children[0]
        return ("dimension tuple positions", tuple_positions)

    # _agg: Any, _equals: Any, positions: Tuple[Tuple[str, int], ...]
    def rhs_aggregation_matches(
        self, meta: Any, children: List[Any]
    ) -> Tuple[str, Tuple[TuplePosition]]:
        assert isinstance(children[0], tuple)
        tuple_positions: TuplePosition = children[0]
        return ("aggregation tuple positions", tuple_positions)

    # name_token: Token, conditionals: Optional[Sequence[Any]] = None
    def rhs_variable_reference(
        self, meta: Any, children: List[Any]
    ) -> VariableReference:
        """
        rhs_variable_reference: NAME ["(" rhs_variable_conditional ("," rhs_variable_conditional)* ")" ]
        """
        name_token: Token = children[0]
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        variable_name: str = name_token.value
        for child in children[1:]:
            if isinstance(child, tuple) and isinstance(child[0], str):
                match child[0]:
                    case "domain restriction":
                        domain_expression: DomainExpression = child[1]
                    case "dimension tuple positions":
                        dimension_matches: Tuple[TuplePosition, ...] = tuple(child[1])
                    case "aggregation tuple positions":
                        aggregation_matches: Tuple[TuplePosition, ...] = tuple(child[1])
        domain_expression: Optional[DomainExpression] = None
        dimension_matches: Optional[Tuple[TuplePosition, ...]] = None
        aggregation_matches: Optional[Tuple[TuplePosition, ...]] = None

        return VariableReference(
            position=position,
            name=variable_name,
            domain_expression=domain_expression,
            dimension_matches=dimension_matches,
            aggregation_matches=aggregation_matches,
        )

    # ---------------------------------------------------------------------
    # LHS variables and wrappers
    # ---------------------------------------------------------------------

    def lhs_variable_reference(
        self, meta: Any, children: List[Any]
    ) -> LhsVariableReference:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        name_token: Token = children[0]
        domain_expression: Optional[DomainExpression] = (
            children[1] if len(children) > 1 else None
        )
        return LhsVariableReference(
            position=position,
            name=self.get_name(name_token),
            domain_expression=domain_expression,
        )

    def lhs_wrapped_variable(self, meta: Any, children: List[Any]) -> Any:
        """
        ### Overview
        LHS wrapped variable handler.

        Given a wrapped variable, return the inner LHS variable reference.

        """
        assert len(children) == 1
        return children[0]

    # _e: Any, _lparen: Any, inner: Any, _rparen: Any
    def lhs_expectation(self, meta: Any, children: List[Any]) -> LhsVariableReference:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        logging.debug(children)
        exit("debug lhs_expectation")
        lhs_variable_reference: LhsVariableReference = children[0]
        lhs_variable_reference.expectation = True
        return lhs_variable_reference

    def lhs_lead(
        self,
        meta: Any,
        children: List[Any],
    ) -> LhsVariableReference:
        """
        ### Overview

        LHS lead function handler.
        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        logging.debug(children)
        exit("debug lhs_lead")
        lhs_variable_reference: LhsVariableReference = children[0]
        lhs_variable_reference.lead = True
        return lhs_variable_reference

    def lhs_wrapped_variable_reference(
        self,
        meta: Any,
        children: List[Any],
    ) -> LhsVariableReference:
        """
        ### Overview

        TODO: Check if this can ever be reached when parsing
        files that conform to the Lark grammar.

        LHS wrapped variable reference handler.
        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return children[0]

    # ---------------------------------------------------------------------
    # Equation root
    # ---------------------------------------------------------------------

    # meta: Any, lhs: Any, _equals: Any, rhs: Any
    def equality_expression(self, meta: Any, children: List[Any]) -> EquationExpression:

        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )

        if not isinstance(children, list) and len(children) == 3:
            self.diagnostics.add(
                Diagnostic(
                    code=errors.syntax_error,
                    severity=DiagnosticSeverity.error,
                    message=f"Missing left-hand side in an equality expression.",
                    primary_label=DiagnosticLabel(
                        position=position,
                        message="The error occurred near here.",
                        is_primary=True,
                    ),
                    help_text="Ensure that the equality expression has a left-hand side.",
                )
            )
            return Discard

        # Get the LHS of the equality expression
        lhs_variable_reference: LhsVariableReference = children[0]

        # Equality operator token is child 1.

        # Get the RHS of the equality expression
        rhs_expression: List[Any] = children[2:]
        return EquationExpression(
            position=position, lhs=lhs_variable_reference, rhs=rhs_expression
        )

    def equation_expression(
        self, meta: Any, child: EquationExpression
    ) -> EquationExpression:
        return child

    # ---------------------------------------------------------------------
    # Expression grammar
    # ---------------------------------------------------------------------

    def atom(self, meta: Any, child: Any) -> Any:
        return child

    def rhs_expectation(
        self,
        meta: Any,
        _e: Any,
        _lparen: Any,
        variable: VariableReference,
        _rparen: Any,
    ) -> Expectation:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return Expectation(position=position, reference=variable)

    def function(
        self,
        meta: Any,
        function_name_token: Token,
        _lparen: Any,
        argument: Any,
        _rparen: Any,
    ) -> FunctionCall:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=function_name_token
        )
        return FunctionCall(
            position=position, function_name=str(function_name_token), argument=argument
        )

    def summation(self, meta: Any, children: List[Any]) -> Summation:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        dimension: StringWithPosition = children[1]
        body: Tuple[Any] = tuple(children[2:])
        return Summation(position=position, dimension_name=dimension, body=body)

    def product(self, meta: Any, children: List[Any]) -> Product:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        dimension: StringWithPosition = children[1]
        body: Tuple[Any] = Tuple(children[2:])
        return Product(position=position, dimension_name=dimension, body=body)

    def number_literal(self, meta: Any, value: float) -> NumberLiteral:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return NumberLiteral(position=position, value=value)

    def boolean_literal(self, meta: Any, value: bool) -> BooleanLiteral:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return BooleanLiteral(position=position, value=value)

    def rhs_variable_atom(
        self, meta: Any, reference: VariableReference
    ) -> VariableExpression:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=reference.position
        )
        return VariableExpression(position=position, reference=reference)

    def unary_expression(self, meta: Any, *children: Any) -> Any:
        # unary_expression: MINUS unary_expression | atom  (typical)
        if len(children) == 2 and str(children[0]) == "-":
            position: SourcePosition = symphony_position(
                file_path=self.file_path, token_or_meta=meta
            )
            return UnaryMinus(position=position, operand=children[1])
        if len(children) == 1:
            return children[0]
        return children[-1]

    def sum_expression(self, meta: Any, first: Any, *rest: Any) -> Any:
        return self._fold_left(meta=meta, first=first, rest=rest)

    def product_expression(self, meta: Any, first: Any, *rest: Any) -> Any:
        return self._fold_left(meta=meta, first=first, rest=rest)

    def power_expression(self, meta: Any, child: Any, *rest: Any) -> Any:
        # If POWER operator exists, fold as right-associative; otherwise passthrough.
        if not rest:
            return child
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        # right associative: a ^ b ^ c = a ^ (b ^ c)
        rest_items: List[Any] = [child] + list(rest)
        # expecting pattern: base, op, exponent, op, exponent...
        operator: str = str(rest_items[1])
        right: Any = rest_items[2]
        # fold remaining to the right
        i: int = 3
        while i + 1 < len(rest_items):
            operator_next: str = str(rest_items[i])
            exponent_next: Any = rest_items[i + 1]
            right = BinaryOperation(
                position=position,
                operator=operator_next,
                left=right,
                right=exponent_next,
            )
            i += 2
        return BinaryOperation(
            position=position, operator=operator, left=child, right=right
        )

    def _fold_left(self, meta: Any, first: Any, rest: Sequence[Any]) -> Any:
        if not rest:
            return first
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        items: Tuple[Any, ...] = tuple(rest)
        expression: Any = first
        i: int = 0
        while i + 1 < len(items):
            operator: str = str(items[i])
            right: Any = items[i + 1]
            expression = BinaryOperation(
                position=position, operator=operator, left=expression, right=right
            )
            i += 2
        return expression

    # ---------------------------------------------------------------------
    # Root rules
    # ---------------------------------------------------------------------

    # def declaration(self, meta: Any, child: Any) -> AnyDeclaration:
    #     exit("debug declaration")
    #     return child

    # ---------- top-level rule ----------

    # def start(self, meta: Any, *children: Any) -> Tuple[AnyDeclaration, ...]:
    #     declarations: List[AnyDeclaration] = [child for child in children if child is not None]
    #     return tuple(declarations)

    def start(self, meta: Any, children: List[AnyDeclaration]) -> Module:
        """
        ### Overview

        Top-level grammar rule: wrap all declarations into a Program.
        No semantic checks here.
        """
        return Module(
            position=SourcePosition(file_path=self.file_path, line=1, column=1),
            declarations=tuple(children),
        )


# ---------- Create the abstract syntax tree for the whole model ---------


@dataclass(frozen=True)
class ASTLoaderResult:
    """
    This is the result returned by the abstract syntax tree loader.

    It supports both the loaded modules and any diagnostics encountered.
    """

    modules: Modules
    diagnostics: DiagnosticBag


def load_modules(loader_result: LoaderResult) -> ASTLoaderResult:
    """
    ### Overview

    Load a complete Symphony model from the given Lark parse trees.

    ### Arguments

    - `symphony_files`: The SymphonyFiles object containing all the Lark parse trees for the files that
    will be loaded into the abstract syntax tree.

    """

    modules: list[Module] = []
    diagnostics: DiagnosticBag = loader_result.diagnostics
    for symphony_file in loader_result.symphony_files.file_list:
        try:
            module: Module = AbstractSyntaxTreeTransformer(
                file_path=symphony_file.file_path,
                diagnostics=diagnostics,
            ).transform(symphony_file.tree)
            modules.append(module)
        except UnexpectedInput as err:
            # The module does not get added to the set of modules because it could not be transformed into an AST.
            # TODO: improve error reporting here - check for how this should be done to respond to error details in transformer.
            diagnostics.diagnostics.add(
                Diagnostic(
                    code=errors.syntax_error,
                    severity=DiagnosticSeverity.error,
                    message=f"Failed to parse Symphony file. {err}",
                    primary_label=DiagnosticLabel(
                        position=SourcePosition(
                            file_path=symphony_file.file_path, line=1, column=1
                        ),
                        message="Symphony error occurred here.",
                        is_primary=True,
                    ),
                    help_text="Check for errors near this location.",
                )
            )

    return ASTLoaderResult(
        modules=Modules(modules=tuple(modules)),
        diagnostics=diagnostics,
    )
