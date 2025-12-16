from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Optional, Sequence, Tuple, Union

from symphony import SourcePosition


# =============================================================================
# Base node types
# =============================================================================

@dataclass(frozen=True, slots=True)
class Node:
    """
    Base type for all abstract syntax tree nodes.
    """
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class StringWithPosition:
    value: str
    position: SourcePosition


# =============================================================================
# Declarations
# =============================================================================

class DeclarationType(str, Enum):
    include = "include"
    member = "member"
    category = "category"
    dimension = "dimension"
    domain = "domain"
    parameter = "parameter"
    variable = "variable"
    unit = "unit"
    equation = "equation"


@dataclass(frozen=True, slots=True)
class Declaration(Node):
    declaration_type: DeclarationType


@dataclass(frozen=True, slots=True)
class IncludeDeclaration(Declaration):
    declaration_type: DeclarationType = DeclarationType.include
    included_path: str = ""


@dataclass(frozen=True, slots=True)
class NamedDeclaration(Declaration):
    name: str = ""
    label: StringWithPosition = field(
        default_factory=lambda: StringWithPosition(
            value="",
            position=SourcePosition(file_path=Path("<unknown>"), line=1, column=1),
        )
    )
    documentation: Optional[StringWithPosition] = None


@dataclass(frozen=True, slots=True)
class MemberDeclaration(NamedDeclaration):
    declaration_type: DeclarationType = DeclarationType.member


@dataclass(frozen=True, slots=True)
class CategoryDeclaration(NamedDeclaration):
    declaration_type: DeclarationType = DeclarationType.category
    members: Tuple[str, ...] = ()


# =============================================================================
# Dimension and domain expressions (raw, pass 1)
# =============================================================================

@dataclass(frozen=True, slots=True)
class DimensionTerm(Node):
    pass


@dataclass(frozen=True, slots=True)
class DimensionListTerm(DimensionTerm):
    members: Tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DimensionReferenceTerm(DimensionTerm):
    referenced_dimension: str = ""


@dataclass(frozen=True, slots=True)
class DimensionExpression(Node):
    first: DimensionTerm
    rest: Tuple[Tuple[str, DimensionTerm], ...] = ()


@dataclass(frozen=True, slots=True)
class DomainList(Node):
    """
    A list that appears inside a domain expression term.

    The grammar allows either:
      - name_list: typically dimension names
      - member_list: explicit member names

    Pass 1 does not resolve which is intended; later passes can interpret using
    symbol tables. We record the list and whether it came from name_list or
    member_list.
    """
    kind: str  # "names" | "members"
    items: Tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TupleCondition(Node):
    """
    A condition over tuple positions, e.g. 1 = 2 or 1 != 2.
    """
    left_position: int
    operator: str
    right_position: int


@dataclass(frozen=True, slots=True)
class DomainTerm(Node):
    domain_list: DomainList
    tuple_conditions: Tuple[TupleCondition, ...] = ()


@dataclass(frozen=True, slots=True)
class DomainExpression(Node):
    first: DomainTerm
    rest: Tuple[Tuple[str, DomainTerm], ...] = ()


@dataclass(frozen=True, slots=True)
class DimensionDeclaration(NamedDeclaration):
    declaration_type: DeclarationType = DeclarationType.dimension
    expression: Optional[DimensionExpression] = None
    resolved_members: Optional[Tuple[str, ...]] = None


@dataclass(frozen=True, slots=True)
class DomainDeclaration(NamedDeclaration):
    declaration_type: DeclarationType = DeclarationType.domain
    expression: Optional[DomainExpression] = None
    resolved_tuples: Optional[Tuple[Tuple[str, ...], ...]] = None


# =============================================================================
# Units
# =============================================================================

@dataclass(frozen=True, slots=True)
class UnitDeclaration(NamedDeclaration):
    declaration_type: DeclarationType = DeclarationType.unit


# =============================================================================
# Parameters and variables
# =============================================================================

@dataclass(frozen=True, slots=True)
class UnitSpecification(Node):
    unit_name: str


@dataclass(frozen=True, slots=True)
class DeviationUnitSpecification(Node):
    deviation_unit_name: str


@dataclass(frozen=True, slots=True)
class ParameterDeclaration(NamedDeclaration):
    declaration_type: DeclarationType = DeclarationType.parameter
    domain_expression: Optional[DomainExpression] = None
    unit: Optional[UnitSpecification] = None


