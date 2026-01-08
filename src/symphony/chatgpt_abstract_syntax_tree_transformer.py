from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

from lark import Token, Transformer, UnexpectedInput, v_args

from symphony import (
    Diagnostic,
    DiagnosticBag,
    DiagnosticLabel,
    DiagnosticSeverity,
    SourcePosition,
    SymphonyDiagnosticsException,
    SymphonyFiles,
    symphony_position,
    symphony_parser,
)

from symphony.base_transformer import BaseTransformer
from symphony.abstract_syntax_tree import (
    AnyDeclaration,
    BooleanLiteral,
    CategoryDeclaration,
    DeclarationType,
    DeviationUnitSpecification,
    DimensionDeclaration,
    DimensionExpression,
    DimensionListTerm,
    DimensionReference,
    DomainDeclaration,
    DomainExpression,
    NameList,
    DomainTerm,
    EquationDeclaration,
    EquationExpression,
    Expectation,
    FunctionCall,
    IncludeDeclaration,
    LhsExpectation,
    LhsLead,
    LhsVariableReference,
    LhsWrappedVariable,
    MemberDeclaration,
    Module,
    Modules,
    NumberLiteral,
    ParameterDeclaration,
    Product,
    StringWithPosition,
    Summation,
    TupleCondition,
    UnitDeclaration,
    UnitSpecification,
    VariableDeclaration,
    VariableExpression,
    VariableReference,
    UnaryMinus,
    BinaryOperation,
)


def _triple_string_value(token: Token) -> str:
    """
    Convert a TRIPLE_STRING token into its text content.

    The grammar uses a regex token like /\"\"\"(.|\n|\r)*?\"\"\"/.
    """
    raw: str = token.value
    if raw.startswith('"""') and raw.endswith('"""') and len(raw) >= 6:
        return raw[3:-3]
    return raw


