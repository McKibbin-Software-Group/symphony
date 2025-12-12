from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass, fields
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
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
class Module:
    """
    The module consists of a flat list of declarations from a single Symphony file.
    """

    declarations: List[AnyDeclaration]

class Model:
    """
    The model consists of a flat list of declarations that together make up the model.
    """

    def __init__(self):
        """
         ### Overview
         
         Set up the symbol tables for the model.
         """
        self._names: Set[str] = set()
        self._members: Dict[str, MemberDeclaration] = {}
        self._dimensions: Dict[str, DimensionDeclaration] = {}
        self._categories: Dict[str, CategoryDeclaration] = {}
        self._domains: Dict[str, DomainDeclaration] = {}
        self._units: Dict[str, UnitDeclaration] = {}
        self._parameters: Dict[str, ParameterDeclaration] = {}
        self._variables: Dict[str, VariableDeclaration] = {}
        self._equations: Dict[str, EquationDeclaration] = {}

    @property
    def names(self) -> Set[str]:
        """
        ### Overview

        Get the set of all names declared in this model.

        ### Returns

        A set of all declared names.
        """
        return self._names

    @property
    def members(self) -> Dict[str, MemberDeclaration]:
        """
        ### Overview

        Get the list of member declarations in this model.

        ### Returns

        A list of `MemberDeclaration` objects.
        """
        return self._members
    
    @property
    def categories(self) -> Dict[str, CategoryDeclaration]:
        """
        ### Overview

        Get the list of category declarations in this model.

        ### Returns

        A list of `CategoryDeclaration` objects.
        """
        return self._categories
    
    @property
    def dimensions(self) -> Dict[str, DimensionDeclaration]:
        """
        ### Overview

        Get the list of dimension declarations in this model.

        ### Returns

        A list of `DimensionDeclaration` objects.
        """
        return self._dimensions
    
    @property
    def domains(self) -> Dict[str, DomainDeclaration]:
        """
        ### Overview

        Get the list of domain declarations in this model.

        ### Returns

        A list of `DomainDeclaration` objects.
        """
        return self._domains
    
    @property
    def units(self) -> Dict[str, UnitDeclaration]:
        """
        ### Overview

        Get the list of unit declarations in this model.

        ### Returns

        A list of `UnitDeclaration` objects.
        """
        return self._units
    
    @property
    def parameters(self) -> Dict[str, ParameterDeclaration]:
        """
        ### Overview

        Get the list of parameter declarations in this model.

        ### Returns

        A list of `ParameterDeclaration` objects.
        """
        return self._parameters
    
    @property
    def variables(self) -> Dict[str, VariableDeclaration]:
        """
        ### Overview

        Get the list of variable declarations in this model.

        ### Returns

        A list of `VariableDeclaration` objects.
        """
        return self._variables
    
    @property
    def equations(self) -> Dict[str, EquationDeclaration]:
        """
        ### Overview

        Get the list of equation declarations in this model.

        ### Returns

        A list of `EquationDeclaration` objects.
        """
        return self._equations

    def add(self, module: Module) -> None:
        """
        ### Overview

        Add declarations from a module into this model.

        ### Arguments

        - `module: Module`: The module whose declarations are to be added.
        """
        for declaration in module.declarations:

            if isinstance(declaration, CategoryDeclaration):
                if declaration.name in self.categories:
                    raise ValueError(f"Duplicate category name: {declaration.name}. See {declaration.position}.")
                if declaration.name in self.dimensions:
                    raise ValueError(f"Duplicate dimension/category name: {declaration.name}. See {declaration.position}.")
                if declaration.name in self._names:
                    raise ValueError(f"Duplicate name: {declaration.name}. See {declaration.position}.")                
                self._names.add(declaration.name)
                self.dimensions[declaration.name] = declaration
                self.categories[declaration.name] = declaration

            elif isinstance(declaration, MemberDeclaration):
                if declaration.name in self.members:
                    raise ValueError(f"Duplicate member name: {declaration.name}. See {declaration.position}.")
                if declaration.name in self._names:
                    raise ValueError(f"Duplicate name: {declaration.name}. See {declaration.position}.")
                self.names.add(declaration.name)
                self.members[declaration.name] = declaration
