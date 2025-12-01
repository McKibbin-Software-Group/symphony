from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass, fields
from enum import Enum
from typing import Any, List, Optional, Tuple, Union

# Abstract Syntax Tree definitions and printers

# ========= Core AST node types =========


@dataclass(frozen=True)
class SourcePosition:
    """
    1-based line/column location in the source file.
    """
    line: int
    column: int


class DeclarationType(str, Enum):
    """
    Top-level declaration types.
    """
    member = "member"
    unit = "unit"
    dimension = "dimension"
    dimensions = "dimensions"
    domain = "domain"
    parameter = "parameter"
    variable = "variable"
    equation = "equation"
    category = "category"

DomainTuple = List[str] # The list of members in a domain tuple.
DomainTuples = List[DomainTuple] # The list of tuples in a domain.

Documentation = Tuple[str, SourcePosition] # The content and position of a docstring documentation for an entity.

# Internal structures used for dimension expressions:
# ("list", List[Token])  -> a bracketed list of member names
# ("dimension reference", (name, SourcePosition)) -> reference to a dimension
DimensionTerm = Tuple[str, Any]

# Internal structure used for domain expressions:
# ("dimension reference", (name, SourcePosition)) -> reference to a dimension
DomainTerm = Tuple[str, Tuple[str, SourcePosition]]

# ("dimension_expression", first_term, [(op, term), ...])
DimensionExpression = Tuple[str, DimensionTerm, List[Tuple[str, DimensionTerm]]]

# ("domain_expression", first_term, [(op, term), ...])
DomainExpression = Tuple[str, DomainTerm, List[Tuple[str, DomainTerm]]]

@dataclass(frozen=True)
class Declaration:
    """
    Base class for all top-level declarations.
    """
    declaration_type: DeclarationType
    type_position: SourcePosition

    name: str
    name_position: SourcePosition

    label: str
    label_position: SourcePosition

    documentation: Optional[str]
    documentation_position: Optional[SourcePosition]


@dataclass(frozen=True)
class MemberDeclaration(Declaration):
    """
    `member` NAME ":" label doc?
    """
    pass


@dataclass(frozen=True)
class UnitDeclaration(Declaration):
    """
    Unit declaration.
    """
    pass


@dataclass(frozen=True)
class DimensionDeclaration(Declaration):
    """
    `dimension` NAME ":" label dimension_expression? doc?

    Pass 1:
        - `dimension_expression` holds the raw dimension expression AST.
        - `dimension_members` is left empty.

    Later semantic passes:
        - evaluate `dimension_expression`
        - fill `dimension_members` with the resolved member names.
    """
    dimension_members: List[str]
    dimension_expression: Optional[DimensionExpression] = None


@dataclass(frozen=True)
class CategoryDeclaration(DimensionDeclaration):
    """
    `category` NAME ":" label [name_list] doc?
    """
    pass

@dataclass(frozen=True)
class DomainDeclaration(Declaration):
    """
    Domain declaration (exact syntax driven by the grammar).
    """
    tuples: DomainTuples = field(default_factory=list)

@dataclass(frozen=True)
class DimensionsDeclaration(DomainDeclaration):
    """
     "dimensions" NAME ":" label name_list doc?

    `dimensions` lists the name of each included dimension
    """
    dimensions: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ParameterDeclaration(Declaration):
    """
    Parameter declaration.
    """
    pass

@dataclass(frozen=True)
class VariableDeclaration(Declaration):
    """
    Variable declaration.
    """
    pass


@dataclass(frozen=True)
class EquationDeclaration(Declaration):
    """
    Equation declaration.
    """
    pass


DeclarationNode = Union[
    MemberDeclaration,
    CategoryDeclaration,
    DimensionDeclaration,
    DimensionsDeclaration,
    DomainDeclaration,
    ParameterDeclaration,
    VariableDeclaration,
    EquationDeclaration,
    UnitDeclaration,
]


@dataclass(frozen=True)
class Model:
    """
    Root node: a flat list of declarations.
    """
    declarations: List[DeclarationNode]


