from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Tuple
from lark import Token
from symphony import SourcePosition

# Abstract Syntax Tree definitions and printers

# ========= Core AST node types =========

DomainTuple = Tuple[str]  # The members in a tuple.
DomainTuples = Tuple[DomainTuple]  # The tuples in a domain.

# The content and position of a docstring documentation for an entity.
StringWithPosition = Tuple[str, SourcePosition]

# Internal structures used for dimension expressions:
# ("list", List[Token])  -> a bracketed list of member names
# ("dimension reference", (name, SourcePosition)) -> reference to a dimension
TypedList = Tuple[str, List[Token]]
NameReference = Tuple[str, Tuple[str, SourcePosition]]

DimensionTerm = TypedList | NameReference

# ("dimension_expression", first_term, [(op, term), ...])
DimensionExpression = Tuple[str, TypedList, List[Tuple[str, DimensionTerm]]]

# Internal structure used for domain expressions:
# ("dimension reference", (name, SourcePosition)) -> reference to a dimension
DomainTerm = NameReference

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

    expression: Optional[DimensionExpression] = None


@dataclass(frozen=True)
class CategoryDeclaration(DimensionDeclaration):
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


AnyDeclaration = (
    MemberDeclaration
    | CategoryDeclaration
    | DimensionDeclaration
    | DomainDeclaration
    | ParameterDeclaration
    | VariableDeclaration
    | EquationDeclaration
    | UnitDeclaration
)


@dataclass(frozen=True)
class Module:
    """
    The module consists of a flat list of declarations from a single Symphony file.
    """

    declarations: List[AnyDeclaration]


@dataclass(frozen=True)
class Modules:
    """
    The full set of modules defining the model.
    """

    modules: Tuple[Module, ...]

    @property
    def declarations(self) -> Tuple[AnyDeclaration, ...]:
        """
        Return all declarations in the full set of modules as a flat tuple.
        """
        return tuple(
            declaration
            for module in self.modules
            for declaration in module.declarations
        )
