from __future__ import annotations
from lark import Token
from dataclasses import dataclass, replace
import logging
import itertools
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
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
    DomainExpression,
    DomainTerm,
    EquationDeclaration,
    MemberDeclaration,
    Modules,
    ParameterDeclaration,
    TupleCondition,
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

        logging.debug(len(modules.declarations))

        for declaration in modules.declarations:

            # logging.debug(f"### Symbol tabling {declaration.type.value} {declaration.name}")
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

        symbol_table.setup_domains()

        if symbol_table.diagnostics.has_errors():
            symbol_table.diagnostics.report_diagnostics()
            return None
        
        elif symbol_table.diagnostics.has_warnings():
            symbol_table.diagnostics.report_diagnostics()
        
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

    def setup_domains(self) -> None:
        """
        ### Overview

        Setup domains in the symbol table.
        """
        domain_processor = DomainProcessor(self)
        domain_processor.process()


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


DomainName = str


class DomainProcessor:
    """
    Resolve domain expressions into concrete tuples of member names.

    Each resolved domain is written back to `DomainDeclaration.tuples`
    as a tuple of tuples.

    Implemented semantics (matching the grammar intent):

    - A domain term may be:
        * A reference to a previously-declared domain (singleton name list)
        * A list of one or more dimensions/categories, interpreted as a cartesian product
        * A list of one or more members, interpreted as a 1-D domain containing those members

    - A domain expression is evaluated left-to-right with:
        * '+' meaning ordered union (append any new tuples)
        * '-' meaning ordered difference (remove tuples)

    - Tuple conditions filter tuples after a term is expanded.
      Tuple positions are treated as 1-based indices.
    """

    def __init__(self, symbol_table: SymbolTable) -> None:
        self.symbol_table: SymbolTable = symbol_table
        self.diagnostics: DiagnosticBag = symbol_table.diagnostics

    # ---------------------------------------------------------------------
    # Public entry point
    # ---------------------------------------------------------------------

    def process(self) -> None:
        """
        Populate `DomainDeclaration.tuples` for every domain in the symbol table.

        This pass:
        1) Builds a dependency graph between domains (A depends on B if A references B).
        2) Topologically sorts the dependency graph and detects cycles.
        3) Evaluates each domain expression left-to-right, producing a stable order.

        Diagnostics are recorded on invalid references, arity mismatches, and cycles.
        """

        dependency_graph: Dict[DomainName, Set[DomainName]] = self._build_dependency_graph()
        ordered_domains: Optional[List[DomainName]] = self._topological_sort_domains(dependency_graph)

        for domain_name in ordered_domains:
            domain_declaration: DomainDeclaration = self.symbol_table.domains[domain_name]
            resolved: Optional[Tuple[Tuple[str, ...], ...]] = self._evaluate_domain_declaration(domain_declaration)
            if resolved is None:
                continue
            self.symbol_table.domains[domain_name] = replace(domain_declaration, tuples=resolved)

    # ---------------------------------------------------------------------
    # Dependency graph + topo sort
    # ---------------------------------------------------------------------

    def _build_dependency_graph(self) -> Dict[DomainName, Set[DomainName]]:
        """
        Return prerequisites for each domain: graph[A] = {B, C, ...} meaning A depends on B and C.

        Only references to *domains* create prerequisites.
        """
        dependency_graph: Dict[DomainName, Set[DomainName]] = {
            domain_name: set() for domain_name in self.symbol_table.domains.keys()
        }

        for domain_name, domain_declaration in self.symbol_table.domains.items():
            expression: Optional[DomainExpression] = domain_declaration.expression
            if expression is None:
                continue

            for referenced_domain in self._domain_references_in_expression(expression):
                logging.debug(f"Domain '{domain_name}' references domain '{referenced_domain}'")
                if referenced_domain == domain_name:
                    self._add_error(
                        position=expression.position,
                        message=f"Domain '{domain_name}' references itself.",
                        help_text="Remove the self-reference or rewrite the domain expression.",
                    )
                    continue

                if referenced_domain in self.symbol_table.domains:
                    dependency_graph[domain_name].add(referenced_domain)

        return dependency_graph

    def _domain_references_in_expression(self, expression: DomainExpression) -> Iterable[str]:
        """
        Yield any names that are interpreted as domain references: singleton term lists
        whose single item matches a declared domain name.
        """
        for domain_term in self._iterate_domain_terms(expression):
            name_list: NameList = domain_term.domain_list
            items: Tuple[str, ...] = name_list.items
            if len(items) == 1 and items[0] in self.symbol_table.domains:
                yield items[0]

    def _iterate_domain_terms(self, expression: DomainExpression) -> Iterable[DomainTerm]:
        yield expression.first
        for _, term in expression.rest:
            yield term

    def _topological_sort_domains(
        self, dependency_graph: Dict[DomainName, Set[DomainName]]
    ) -> Optional[List[DomainName]]:
        """
        Kahn topological sort using prerequisite sets.
        """
        in_degree_by_domain: Dict[DomainName, int] = {name: 0 for name in dependency_graph.keys()}
        dependents_by_domain: Dict[DomainName, Set[DomainName]] = {name: set() for name in dependency_graph.keys()}

        for domain, prerequisites in dependency_graph.items():
            for prerequisite in prerequisites:
                if prerequisite not in in_degree_by_domain:
                    continue
                in_degree_by_domain[domain] += 1
                dependents_by_domain[prerequisite].add(domain)

        ready: List[DomainName] = sorted([name for name, indegree in in_degree_by_domain.items() if indegree == 0])
        ordered: List[DomainName] = []

        while ready:
            node: DomainName = ready.pop(0)
            ordered.append(node)

            for dependent in sorted(dependents_by_domain.get(node, set())):
                in_degree_by_domain[dependent] -= 1
                if in_degree_by_domain[dependent] == 0:
                    ready.append(dependent)
            ready.sort()

        if len(ordered) != len(dependency_graph):
            cyclic_nodes: List[DomainName] = sorted(
                [name for name, in_degree in in_degree_by_domain.items() if in_degree > 0]
            )
            position: SourcePosition = self._cycle_position_fallback(cyclic_nodes)
            self._add_error(
                position=position,
                message=f"Cycle detected among domains: {', '.join(cyclic_nodes)}",
                help_text="Rewrite the expressions so domains do not (directly or indirectly) reference each other in a cycle.",
            )
            return []

        return ordered

    def _cycle_position_fallback(self, cyclic_nodes: Sequence[DomainName]) -> SourcePosition:
        for node_name in cyclic_nodes:
            return self.symbol_table.domains[node_name].position
        return SourcePosition(
            file_path=getattr(self.symbol_table, "root_file_path", None),
            line=1,
            column=1,
        )

    # ---------------------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------------------

    def _evaluate_domain_declaration(
        self, domain_declaration: DomainDeclaration
    ) -> Optional[Tuple[Tuple[str, ...], ...]]:
        """
        ### Overview
        
        Evaluate a domain declaration's expression into concrete tuples of member names.
        
        Returns None on error.
        """

        domain_expression: Optional[DomainExpression] = domain_declaration.expression
        
        # Return the empty set for domains with no expression. That is a unique
        # domain itself.
        if domain_expression is None:
            return tuple()

        # Process the terms in the domain expression from left to right.
        current: Optional[List[Tuple[str, ...]]] = self._evaluate_domain_term(
            domain_declaration_name=domain_declaration.name,
            term=domain_expression.first,
        )
        if current is None:
            return None
        current = self._unique_preserve_order(current)

        for operator, term in domain_expression.rest:
            right: Optional[List[Tuple[str, ...]]] = self._evaluate_domain_term(
                domain_declaration_name=domain_declaration.name,
                term=term,
            )
            if right is None:
                return None

            if operator == "+":
                current = self._unique_preserve_order(current + right)
            elif operator == "-":
                removal_set: Set[Tuple[str, ...]] = set(right)
                current = [t for t in current if t not in removal_set]
            else:
                self._add_error(
                    position=term.position,
                    message=f"Unknown set operator '{operator}' in domain '{domain_declaration.name}'.",
                    help_text="Only '+' (union) and '-' (difference) are supported in domain expressions.",
                )
                return None

        # Ensure all members with the same position, across all tuples, belong to the same category.
        if current:
            arity: int = len(current[0])
            for position_index in range(arity):
                category_name: Optional[str] = None
                for tuple_value in current:
                    member_name: str = tuple_value[position_index]
                    if member_name not in self.symbol_table.members:
                        self._add_error(
                            position=domain_declaration.position,
                            message=f"Member '{member_name}' used in domain '{domain_declaration.name}' is not declared.",
                            help_text="Declare the member or confirm your model allows implicit member names.",
                        )
                        continue
                    member_declaration: MemberDeclaration = self.symbol_table.members[member_name]
                    if category_name is None:
                        category_name = member_declaration.category
                    else:
                        if member_declaration.category != category_name:
                            self._add_error(
                                position=domain_declaration.position,
                                message=f"Member '{member_name}' in position {position_index + 1} of domain '{domain_declaration.name}' does not belong to category '{category_name}'.",
                                help_text="Ensure all members in the same position across tuples belong to the same category.",
                            )

        # Sort the tuples to match the order of members in their categories, position by position.
        # Do so by calculating a score for each tuple based on tuple positions and values
        # and sorting using this score.
        if current:
            arity: int = len(current[0])
            sorting_scores: list[int] = np.zeros(len(current), dtype=int).tolist()
            position_weights = [10 ** (arity - i - 1) for i in range(arity)]
            for position_index in range(arity):
                category_name: Optional[str] = None
                tuple_index: int = 0
                for tuple_value in current:
                    member_name: str = tuple_value[position_index]
                    if member_name in self.symbol_table.members:
                        member_declaration: MemberDeclaration = self.symbol_table.members[member_name]
                        category_name = member_declaration.category
                        category_declaration: CategoryDeclaration = self.symbol_table.categories[category_name]
                        member_position: int = category_declaration.members.index(member_name)
                        sorting_scores[tuple_index] += member_position * position_weights[position_index]
                    tuple_index += 1
            # Sort the current tuples by the computed scores.
            sorted_indices: List[int] = sorted(range(len(current)), key=lambda i: sorting_scores[i])
            current = [current[i] for i in sorted_indices]

        return tuple(current)

    def _evaluate_domain_term(
        self, *, domain_declaration_name: str, term: DomainTerm
    ) -> Optional[List[Tuple[str, ...]]]:
        """
        ### Overview
        
        Evaluate a single domain term into concrete tuples of member names.

        Returns None on error.
        """
        name_list: NameList = term.domain_list
        base: Optional[List[Tuple[str, ...]]] = self._expand_domain_list(
            domain_declaration_name=domain_declaration_name,
            position=term.position,
            items=name_list.items,
        )
        if base is None:
            return None

        logging.debug(f"Expanded domain term in domain '{domain_declaration_name}': {term.tuple_conditions}")

        # Now apply any tuple conditions to filter the base tuples.
        if term.tuple_conditions:
            logging.info(f"Applying tuple conditions in domain '{domain_declaration_name}': {term.tuple_conditions}")
            arity: int = len(base[0]) if base else 0 # The number of positions in each tuple.
            filtered: List[Tuple[str, ...]] = []
            for tuple_value in base:
                if self._tuple_satisfies_conditions(
                    tuple_value=tuple_value,
                    conditions=term.tuple_conditions,
                    arity=arity,
                    position=term.position,
                    domain_declaration_name=domain_declaration_name,
                ):
                    filtered.append(tuple_value)
            base = filtered
        # exit("testing tuple conditions usage")
        return base

    def _expand_domain_list(
        self,
        *,
        domain_declaration_name: str,
        position: SourcePosition,
        items: Tuple[str, ...],
    ) -> Optional[List[Tuple[str, ...]]]:
        """
        ### Overview
        
        Expand a NameList in a domain term into concrete tuples of member names.
        
        Returns None on error.
        """
        if len(items) == 0:
            self._add_error(
                position=position,
                message=f"Empty domain term in domain '{domain_declaration_name}'.",
                help_text="A domain term must reference a domain, one or more dimensions/categories, or one or more members.",
            )
            return None

        # Singleton: try domain reference, then dimension/category, then member.
        if len(items) == 1:
            name: str = items[0]

            # Handle singleton domain reference.
            if name in self.symbol_table.domains:
                referenced_domain: DomainDeclaration = self.symbol_table.domains[name]
                if referenced_domain.tuples is None:
                    self._add_error(
                        position=position,
                        message=f"Domain '{domain_declaration_name}' references domain '{name}' which could not be resolved.",
                        help_text="Fix errors in the referenced domain, or break dependency cycles.",
                    )
                    return None
                return [tuple(t) for t in referenced_domain.tuples]

            # Handle singleton dimension/category reference.
            dimension_members: Optional[Tuple[str, ...]] = self._members_for_dimension_or_category(name)
            if dimension_members is not None:
                return [(member_name,) for member_name in dimension_members]

            # Handle singleton member reference.
            if name in self.symbol_table.members:
                return [(name,)]

            self._add_error(
                position=position,
                message=f"Unknown reference '{name}' in domain '{domain_declaration_name}'.",
                help_text="Declare a domain, dimension/category, or member with this name, or correct the spelling.",
            )
            return None

        # Multi-name: either all dimensions/categories (cartesian product) or all members (1-D explicit set).
        dimension_name_list: List[str] = []
        member_name_list: List[str] = []
        unknown_names: List[str] = []

        for name in items:
            if name in self.symbol_table.members:
                member_name_list.append(name)
                continue
            if name in self.symbol_table.dimensions:
                dimension_name_list.append(name)
                continue
            if name in self.symbol_table.domains:
                self._add_error(
                    position=position,
                    message=f"Domain '{domain_declaration_name}' includes domain reference '{name}' in a multi-name list.",
                    help_text="Use a singleton domain reference, or list dimensions (or members) only.",
                )
                return None
            unknown_names.append(name)

        if unknown_names:
            logging.debug(f"Unknown names in domain '{domain_declaration_name}': {unknown_names}")
            self._add_error(
                position=position,
                message=f"Unknown reference(s) in domain '{domain_declaration_name}': {', '.join(unknown_names)}.",
                help_text="Add the necessary declarations or correct their spelling.",
            )
            return None

        if dimension_name_list and member_name_list:
            self._add_error(
                position=position,
                message=f"Mixed dimension/category names and member names in domain '{domain_declaration_name}'.",
                help_text="A domain term must be either a list of dimensions/categories (cartesian product) or a list of members.",
            )
            return None

        if member_name_list:
            return [(member_name,) for member_name in member_name_list]

        member_lists: List[Tuple[str, ...]] = []
        for dimension_name in dimension_name_list:
            members: Optional[Tuple[str, ...]] = self._members_for_dimension_or_category(dimension_name)
            if members is None:
                self._add_error(
                    position=position,
                    message=f"Dimension/category '{dimension_name}' has no resolved members (referenced from domain '{domain_declaration_name}').",
                    help_text="Fix errors in the referenced dimension/category first.",
                )
                return None
            member_lists.append(members)

        tuples: List[Tuple[str, ...]] = [tuple(product_tuple) for product_tuple in itertools.product(*member_lists)]
        return tuples

    def _members_for_dimension_or_category(self, name: str) -> Optional[Tuple[str, ...]]:
        if name in self.symbol_table.dimensions:
            dimension_declaration: DimensionDeclaration = self.symbol_table.dimensions[name]
            return dimension_declaration.members or tuple()
        return None

    def _tuple_satisfies_conditions(
        self,
        *,
        tuple_value: Tuple[str, ...],
        conditions: Tuple[TupleCondition, ...],
        arity: int,
        position: SourcePosition,
        domain_declaration_name: str,
    ) -> bool:
        """
        ### Overview

        Check whether a tuple satisfies all given conditions.
       
        ### Arguments

        - `tuple_value`: The tuple to check.
        - `conditions`: The conditions to check against.
        - `arity`: The number of positions in the tuple.
        - `position`: The source position for diagnostics.
        - `domain_declaration_name`: The name of the domain for diagnostics.

        Returns True if all conditions are satisfied, False otherwise.
        
        """
        for condition in conditions:
            left_index: int = condition.left_position - 1
            right_index: int = condition.right_position - 1

            if left_index < 0 or right_index < 0 or left_index >= arity or right_index >= arity:
                self._add_error(
                    position=position,
                    message=(
                        f"Tuple condition uses out-of-range tuple position(s) "
                        f"({condition.left_position} {condition.operator} {condition.right_position}) "
                        f"in domain '{domain_declaration_name}' (arity {arity})."
                    ),
                    help_text="Tuple positions are 1-based indices into the tuple; ensure they are within the number of dimensions in the term.",
                )
                return False

            if condition.operator == "=":
                if tuple_value[left_index] != tuple_value[right_index]:
                    return False
            elif condition.operator == "!=":
                if tuple_value[left_index] == tuple_value[right_index]:
                    return False
            else:
                self._add_error(
                    position=position,
                    message=f"Unknown tuple condition operator '{condition.operator}' in domain '{domain_declaration_name}'.",
                    help_text="Only '=' and '!=' are supported in tuple conditions.",
                )
                return False

        return True

    # ---------------------------------------------------------------------
    # Small utilities
    # ---------------------------------------------------------------------

    def _unique_preserve_order(self, items: Sequence[Tuple[str, ...]]) -> List[Tuple[str, ...]]:
        """
        ### Overview
        
        Generates a list of unique tuples, preserving their original order.
        
        """
        seen: Set[Tuple[str, ...]] = set()
        result: List[Tuple[str, ...]] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result

    def _add_error(self, *, position: SourcePosition, message: str, help_text: str) -> None:
        SymbolTable.add_diagnostic(self.diagnostics, position, DiagnosticSeverity.error, message, help_text)