@v_args(meta=True)
class AbstractSyntaxTreeTransformer(BaseTransformer):
    """
    Pass 1 transformer: parse tree -> raw AST nodes.

    This pass does not perform semantic validation (name resolution, ordering,
    domain expansion, etc.). Later passes should build symbol tables and derive
    resolved fields using dataclasses.replace helpers.
    """

    # ---------------------------------------------------------------------
    # Terminal helpers
    # ---------------------------------------------------------------------

    def label(self, meta: Any, token: Token) -> StringWithPosition:
        value: str = self.parse_escaped_string(token)
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=token
        )
        return StringWithPosition(value=value, position=position)

    def documentation(self, meta: Any, token: Token) -> StringWithPosition:
        value: str = _triple_string_value(token)
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=token
        )
        return StringWithPosition(value=value, position=position)

    def boolean(self, meta: Any, token: Token) -> bool:
        text: str = str(token)
        return text.lower() == "true"

    def number(self, meta: Any, token: Token) -> float:
        return float(str(token))

    # ---------------------------------------------------------------------
    # Simple list rules
    # ---------------------------------------------------------------------

    def name_list(self, meta: Any, *children: Any) -> Tuple[str, ...]:
        # children are NAME tokens (and commas are literals, not included)
        names: List[str] = []
        for child in children:
            if isinstance(child, Token):
                names.append(str(child))
            elif isinstance(child, str):
                names.append(child)
        return tuple(names)

    def member_list(self, meta: Any, *children: Any) -> Tuple[str, ...]:
        # In the grammar, member_list is typically bracketed; we only receive names.
        members: List[str] = []
        for child in children:
            if isinstance(child, Token):
                members.append(str(child))
            elif isinstance(child, str):
                members.append(child)
            elif isinstance(child, tuple):
                # allow passthrough from name_list in some grammars
                members.extend([str(x) for x in child])
        return tuple(members)

    # ---------------------------------------------------------------------
    # Dimension expressions
    # ---------------------------------------------------------------------

    def dimension_reference(self, meta: Any, name_token: Token) -> DimensionReference:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=name_token
        )
        return DimensionReference(position=position, dimension=str(name_token))

    def dimension_term(self, meta: Any, child: Any) -> Any:
        # The grammar typically routes either member_list or dimension_reference here.
        return child

    def dimension_expression(
        self, meta: Any, first_term: Any, *rest: Any
    ) -> DimensionExpression:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        first: Any = first_term
        if isinstance(first_term, tuple):
            first = DimensionListTerm(
                position=position, members=tuple(str(x) for x in first_term)
            )
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
                term_node = DimensionListTerm(
                    position=position, members=tuple(str(x) for x in term_value)
                )
            else:
                term_node = term_value
            rest_pairs.append((operator, term_node))
            i += 2
        return DimensionExpression(
            position=position, first=first, rest=tuple(rest_pairs)
        )

    # ---------------------------------------------------------------------
    # Domain expressions
    # ---------------------------------------------------------------------

    def domain_list(self, meta: Any, child: Any) -> NameList:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        if isinstance(child, tuple):
            # Heuristic: name_list returns tuple[str,...]; member_list also returns tuple[str,...].
            # We cannot distinguish reliably here; later passes can resolve using symbol tables.
            return NameList(
                position=position, kind="names", items=tuple(str(x) for x in child)
            )
        if isinstance(child, NameList):
            return child
        raise TypeError(f"Unexpected domain_list child type: {type(child)}")

    def tuple_condition(
        self, meta: Any, left: Token, operator_token: Token, right: Token
    ) -> TupleCondition:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return TupleCondition(
            position=position,
            left_position=int(str(left)),
            operator=str(operator_token),
            right_position=int(str(right)),
        )

    def tuple_conditions(self, meta: Any, *children: Any) -> Tuple[TupleCondition, ...]:
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
        self, meta: Any, first_term: DomainTerm, *rest: Any
    ) -> DomainExpression:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        rest_pairs: List[Tuple[str, DomainTerm]] = []
        rest_items: Tuple[Any, ...] = tuple(rest)
        i: int = 0
        while i + 1 < len(rest_items):
            operator: str = str(rest_items[i])
            term: DomainTerm = rest_items[i + 1]
            rest_pairs.append((operator, term))
            i += 2
        return DomainExpression(
            position=position, first=first_term, rest=tuple(rest_pairs)
        )

    # ---------------------------------------------------------------------
    # Declarations
    # ---------------------------------------------------------------------

    def include_declaration(self, meta: Any, path_token: Token) -> IncludeDeclaration:
        included_path: str = self.parse_escaped_string(path_token)
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return IncludeDeclaration(
            position=position,
            declaration_type=DeclarationType.include,
            included_path=included_path,
        )

    def member_declaration(
        self,
        meta: Any,
        _member_kw: Any,
        name_token: Token,
        _colon: Any,
        label: StringWithPosition,
        documentation: Optional[StringWithPosition] = None,
    ) -> MemberDeclaration:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=name_token
        )
        return MemberDeclaration(
            position=position,
            declaration_type=DeclarationType.member,
            name=str(name_token),
            label=label,
            documentation=documentation,
        )

    def category_declaration(
        self,
        meta: Any,
        _kw: Any,
        name_token: Token,
        _colon: Any,
        label: StringWithPosition,
        members: Tuple[str, ...],
        documentation: Optional[StringWithPosition] = None,
    ) -> CategoryDeclaration:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=name_token
        )
        return CategoryDeclaration(
            position=position,
            declaration_type=DeclarationType.category,
            name=str(name_token),
            label=label,
            members=members,
            documentation=documentation,
        )

    def dimension_declaration(
        self,
        meta: Any,
        _kw: Any,
        name_token: Token,
        _colon: Any,
        label: StringWithPosition,
        expression: Optional[DimensionExpression] = None,
        documentation: Optional[StringWithPosition] = None,
    ) -> DimensionDeclaration:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=name_token
        )
        return DimensionDeclaration(
            position=position,
            declaration_type=DeclarationType.dimension,
            name=str(name_token),
            label=label,
            expression=expression,
            documentation=documentation,
        )

    def domain_declaration(
        self,
        meta: Any,
        _kw: Any,
        name_token: Token,
        _colon: Any,
        label: StringWithPosition,
        expression: Optional[DomainExpression] = None,
        documentation: Optional[StringWithPosition] = None,
    ) -> DomainDeclaration:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=name_token
        )
        return DomainDeclaration(
            position=position,
            declaration_type=DeclarationType.domain,
            name=str(name_token),
            label=label,
            expression=expression,
            documentation=documentation,
        )

    def unit_declaration(
        self,
        meta: Any,
        _kw: Any,
        name_token: Token,
        _colon: Any,
        label: StringWithPosition,
        documentation: Optional[StringWithPosition] = None,
    ) -> UnitDeclaration:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=name_token
        )
        return UnitDeclaration(
            position=position,
            declaration_type=DeclarationType.unit,
            name=str(name_token),
            label=label,
            documentation=documentation,
        )

    def unit(
        self, meta: Any, _kw: Any, _equals: Any, name_token: Token
    ) -> UnitSpecification:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=name_token
        )
        return UnitSpecification(position=position, unit_name=str(name_token))

    def deviation_unit(
        self, meta: Any, _kw: Any, _equals: Any, name_token: Token
    ) -> DeviationUnitSpecification:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=name_token
        )
        return DeviationUnitSpecification(
            position=position, deviation_unit_name=str(name_token)
        )

    def logged(self, meta: Any, _kw: Any, _equals: Any, value: bool) -> bool:
        return bool(value)

    def intertemporal(self, meta: Any, _kw: Any, _equals: Any, value: bool) -> bool:
        return bool(value)

    def parameter_declaration(
        self,
        meta: Any,
        _kw: Any,
        name_token: Token,
        _colon: Any,
        label: StringWithPosition,
        domain_assignment: Optional[DomainExpression] = None,
        unit: Optional[UnitSpecification] = None,
        documentation: Optional[StringWithPosition] = None,
    ) -> ParameterDeclaration:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=name_token
        )
        return ParameterDeclaration(
            position=position,
            declaration_type=DeclarationType.parameter,
            name=str(name_token),
            label=label,
            domain_expression=domain_assignment,
            unit=unit,
            documentation=documentation,
        )

    def variable_declaration(
        self,
        meta: Any,
        _kw: Any,
        name_token: Token,
        _colon: Any,
        label: StringWithPosition,
        domain_assignment: Optional[DomainExpression] = None,
        unit: Optional[UnitSpecification] = None,
        deviation_unit: Optional[DeviationUnitSpecification] = None,
        logged: Optional[bool] = None,
        intertemporal: Optional[bool] = None,
        documentation: Optional[StringWithPosition] = None,
    ) -> VariableDeclaration:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=name_token
        )
        return VariableDeclaration(
            position=position,
            declaration_type=DeclarationType.variable,
            name=str(name_token),
            label=label,
            domain_expression=domain_assignment,
            unit=unit,
            deviation_unit=deviation_unit,
            logged=logged,
            intertemporal=intertemporal,
            documentation=documentation,
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
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
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

    def lhs_variable_reference(
        self,
        meta: Any,
        name_token: Token,
        domain_expression: Optional[DomainExpression] = None,
    ) -> LhsVariableReference:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=name_token
        )
        return LhsVariableReference(
            position=position, name=str(name_token), domain_expression=domain_expression
        )

    def rhs_domain_restriction(
        self, meta: Any, _dom: Any, _equals: Any, domain_expression: DomainExpression
    ) -> Tuple[str, DomainExpression]:
        return ("dom", domain_expression)

    def tuple_position_list(
        self, meta: Any, *children: Any
    ) -> Tuple[Tuple[str, int], ...]:
        # pattern: dimension_reference ":" TUPLE_POSITION ("," dimension_reference ":" TUPLE_POSITION)*
        result: List[Tuple[str, int]] = []
        items: List[Any] = list(children)
        i: int = 0
        while i + 2 < len(items):
            dimension_term: Any = items[i]
            tuple_position: Any = items[i + 2]
            dimension_name: str
            if isinstance(dimension_term, DimensionReference):
                dimension_name = dimension_term.dimension
            elif isinstance(dimension_term, Token):
                dimension_name = str(dimension_term)
            else:
                dimension_name = str(dimension_term)
            result.append((dimension_name, int(str(tuple_position))))
            i += 3
        return tuple(result)

    def rhs_dimension_matches(
        self, meta: Any, _dim: Any, _equals: Any, positions: Tuple[Tuple[str, int], ...]
    ) -> Tuple[str, Tuple[Tuple[str, int], ...]]:
        return ("dim", positions)

    def rhs_aggregation_matches(
        self, meta: Any, _agg: Any, _equals: Any, positions: Tuple[Tuple[str, int], ...]
    ) -> Tuple[str, Tuple[Tuple[str, int], ...]]:
        return ("agg", positions)

    def rhs_variable_reference(
        self, meta: Any, name_token: Token, conditionals: Optional[Sequence[Any]] = None
    ) -> VariableReference:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=name_token
        )
        domain_expression: Optional[DomainExpression] = None
        dimension_matches: Optional[Tuple[Tuple[str, int], ...]] = None
        aggregation_matches: Optional[Tuple[Tuple[str, int], ...]] = None

        if conditionals:
            for conditional in conditionals:
                if (
                    isinstance(conditional, tuple)
                    and conditional
                    and conditional[0] == "dom"
                ):
                    domain_expression = conditional[1]
                if (
                    isinstance(conditional, tuple)
                    and conditional
                    and conditional[0] == "dim"
                ):
                    dimension_matches = tuple(conditional[1])
                if (
                    isinstance(conditional, tuple)
                    and conditional
                    and conditional[0] == "agg"
                ):
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

    def lhs_expectation(
        self, meta: Any, _e: Any, _lparen: Any, inner: Any, _rparen: Any
    ) -> LhsExpectation:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return LhsExpectation(position=position, inner=inner)

    def lhs_lead(
        self,
        meta: Any,
        _lead: Any,
        _lparen: Any,
        inner: Any,
        _comma_or_rparen: Any = None,
        lead_amount: Optional[Token] = None,
        _rparen: Any = None,
    ) -> LhsLead:
        """
        The grammar variants seen during development differ slightly. This method is tolerant:
          - lead(lhs_wrapped_variable, INT)
          - lead(lhs_wrapped_variable)
        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        amount: int = 1
        if lead_amount is not None and isinstance(lead_amount, Token):
            amount = int(str(lead_amount))
        return LhsLead(position=position, inner=inner, lead_amount=amount)

    def lhs_wrapped_variable_reference(
        self, meta: Any, reference: LhsVariableReference
    ) -> LhsWrappedVariable:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return LhsWrappedVariable(position=position, reference=reference)

    # ---------------------------------------------------------------------
    # Equation root
    # ---------------------------------------------------------------------

    def equality_expression(
        self, meta: Any, lhs: Any, _equals: Any, rhs: Any
    ) -> EquationExpression:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        if isinstance(lhs, LhsVariableReference):
            lhs_wrapped: Any = LhsWrappedVariable(position=lhs.position, reference=lhs)
        else:
            lhs_wrapped = lhs
        return EquationExpression(position=position, lhs=lhs_wrapped, rhs=rhs)

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

    def summation(
        self,
        meta: Any,
        _sum: Any,
        _lparen: Any,
        dimension: DimensionReference,
        _bar: Any,
        body: Any,
        _rparen: Any,
    ) -> Summation:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return Summation(
            position=position, dimension_name=dimension.dimension, body=body
        )

    def product(
        self,
        meta: Any,
        _prod: Any,
        _lparen: Any,
        dimension: DimensionReference,
        _bar: Any,
        body: Any,
        _rparen: Any,
    ) -> Product:
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        return Product(position=position, dimension_name=dimension.dimension, body=body)

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

    def declaration(self, meta: Any, child: Any) -> AnyDeclaration:
        return child

    def start(self, meta: Any, *children: Any) -> Tuple[AnyDeclaration, ...]:
        declarations: List[AnyDeclaration] = [c for c in children if c is not None]
        return tuple(declarations)


def parse_module(file_path: Path, text: str) -> Tuple[Optional[Module], DiagnosticBag]:
    """
    Parse a single Symphony file (already loaded as text) into a Module plus diagnostics.
    """
    diagnostics: DiagnosticBag = DiagnosticBag()

    try:
        parser = symphony_parser()
        tree = parser.parse(text)
        transformer = AbstractSyntaxTreeTransformer(file_path=file_path)
        declarations = transformer.transform(tree)
        if not isinstance(declarations, tuple):
            declarations = (declarations,)  # defensive
        module = Module(
            position=SourcePosition(file_path=file_path, line=1, column=1),
            file_path=file_path,
            declarations=tuple(declarations),
        )
        return module, diagnostics
    except UnexpectedInput as err:
        diagnostics.add(
            Diagnostic(
                severity=DiagnosticSeverity.error,
                message=f"Failed to parse Symphony file: {err}",
                primary_label=DiagnosticLabel(
                    position=SourcePosition(
                        file_path=file_path,
                        line=getattr(err, "line", 1),
                        column=getattr(err, "column", 1),
                    ),
                    message="Parse error occurred here.",
                    is_primary=True,
                ),
                help_text="Check syntax near this location.",
            )
        )
        return None, diagnostics


def build_modules(symphony_files: SymphonyFiles) -> Tuple[Modules, DiagnosticBag]:
    """
    Parse all already-loaded SymphonyFiles into Modules.

    This assumes a Loader has expanded includes and populated SymphonyFiles.
    """
    diagnostics: DiagnosticBag = DiagnosticBag()
    modules: List[Module] = []

    for symphony_file in symphony_files.files:
        module, module_diagnostics = parse_module(
            symphony_file.file_path, symphony_file.text
        )
        diagnostics.extend(module_diagnostics)
        if module is not None:
            modules.append(module)

    return Modules(modules=tuple(modules)), diagnostics