@dataclass(frozen=True, slots=True)
class VariableDeclaration(NamedDeclaration):
    declaration_type: DeclarationType = DeclarationType.variable
    domain_expression: Optional[DomainExpression] = None
    unit: Optional[UnitSpecification] = None
    deviation_unit: Optional[DeviationUnitSpecification] = None
    logged: Optional[bool] = None
    intertemporal: Optional[bool] = None


# =============================================================================
# Equation expression nodes
# =============================================================================

@dataclass(frozen=True, slots=True)
class VariableReference(Node):
    name: str
    domain_expression: Optional[DomainExpression] = None
    dimension_matches: Optional[Tuple[Tuple[str, int], ...]] = None
    aggregation_matches: Optional[Tuple[Tuple[str, int], ...]] = None


@dataclass(frozen=True, slots=True)
class LhsVariableReference(Node):
    name: str
    domain_expression: Optional[DomainExpression] = None


@dataclass(frozen=True, slots=True)
class Expression(Node):
    pass


@dataclass(frozen=True, slots=True)
class NumberLiteral(Expression):
    value: float


@dataclass(frozen=True, slots=True)
class BooleanLiteral(Expression):
    value: bool


@dataclass(frozen=True, slots=True)
class VariableExpression(Expression):
    reference: VariableReference


@dataclass(frozen=True, slots=True)
class FunctionCall(Expression):
    function_name: str
    argument: Expression


@dataclass(frozen=True, slots=True)
class UnaryMinus(Expression):
    operand: Expression


@dataclass(frozen=True, slots=True)
class BinaryOperation(Expression):
    operator: str
    left: Expression
    right: Expression


@dataclass(frozen=True, slots=True)
class Summation(Expression):
    dimension_name: str
    body: Expression


@dataclass(frozen=True, slots=True)
class Product(Expression):
    dimension_name: str
    body: Expression


@dataclass(frozen=True, slots=True)
class Expectation(Expression):
    reference: VariableReference


@dataclass(frozen=True, slots=True)
class LhsWrapped(Node):
    pass


@dataclass(frozen=True, slots=True)
class LhsWrappedVariable(LhsWrapped):
    reference: LhsVariableReference


@dataclass(frozen=True, slots=True)
class LhsExpectation(LhsWrapped):
    inner: LhsWrapped


@dataclass(frozen=True, slots=True)
class LhsLead(LhsWrapped):
    inner: LhsWrapped
    lead_amount: int


@dataclass(frozen=True, slots=True)
class EquationExpression(Node):
    lhs: LhsWrapped
    rhs: Expression


@dataclass(frozen=True, slots=True)
class EquationDeclaration(Declaration):
    declaration_type: DeclarationType = DeclarationType.equation
    label: StringWithPosition = field(
        default_factory=lambda: StringWithPosition(
            value="",
            position=SourcePosition(file_path=Path("<unknown>"), line=1, column=1),
        )
    )
    domain_expression: Optional[DomainExpression] = None
    equation_expression: Optional[EquationExpression] = None
    documentation: Optional[StringWithPosition] = None


AnyDeclaration = Union[
    IncludeDeclaration,
    MemberDeclaration,
    CategoryDeclaration,
    DimensionDeclaration,
    DomainDeclaration,
    ParameterDeclaration,
    VariableDeclaration,
    UnitDeclaration,
    EquationDeclaration,
]


# =============================================================================
# Module containers
# =============================================================================

@dataclass(frozen=True, slots=True)
class Module(Node):
    file_path: Path
    declarations: Tuple[AnyDeclaration, ...] = ()


@dataclass(frozen=True, slots=True)
class Modules:
    modules: Tuple[Module, ...]

    @property
    def declarations(self) -> Tuple[AnyDeclaration, ...]:
        return tuple(declaration for module in self.modules for declaration in module.declarations)


# =============================================================================
# Convenience helpers for later passes (do not mutate frozen nodes)
# =============================================================================

def with_resolved_dimension_members(
    declaration: DimensionDeclaration,
    resolved_members: Sequence[str],
) -> DimensionDeclaration:
    return replace(declaration, resolved_members=tuple(resolved_members))


def with_resolved_domain_tuples(
    declaration: DomainDeclaration,
    resolved_tuples: Sequence[Sequence[str]],
) -> DomainDeclaration:
    return replace(declaration, resolved_tuples=tuple(tuple(items) for items in resolved_tuples))
