from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set
from symphony.abstract_syntax_tree import (
    CategoryDeclaration,
    DimensionDeclaration,
    DomainDeclaration,
    EquationDeclaration,
    MemberDeclaration,
    Modules,
    ParameterDeclaration,
    UnitDeclaration,
    VariableDeclaration,
)


@dataclass(frozen=True)
class SymbolTable:
    """
    Symbol table for the model.
    """

    names: Set[str]
    members: Dict[str, MemberDeclaration]
    dimensions: Dict[str, DimensionDeclaration]
    categories: Dict[str, CategoryDeclaration]
    domains: Dict[str, DomainDeclaration]
    units: Dict[str, UnitDeclaration]
    parameters: Dict[str, ParameterDeclaration]
    variables: Dict[str, VariableDeclaration]
    equations: Dict[str, EquationDeclaration]

    def build_model_index(modules: Modules) -> SymbolTable:
        names: Set[str] = set()
        members: Dict[str, MemberDeclaration] = {}
        dimensions: Dict[str, DimensionDeclaration] = {}
        categories: Dict[str, CategoryDeclaration] = {}
        domains: Dict[str, DomainDeclaration] = {}
        units: Dict[str, UnitDeclaration] = {}
        parameters: Dict[str, ParameterDeclaration] = {}
        variables: Dict[str, VariableDeclaration] = {}
        equations: Dict[str, EquationDeclaration] = {}

        for declaration in modules.declarations:
            if isinstance(declaration, CategoryDeclaration):
                if declaration.name in categories:
                    raise ValueError(
                        f"Duplicate category name: {declaration.name}. See {declaration.position}."
                    )
                if declaration.name in dimensions:
                    raise ValueError(
                        f"Duplicate dimension/category name: {declaration.name}. See {declaration.position}."
                    )
                if declaration.name in names:
                    raise ValueError(
                        f"Duplicate name: {declaration.name}. See {declaration.position}."
                    )
                names.add(declaration.name)
                dimensions[declaration.name] = declaration
                categories[declaration.name] = declaration

            elif isinstance(declaration, DimensionDeclaration):
                if declaration.name in dimensions:
                    raise ValueError(
                        f"Duplicate dimension name: {declaration.name}. See {declaration.position}."
                    )
                if declaration.name in categories:
                    raise ValueError(
                        f"Duplicate dimension/category name: {declaration.name}. See {declaration.position}."
                    )
                if declaration.name in names:
                    raise ValueError(
                        f"Duplicate name: {declaration.name}. See {declaration.position}."
                    )
                names.add(declaration.name)
                dimensions[declaration.name] = declaration

            elif isinstance(declaration, MemberDeclaration):
                if declaration.name in members:
                    raise ValueError(
                        f"Duplicate member name: {declaration.name}. See {declaration.position}."
                    )
                if declaration.name in names:
                    raise ValueError(
                        f"Duplicate name: {declaration.name}. See {declaration.position}."
                    )
                names.add(declaration.name)
                members[declaration.name] = declaration

            # ... repeat for units, domains, parameters, variables, equations ...

        return SymbolTable(
            names=names,
            members=members,
            dimensions=dimensions,
            categories=categories,
            domains=domains,
            units=units,
            parameters=parameters,
            variables=variables,
            equations=equations,
        )
