# symphony_model.py
# TODO: Eventually to be replaced fully by a mult-pass processor.
# # symbol tables and model object
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from abstract_syntax_tree import (
    CategoryDeclaration,
    DeclarationNode,
    DimensionDeclaration,
    MemberDeclaration,
    Program,
)


@dataclass
class SymbolTables:
    """
    Simple semantic view of a Program.

    This mirrors (and persists) the symbol tables that the ToAST transformer
    builds transiently while parsing.
    """
    members: Set[str] = field(default_factory=set)
    member_category: Dict[str, str] = field(default_factory=dict)
    categories: Dict[str, List[str]] = field(default_factory=dict)
    dimensions: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class Model:
    """
    Higher-level representation of the .sym model for downstream consumers.
    """
    program: Program
    symbols: SymbolTables


class ModelBuilder:
    """
    Build a Model (AST + symbol tables) from a Program AST.
    """

    def build(self, program: Program) -> Model:
        symbols = SymbolTables()

        for decl in program.decls:
            self._visit_decl(decl, symbols)

        return Model(program=program, symbols=symbols)

    def _visit_decl(self, decl: DeclarationNode, symbols: SymbolTables) -> None:
        if isinstance(decl, MemberDeclaration):
            if decl.name in symbols.members:
                # The transformer already enforces uniqueness; treat this as a sanity check.
                raise ValueError(f"Duplicate member '{decl.name}' in Program AST.")
            symbols.members.add(decl.name)

        elif isinstance(decl, CategoryDeclaration):
            symbols.categories[decl.name] = list(decl.dimension_members)
            for member in decl.dimension_members:
                if member in symbols.member_category:
                    prev = symbols.member_category[member]
                    raise ValueError(
                        f"Member '{member}' appears in both category '{prev}' and '{decl.name}'."
                    )
                symbols.member_category[member] = decl.name

        elif isinstance(decl, DimensionDeclaration):
            symbols.dimensions[decl.name] = list(decl.dimension_members)
        else:
            # Other declaration types currently do not contribute to these symbol tables.
            pass
