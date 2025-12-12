from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass, fields
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union
from symphony import SourcePosition

# Abstract Syntax Tree definitions and printers

# ========= Core AST node types =========

DomainTuple = Tuple[str]  # The members in a tuple.
DomainTuples = Tuple[DomainTuple]  # The tuples in a domain.

# The content and position of a docstring documentation for an entity.
Documentation = Tuple[str, SourcePosition]

# Internal structures used for dimension expressions:
# ("list", List[Token])  -> a bracketed list of member names
# ("dimension reference", (name, SourcePosition)) -> reference to a dimension
DimensionTerm = Tuple[str, Any]

# ("dimension_expression", first_term, [(op, term), ...])
DimensionExpression = Tuple[str, DimensionTerm, List[Tuple[str, DimensionTerm]]]

# Internal structure used for domain expressions:
# ("dimension reference", (name, SourcePosition)) -> reference to a dimension
DomainTerm = Tuple[str, Tuple[str, SourcePosition]]

# ("domain_expression", first_term, [(op, term), ...])
DomainExpression = Tuple[str, DomainTerm, List[Tuple[str, DomainTerm]]]


@dataclass(frozen=True)
class Declaration:
    """
    Base class for all top-level declarations.

    The common fields are:
    - `position`: Source position of the declaration.
    - `name`: Optional name of the declared entity.
    - `label`: Optional label of the declared entity.
    - `documentation`: Optional documentation string associated with the declaration.

    """

    position: SourcePosition
    label: Optional[str]
    documentation: Optional[str]


@dataclass(frozen=True)
class EquationDeclaration(Declaration):
    """
    Equation declaration.
    """

    pass


@dataclass(frozen=True)
class NamedDeclaration(Declaration):
    """
    Base class for all top-level declarations.

    The common fields are:
    - `name`: Required unique name of the declared entity.

    """

    name: str


@dataclass(frozen=True)
class MemberDeclaration(NamedDeclaration):
    """
    Member declaration.
    """

    pass


@dataclass(frozen=True)
class UnitDeclaration(NamedDeclaration):
    """
    Unit declaration.
    """

    pass


@dataclass(frozen=True)
class DimensionDeclaration(NamedDeclaration):
    """
    Dimension declaration.

    Pass 1:
        - `members` is left empty.
        - `expression` holds the raw dimension expression AST.

    Later semantic passes:
        - evaluate `dimension_expression`
        - fill `dimension_members` with the resolved member names.
    """

    members: Tuple[str]
    expression: Optional[DimensionExpression] = None


@dataclass(frozen=True)
class CategoryDeclaration(NamedDeclaration):
    """
    Category declaration (a specialized dimension).
    """

    pass


@dataclass(frozen=True)
class DomainDeclaration(NamedDeclaration):
    """
    Domain declaration.
    """

    tuples: DomainTuples = field(default_factory=list)


@dataclass(frozen=True)
class ParameterDeclaration(NamedDeclaration):
    """
    Parameter declaration.
    """

    pass


@dataclass(frozen=True)
class VariableDeclaration(NamedDeclaration):
    """
    Variable declaration.
    """

    pass


AnyDeclaration = Union[
    MemberDeclaration,
    CategoryDeclaration,
    DimensionDeclaration,
    DomainDeclaration,
    ParameterDeclaration,
    VariableDeclaration,
    EquationDeclaration,
    UnitDeclaration,
]


@dataclass(frozen=True)
class Model:
    """
    The model consists of a flat list of declarations.
    """

    declarations: List[AnyDeclaration]
