from __future__ import annotations
from lark import Token
from dataclasses import dataclass, replace
import logging
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from symphony import Diagnostic, DiagnosticBag, DiagnosticLabel, DiagnosticSeverity, SourcePosition, errors
from symphony.abstract_syntax_tree import (
    AnyDeclaration,
    CategoryDeclaration,
    Declaration,
    DeclarationType,
    DimensionDeclaration,
    DimensionExpression,
    DimensionReference,
    DomainDeclaration,
    EquationDeclaration,
    MemberDeclaration,
    Modules,
    ParameterDeclaration,
    UnitDeclaration,
    VariableDeclaration,
    NameList,
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
    diagnostics: DiagnosticBag

    @staticmethod
    def add_diagnostic(diagnostics: DiagnosticBag, position: SourcePosition, severity: DiagnosticSeverity, message: str, help_text: str) -> None:
        diagnostics.add(
            Diagnostic(
                code=errors.syntax_error,
                severity=severity,
                message=f"{message}",
                primary_label=DiagnosticLabel(
                    position=position,
                    message="The error occurred near here.",
                    is_primary=True,
                ),
                help_text=f"{help_text}",
            )
        )        
        pass

    def name_is_unique(declaration: Declaration, names: Dict[str, Declaration], diagnostics: DiagnosticBag) -> bool:
        """
        ### Overview
        
        Check if a declaration's name is unique within the symbol table.
        """
        if not hasattr(declaration, "name"):
            return True
        if declaration.name not in names:
            return True
        other_declaration: Declaration = names[declaration.name]
        SymbolTable.add_diagnostic(
            diagnostics,
            declaration.position,
            DiagnosticSeverity.error,
            f"Duplicate name: {declaration}.",
            f"{declaration} has a name clash with {other_declaration} at {other_declaration.position}",
        )
        return False

    @staticmethod
    def build(modules: Modules, diagnostics: DiagnosticBag) -> SymbolTable:
        names: Dict[str, AnyDeclaration] = {}
        members: Dict[str, MemberDeclaration] = {}
        dimensions: Dict[str, DimensionDeclaration] = {}
        categories: Dict[str, CategoryDeclaration] = {}
        domains: Dict[str, DomainDeclaration] = {}
        units: Dict[str, UnitDeclaration] = {}
        parameters: Dict[str, ParameterDeclaration] = {}
        variables: Dict[str, VariableDeclaration] = {}
        equations: Dict[str, EquationDeclaration] = {}

        for declaration in modules.declarations:

            if SymbolTable.name_is_unique(declaration, names, diagnostics):

                match declaration.__class__.__name__:
                    case CategoryDeclaration.__name__:
                        categories[declaration.name] = declaration
                        dimensions[declaration.name] = declaration
                    case DimensionDeclaration.__name__:
                        dimensions[declaration.name] = declaration
                    case MemberDeclaration.__name__:
                        members[declaration.name] = declaration
                    case DomainDeclaration.__name__:
                        domains[declaration.name] = declaration
                    case UnitDeclaration.__name__:
                        units[declaration.name] = declaration
                    case ParameterDeclaration.__name__:
                        parameters[declaration.name] = declaration
                    case VariableDeclaration.__name__:
                        variables[declaration.name] = declaration
                    case EquationDeclaration.__name__:
                        equations[declaration.name] = declaration
                    case _:
                        diagnostics.add(
                            Diagnostic(
                                code=errors.unexpected_declaration_type,
                                severity=DiagnosticSeverity.error,
                                message=f"Unexpected declaration type: {declaration}.",
                                primary_label=DiagnosticLabel(
                                    position=declaration.position,
                                    message="The unexpected declaration is here.",
                                    is_primary=True,
                                ),
                                help_text=f"The {declaration.__class__.__name__} declaration is not recognized.",
                            )
                        )
                names[declaration.name] = declaration

        symbol_table: SymbolTable = SymbolTable(
            names=names,
            members=members,
            dimensions=dimensions,
            categories=categories,
            domains=domains,
            units=units,
            parameters=parameters,
            variables=variables,
            equations=equations,
            diagnostics=diagnostics,
        )

        symbol_table.setup_members()

        symbol_table.setup_dimensions()

        return symbol_table
    
    def setup_members(self) -> None:
        """
        ### Overview
        
        Setup members in the symbol table.
        """
        processor = MemberProcessor(self)
        processor.process()

    def setup_dimensions(self) -> None:
        """
        ### Overview

        Setup dimensions in the symbol table.
        """
        dimension_processor = DimensionProcessor(self)
        dimension_processor.process()


MemberName = str
DimensionName = str

class MemberProcessor:

    def __init__(self, symbol_table: SymbolTable) -> None:
        self.symbol_table: SymbolTable = symbol_table

    # ---------------------------------------------------------------------
    # Public entry point
    # ---------------------------------------------------------------------

    def process(self) -> None:
        """
        Populate `MemberDeclaration.category` for every member in the symbol table.

        Validates the members on the way through.
        """

        for category_name, category in self.symbol_table.categories.items():
            
            # Ensure that each category has members that are in the symbol table
            for member_reference in category.members:
                if member_reference not in self.symbol_table.members:
                    SymbolTable.add_diagnostic(
                        self.diagnostics,
                        category.position,
                        DiagnosticSeverity.error,
                        f"Undefined member reference: {member_reference}.",
                        f"The member {member_reference} has not been declared.",
                    )

            # Set up references to category for each member.
            for member_reference in category.members:
                if member_reference in self.symbol_table.members:
                    member_declaration: MemberDeclaration = self.symbol_table.members[member_reference]
                    if member_declaration.category is None:
                        self.symbol_table.members[member_reference] = replace(
                            member_declaration,
                            category=category.name,
                        )
                        continue
                    elif member_declaration.category == category_name:
                        SymbolTable.add_diagnostic(
                            self.diagnostics,
                            category.position,
                            DiagnosticSeverity.error,
                            f"Member '{member_reference}' is repeated in the declaration of category '{member_declaration.category}'.",
                            f"Members must be assigned once to exactly one category.",
                        )
                    else:
                        SymbolTable.add_diagnostic(
                            self.diagnostics,
                            category.position,
                            DiagnosticSeverity.error,
                            f"Member '{member_reference}' belongs to multiple categories: '{member_declaration.category}' and '{category_name}'.",
                            f"Members must be assigned once to exactly one category.",
                        )

        # Ensure that all members belong to a category.
        for member_name, member in self.symbol_table.members.items():
            if member.category is None:
                SymbolTable.add_diagnostic(
                    self.diagnostics,
                    member.position,
                    DiagnosticSeverity.error,
                    f"Member '{member_name}' is not assigned to any category.",
                    f"Members must be assigned to exactly one category.",
                )


class DimensionProcessor:

    def __init__(self, symbol_table: SymbolTable) -> None:
        self.symbol_table: SymbolTable = symbol_table

    # ---------------------------------------------------------------------
    # Public entry point
    # ---------------------------------------------------------------------

    def process(self) -> None:
        """
        Populate `DimensionDeclaration.members` for every dimension in the symbol table.

        This pass:
        1) Builds a dependency graph between dimensions (A depends on B if A references B).
        2) Topologically sorts the dependency graph and detects cycles.
        3) Evaluates each dimension expression left-to-right, producing a stable order.

        Validates the dimensions on the way through.
        """

        dependency_graph: Dict[DimensionName, Set[DimensionName]] = self._build_dependency_graph()
        evaluation_order: Optional[List[DimensionName]] = self._topological_sort_dimensions(dependency_graph)

        if evaluation_order is None:
            return

        for dimension_name in evaluation_order:
            dimension_declaration: DimensionDeclaration = self.symbol_table.dimensions[dimension_name]
            if dimension_declaration.type == DeclarationType.category:
                continue
            resolved_members: Optional[Tuple[MemberName, ...]] = self._evaluate_dimension_expression(dimension_declaration)
            if resolved_members is None:
                continue

            # Ensure that all members are in the same category.
            dimension_category: str = None
            for member_name in resolved_members:
                if member_name not in self.symbol_table.members:
                    SymbolTable.add_diagnostic(
                        self.diagnostics,
                        dimension_declaration.position,
                        DiagnosticSeverity.error,
                        f"Member '{dimension_name}' includes a member that is not declared: '{member_name}'.",
                        f"All members must be declared.",
                    )
                member_declaration: MemberDeclaration = self.symbol_table.members[member_name]
                if dimension_category is None:
                    dimension_category = member_declaration.category
                else:
                    if member_declaration.category != dimension_category:
                        self._add_error(
                            position=dimension_declaration.position,
                            message=f"Member '{member_name}' in dimension '{dimension_name}' does not belong to category '{dimension_category}'.",
                            help_text="Ensure all members in a dimension expression belong to the same category.",
                        )

            # Sort the resolved members into the same order as the members in the category.
            category_declaration: CategoryDeclaration = self.symbol_table.categories[dimension_category]
            sorted_members: List[MemberName] = []
            for category_member in category_declaration.members:
                if category_member in resolved_members:
                    sorted_members.append(category_member)

            self.symbol_table.dimensions[dimension_name] = replace(
                dimension_declaration,
                members=tuple(sorted_members),
            )

    # ---------------------------------------------------------------------
    # Dependency graph
    # ---------------------------------------------------------------------

    def _build_dependency_graph(self) -> Dict[DimensionName, Set[DimensionName]]:
        """
        Return prerequisites for each dimension: graph[A] = {B, C, ...} meaning A depends on B and C.

        Only references to *dimensions* create prerequisites.
        References to categories are expanded at evaluation time.
        """
        dependency_graph: Dict[DimensionName, Set[DimensionName]] = {
            dimension_name: set() for dimension_name in self.symbol_table.dimensions.keys()
        }

        # Iterate over the dimension declarations
        for dimension_name, dimension_declaration in self.symbol_table.dimensions.items():
            if dimension_declaration.type == DeclarationType.category:
                continue
            expression: Optional[DimensionExpression] = dimension_declaration.expression
            if expression is None:
                continue
            for referenced_name in self._dimension_references_in_expression(expression):
                if referenced_name == dimension_name:
                    self._add_error(
                        position=expression.position,
                        message=f"Dimension '{dimension_name}' references itself.",
                        help_text="Remove the self-reference or rewrite the dimension expression.",
                    )
                    continue

                if referenced_name in self.symbol_table.dimensions:
                    dependency_graph[dimension_name].add(referenced_name)
                    continue

                if referenced_name in self.symbol_table.categories:
                    continue

                self._add_error(
                    position=expression.position,
                    message=f"Unknown dimension/category reference '{referenced_name}' in dimension '{dimension_name}'.",
                    help_text="Declare the referenced dimension or category, or correct the name.",
                )

        return dependency_graph

    def _dimension_references_in_expression(self, expression: DimensionExpression) -> Iterable[str]:
        for element in expression.elements:
            if isinstance(element, DimensionReference):
                yield element.dimension

    def _topological_sort_dimensions(
        self,
        dependency_graph: Dict[DimensionName, Set[DimensionName]],
    ) -> Optional[List[DimensionName]]:
        """
        Kahn's algorithm on a prerequisite graph.

        Returns an evaluation order where all prerequisites of a dimension appear earlier.
        Returns None (and reports an error) if a cycle is detected.
        """
        reverse_graph: Dict[DimensionName, Set[DimensionName]] = {name: set() for name in dependency_graph.keys()}
        for dimension_name, prerequisites in dependency_graph.items():
            for prerequisite in prerequisites:
                reverse_graph[prerequisite].add(dimension_name)

        in_degree_by_dimension: Dict[DimensionName, int] = {
            dimension_name: len(prerequisites) for dimension_name, prerequisites in dependency_graph.items()
        }

        ready: List[DimensionName] = sorted([name for name, in_degree in in_degree_by_dimension.items() if in_degree == 0])
        ordered: List[DimensionName] = []

        while ready:
            current: DimensionName = ready.pop(0)
            ordered.append(current)

            for dependent in sorted(reverse_graph[current]):
                in_degree_by_dimension[dependent] -= 1
                if in_degree_by_dimension[dependent] == 0:
                    ready.append(dependent)
            ready.sort()

        if len(ordered) != len(dependency_graph):
            cyclic_nodes: List[DimensionName] = sorted(
                [name for name, in_degree in in_degree_by_dimension.items() if in_degree > 0]
            )
            position: SourcePosition = self._cycle_position_fallback(cyclic_nodes)
            self._add_error(
                position=position,
                message=f"Cycle detected among dimensions: {', '.join(cyclic_nodes)}",
                help_text="Rewrite the expressions so dimensions do not (directly or indirectly) reference each other in a cycle.",
            )
            return None

        return ordered

    def _cycle_position_fallback(self, cyclic_nodes: Sequence[DimensionName]) -> SourcePosition:
        for node_name in cyclic_nodes:
            return self.symbol_table.dimensions[node_name].position
        # If there are truly no expressions, fabricate a minimal position.
        return SourcePosition(file_path=self.symbol_table.root_file_path if hasattr(self.symbol_table, "root_file_path") else None, line=1, column=1)

    # ---------------------------------------------------------------------
    # Expression evaluation
    # ---------------------------------------------------------------------

    def _evaluate_dimension_expression(
        self,
        dimension_declaration: DimensionDeclaration,
    ) -> Optional[Tuple[MemberName, ...]]:
                
        expression: Optional[DimensionExpression] = dimension_declaration.expression
        if expression is None:
            return tuple()

        parsed = self._parse_dimension_expression_elements(expression)
        if parsed is None:
            self._add_error(
                position=expression.position,
                message=f"Invalid dimension expression for dimension '{dimension_declaration.name}'.",
                help_text="Ensure the dimension expression follows the grammar: term (('+'|'-') term)*.",
            )
            return None

        first_term, operator_term_pairs = parsed

        current_members: Optional[List[MemberName]] = self._term_members(first_term, expression.position, dimension_declaration.name)
        if current_members is None:
            return None
        current_members = self._unique_preserve_order(current_members)

        for operator_token, term in operator_term_pairs:
            right_members: Optional[List[MemberName]] = self._term_members(term, expression.position, dimension_declaration.name)
            if right_members is None:
                return None

            if operator_token.type == "PLUS":
                current_members = self._unique_preserve_order(current_members + right_members)
            elif operator_token.type == "MINUS":
                removal_set: Set[MemberName] = set(right_members)
                current_members = [name for name in current_members if name not in removal_set]
            else:
                self._add_error(
                    position=expression.position,
                    message=f"Unexpected set operator '{operator_token}' in dimension '{dimension_declaration.name}'.",
                    help_text="Only '+' and '-' are valid in dimension expressions.",
                )
                return None

        # Optional: warn on implicit member names.
        for member_name in current_members:
            if member_name not in self.symbol_table.members:
                self._add_warning(
                    position=expression.position,
                    message=f"Member '{member_name}' used in dimension '{dimension_declaration.name}' is not declared with 'member'.",
                    help_text="Declare the member or confirm your model allows implicit member names.",
                )

        return tuple(current_members)

    def _parse_dimension_expression_elements(
        self,
        expression: DimensionExpression,
    ) -> Optional[Tuple[object, List[Tuple[Token, object]]]]:
        elements: Tuple[object, ...] = expression.elements
        if not elements:
            return None

        first_term: object = elements[0]
        if not self._is_dimension_term(first_term):
            return None

        if (len(elements) - 1) % 2 != 0:
            return None

        operator_term_pairs: List[Tuple[Token, object]] = []
        index: int = 1
        while index < len(elements):
            operator = elements[index]
            term = elements[index + 1]

            if not isinstance(operator, Token):
                return None
            if operator.type not in {"PLUS", "MINUS"}:
                return None
            if not self._is_dimension_term(term):
                return None

            operator_term_pairs.append((operator, term))
            index += 2

        return first_term, operator_term_pairs

    def _is_dimension_term(self, term: object) -> bool:
        return isinstance(term, (NameList, DimensionReference))

    def _term_members(
        self,
        term: object,
        position: SourcePosition,
        dimension_name: str,
    ) -> Optional[List[MemberName]]:
        if isinstance(term, NameList):
            if term.kind != "member":
                self._add_error(
                    position=position,
                    message=f"Unexpected NameList kind '{term.kind}' inside a dimension expression for '{dimension_name}'.",
                    help_text="Only member lists are valid inside dimension expressions.",
                )
                return None
            return list(term.items)

        if isinstance(term, DimensionReference):
            referenced_name: str = term.dimension

            if referenced_name in self.symbol_table.dimensions:
                referenced_dimension: DimensionDeclaration = self.symbol_table.dimensions[referenced_name]
                if referenced_dimension.members is None:
                    self._add_error(
                        position=position,
                        message=f"Dimension '{dimension_name}' references dimension '{referenced_name}' before it is resolved.",
                        help_text="This is usually caused by a cycle or incorrect evaluation order.",
                    )
                    return None
                return list(referenced_dimension.members)

            if referenced_name in self.symbol_table.categories:
                category: CategoryDeclaration = self.symbol_table.categories[referenced_name]
                return list(category.members.items)

            self._add_error(
                position=position,
                message=f"Unknown dimension/category reference '{referenced_name}' in dimension '{dimension_name}'.",
                help_text="Declare the referenced dimension or category, or correct the name.",
            )
            return None

        self._add_error(
            position=position,
            message=f"Unexpected term type '{type(term).__name__}' in dimension '{dimension_name}'.",
            help_text="This is likely an AST construction bug; inspect the transformer output.",
        )
        return None

    # ---------------------------------------------------------------------
    # Diagnostics helpers
    # ---------------------------------------------------------------------

    def _add_error(self, position: SourcePosition, message: str, help_text: str) -> None:
        SymbolTable.add_diagnostic(
            diagnostics=self.symbol_table.diagnostics,
            position=position,
            severity=DiagnosticSeverity.error,
            message=message,
            help_text=help_text,
        )

    def _add_warning(self, position: SourcePosition, message: str, help_text: str) -> None:
        SymbolTable.add_diagnostic(
            diagnostics=self.symbol_table.diagnostics,
            position=position,
            severity=DiagnosticSeverity.warning,
            message=message,
            help_text=help_text,
        )

    @staticmethod
    def _unique_preserve_order(items: Sequence[str]) -> List[str]:
        seen: Set[str] = set()
        result: List[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result
