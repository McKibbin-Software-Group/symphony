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
    Summation,
    TupleCondition,
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
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
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
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        names: NameList = children[0]
        return NameList(position=position, kind="member", items=names.items)

    def dimension_list(self, meta: Any, children: List[Token]) -> NameList:
        """
        ### Overview
        
        Dimension list handler.
        """
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        names: NameList = children[0]
        return NameList(position=position, kind="dimension", items=names.items)

    # ---------- rule handlers ----------

    def label(self, meta: Any, children: List[Token]) -> StringWithPosition:
        token: Token = children[0]
        value: str = self.parse_escaped_string(token)
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=token)
        return StringWithPosition(value=value, position=position)

    def documentation(self, meta: Any, children: List[Token]) -> StringWithPosition:
        token: Token = children[0]
        value: str = self.triple_string_value(token)
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=token)
        return StringWithPosition(value=value, position=position)

    # ---------- dimension expression handlers ----------

    def dimension_reference(self, meta: Any, children: List[Token]) -> DimensionReference:
        token: Token = children[0]
        referenced_dimension: str = token.value
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        return DimensionReference(position=position, referenced_dimension=referenced_dimension)

    def dimension_term(self, meta: Any, child: Any) -> Any:
        # The grammar typically routes either member_list or dimension_reference here.
        return child

    def dimension_expression(self, meta: Any, first_term: Any, *rest: Any) -> DimensionExpression:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        first: Any = first_term
        if isinstance(first_term, tuple):
            first = DimensionListTerm(position=position, members=tuple(str(x) for x in first_term))
        rest_pairs: List[Tuple[str, Any]] = []
        # rest arrives as (op, term, op, term, ...)
        i: int = 0
        rest_items: Tuple[Any, ...] = tuple(rest)
        while i + 1 < len(rest_items):
            operator_token: Any = rest_items[i]
            term_value: Any = rest_items[i + 1]
            operator: str = str(operator_token)
            term_node: Any
            if isinstance(term_value, tuple):
                term_node = DimensionListTerm(position=position, members=tuple(str(x) for x in term_value))
            else:
                term_node = term_value
            rest_pairs.append((operator, term_node))
            i += 2
        return DimensionExpression(position=position, first=first, rest=tuple(rest_pairs))


    # ---------- domain expression handlers ----------

    def domain_list(self, meta: Any, children: List[Token]) -> NameList:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        # logging.debug(f"domain_list children: {children}")
        # exit("Domain List handler")
        if isinstance(children, list):
            # Heuristic: name_list returns tuple[str,...]; member_list also returns tuple[str,...].
            # We cannot distinguish reliably here; later passes can resolve using symbol tables.
            return NameList(position=position, kind="names", items=tuple(str(x) for x in children))
        if isinstance(children, NameList):
            return children
        raise TypeError(f"Unexpected domain_list child type: {type(children)}")

    def tuple_condition(self, meta: Any, children: List[Token]) -> TupleCondition:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        return TupleCondition(
            position=position,
            left_position=int(str(children[0])),
            operator=str(children[1]),
            right_position=int(str(children[2])),
        )

    def tuple_conditions(self, meta: Any, *children: Any) -> Tuple[TupleCondition, ...]:
        conditions: List[TupleCondition] = [c for c in children if isinstance(c, TupleCondition)]
        return tuple(conditions)

    def domain_term(self, meta: Any, domain_list: NameList, tuple_conditions: Optional[Tuple[TupleCondition, ...]] = None) -> DomainTerm:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        return DomainTerm(position=position, domain_list=domain_list, tuple_conditions=tuple_conditions or ())

    def domain_expression(self, meta: Any, first_term: DomainTerm, *rest: Any) -> DomainExpression:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        rest_pairs: List[Tuple[str, DomainTerm]] = []
        rest_items: Tuple[Any, ...] = tuple(rest)
        i: int = 0
        while i + 1 < len(rest_items):
            operator: str = str(rest_items[i])
            term: DomainTerm = rest_items[i + 1]
            rest_pairs.append((operator, term))
            i += 2
        return DomainExpression(position=position, first=first_term, rest=tuple(rest_pairs))

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
        documentation: StringWithPosition = children[3] if len(children) == 4 else None

        return MemberDeclaration(
            position=position,
            declaration_type=DeclarationType.member,
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
        members: NameList = children[3]
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
    
    def domain_declaration(
        self, meta: Any, children: List[Any]
    ) -> DomainDeclaration:
        """
        ### Overview

        Domain declaration handler.
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
            declaration_type=DeclarationType.unit,
            name=name,
            label=label,
            documentation=documentation,
        )
    
    def parameter_declaration(self, meta: Any, children: List[Any]) -> ParameterDeclaration:    
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        name: str = self.get_name(children[1])
        label: StringWithPosition = children[2]

        return ParameterDeclaration(
            position=position,
            declaration_type=DeclarationType.parameter,
            name=name,
            label=label,
            domain_expression=None,
            unit=None,
            documentation=None,
        )

    def variable_declaration(self, meta: Any, children: List[Any]) -> VariableDeclaration:    
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        name: str = self.get_name(children[1])
        label: StringWithPosition = children[2]

        return VariableDeclaration(
            position=position,
            declaration_type=DeclarationType.variable,
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
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        unit_reference: UnitReference = children[1]
        return UnitSpecification(position=position, unit_name=unit_reference.referenced_unit)

    def unit_reference(self, meta: Any, children: List[Token]) -> UnitReference:
        token: Token = children[0]
        referenced_unit: str = token.value
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        return UnitReference(position=position, referenced_unit=referenced_unit)

    def deviation_unit(self, meta: Any, children: List[Any]) -> DeviationUnitSpecification:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        unit_reference: UnitReference = children[1]
        return DeviationUnitSpecification(position=position, deviation_unit_name=unit_reference.referenced_unit)

    def logged(self, meta: Any, children: List[Any]) -> bool:
        return bool(children[1])

    def intertemporal(self, meta: Any, children: List[Any]) -> bool:
        return bool(children[1])

    # ---------------------------------------------------------------------
    # Equation declaration
    # ---------------------------------------------------------------------

    def equation_declaration(self, meta: Any, children: List[Any]) -> EquationDeclaration:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)       
        return EquationDeclaration(
            position=position,
            declaration_type=DeclarationType.equation,
            label=None,
            domain_expression=None,
            equation_expression=None,
            documentation=None,
        )


    def equation_declaration(
        self,
        meta: Any,
        _kw: Any,
        _colon: Any,
        label: StringWithPosition,
        domain_expression: Optional[DomainExpression],
        equation_expression: EquationExpression,
        documentation: Optional[StringWithPosition] = None,
    ) -> EquationDeclaration:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        return EquationDeclaration(
            position=position,
            declaration_type=DeclarationType.equation,
            label=label,
            domain_expression=domain_expression,
            equation_expression=equation_expression,
            documentation=documentation,
        )

    # ---------------------------------------------------------------------
    # Variable references (lhs / rhs)
    # ---------------------------------------------------------------------

    def lhs_variable_reference(self, meta: Any, name_token: Token, domain_expression: Optional[DomainExpression] = None) -> LhsVariableReference:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=name_token)
        return LhsVariableReference(position=position, name=str(name_token), domain_expression=domain_expression)

    def rhs_domain_restriction(self, meta: Any, _dom: Any, _equals: Any, domain_expression: DomainExpression) -> Tuple[str, DomainExpression]:
        return ("dom", domain_expression)

    def tuple_position_list(self, meta: Any, *children: Any) -> Tuple[Tuple[str, int], ...]:
        # pattern: dimension_reference ":" TUPLE_POSITION ("," dimension_reference ":" TUPLE_POSITION)*
        result: List[Tuple[str, int]] = []
        items: List[Any] = list(children)
        i: int = 0
        while i + 2 < len(items):
            dimension_term: Any = items[i]
            tuple_position: Any = items[i + 2]
            dimension_name: str
            if isinstance(dimension_term, DimensionReference):
                dimension_name = dimension_term.referenced_dimension
            elif isinstance(dimension_term, Token):
                dimension_name = str(dimension_term)
            else:
                dimension_name = str(dimension_term)
            result.append((dimension_name, int(str(tuple_position))))
            i += 3
        return tuple(result)

    def rhs_dimension_matches(self, meta: Any, _dim: Any, _equals: Any, positions: Tuple[Tuple[str, int], ...]) -> Tuple[str, Tuple[Tuple[str, int], ...]]:
        return ("dim", positions)

    def rhs_aggregation_matches(self, meta: Any, _agg: Any, _equals: Any, positions: Tuple[Tuple[str, int], ...]) -> Tuple[str, Tuple[Tuple[str, int], ...]]:
        return ("agg", positions)

    def rhs_variable_reference(self, meta: Any, name_token: Token, conditionals: Optional[Sequence[Any]] = None) -> VariableReference:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=name_token)
        domain_expression: Optional[DomainExpression] = None
        dimension_matches: Optional[Tuple[Tuple[str, int], ...]] = None
        aggregation_matches: Optional[Tuple[Tuple[str, int], ...]] = None

        if conditionals:
            for conditional in conditionals:
                if isinstance(conditional, tuple) and conditional and conditional[0] == "dom":
                    domain_expression = conditional[1]
                if isinstance(conditional, tuple) and conditional and conditional[0] == "dim":
                    dimension_matches = tuple(conditional[1])
                if isinstance(conditional, tuple) and conditional and conditional[0] == "agg":
                    aggregation_matches = tuple(conditional[1])

        return VariableReference(
            position=position,
            name=str(name_token),
            domain_expression=domain_expression,
            dimension_matches=dimension_matches,
            aggregation_matches=aggregation_matches,
        )

    # ---------------------------------------------------------------------
    # LHS wrappers
    # ---------------------------------------------------------------------

    def lhs_wrapped_variable(self, meta: Any, child: Any) -> Any:
        return child

    def lhs_expectation(self, meta: Any, _e: Any, _lparen: Any, inner: Any, _rparen: Any) -> LhsExpectation:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        return LhsExpectation(position=position, inner=inner)

    def lhs_lead(self, meta: Any, _lead: Any, _lparen: Any, inner: Any, _comma_or_rparen: Any = None, lead_amount: Optional[Token] = None, _rparen: Any = None) -> LhsLead:
        """
        The grammar variants seen during development differ slightly. This method is tolerant:
          - lead(lhs_wrapped_variable, INT)
          - lead(lhs_wrapped_variable)
        """
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        amount: int = 1
        if lead_amount is not None and isinstance(lead_amount, Token):
            amount = int(str(lead_amount))
        return LhsLead(position=position, inner=inner, lead_amount=amount)

    def lhs_wrapped_variable_reference(self, meta: Any, reference: LhsVariableReference) -> LhsWrappedVariable:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        return LhsWrappedVariable(position=position, reference=reference)

    # ---------------------------------------------------------------------
    # Equation root
    # ---------------------------------------------------------------------

    def equality_expression(self, meta: Any, lhs: Any, _equals: Any, rhs: Any) -> EquationExpression:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        if isinstance(lhs, LhsVariableReference):
            lhs_wrapped: Any = LhsWrappedVariable(position=lhs.position, reference=lhs)
        else:
            lhs_wrapped = lhs
        return EquationExpression(position=position, lhs=lhs_wrapped, rhs=rhs)

    def equation_expression(self, meta: Any, child: EquationExpression) -> EquationExpression:
        return child

    # ---------------------------------------------------------------------
    # Expression grammar
    # ---------------------------------------------------------------------

    def atom(self, meta: Any, child: Any) -> Any:
        return child

    def rhs_expectation(self, meta: Any, _e: Any, _lparen: Any, variable: VariableReference, _rparen: Any) -> Expectation:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        return Expectation(position=position, reference=variable)

    def function(self, meta: Any, function_name_token: Token, _lparen: Any, argument: Any, _rparen: Any) -> FunctionCall:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=function_name_token)
        return FunctionCall(position=position, function_name=str(function_name_token), argument=argument)

    def summation(self, meta: Any, _sum: Any, _lparen: Any, dimension: DimensionReference, _bar: Any, body: Any, _rparen: Any) -> Summation:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        return Summation(position=position, dimension_name=dimension.referenced_dimension, body=body)

    def product(self, meta: Any, _prod: Any, _lparen: Any, dimension: DimensionReference, _bar: Any, body: Any, _rparen: Any) -> Product:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        return Product(position=position, dimension_name=dimension.referenced_dimension, body=body)

    def number_literal(self, meta: Any, value: float) -> NumberLiteral:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        return NumberLiteral(position=position, value=value)

    def boolean_literal(self, meta: Any, value: bool) -> BooleanLiteral:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        return BooleanLiteral(position=position, value=value)

    def rhs_variable_atom(self, meta: Any, reference: VariableReference) -> VariableExpression:
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=reference.position)
        return VariableExpression(position=position, reference=reference)

    def unary_expression(self, meta: Any, *children: Any) -> Any:
        # unary_expression: MINUS unary_expression | atom  (typical)
        if len(children) == 2 and str(children[0]) == "-":
            position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
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
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
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
            right = BinaryOperation(position=position, operator=operator_next, left=right, right=exponent_next)
            i += 2
        return BinaryOperation(position=position, operator=operator, left=child, right=right)

    def _fold_left(self, meta: Any, first: Any, rest: Sequence[Any]) -> Any:
        if not rest:
            return first
        position: SourcePosition = symphony_position(file_path=self.file_path, token_or_meta=meta)
        items: Tuple[Any, ...] = tuple(rest)
        expression: Any = first
        i: int = 0
        while i + 1 < len(items):
            operator: str = str(items[i])
            right: Any = items[i + 1]
            expression = BinaryOperation(position=position, operator=operator, left=expression, right=right)
            i += 2
        return expression

    # ---------------------------------------------------------------------
    # Root rules
    # ---------------------------------------------------------------------

    def declaration(self, meta: Any, child: Any) -> AnyDeclaration:
        return child

    def start(self, meta: Any, *children: Any) -> Tuple[AnyDeclaration, ...]:
        declarations: List[AnyDeclaration] = [c for c in children if c is not None]
        return tuple(declarations)


    # ---------- top-level rule ----------

    def start(self, meta: Any, children: List[AnyDeclaration]) -> Module:
        """
        Top-level grammar rule: wrap all declarations into a Program.
        No semantic checks here.
        """
        return Module(
            position=SourcePosition(file_path=self.file_path, line=1, column=1),
            declarations=children,
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
                        position=SourcePosition(file_path=symphony_file.file_path, line=1, column=1),
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