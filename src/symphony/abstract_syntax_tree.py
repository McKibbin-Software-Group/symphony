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
]


@dataclass(frozen=True)
class Model:
    """
    Root node: a flat list of declarations.
    """
    declarations: List[DeclarationNode]


# ========= AST text / summary printers =========

def _is_position_like(field_name: str, value: Any) -> bool:
    if field_name.endswith("_position"):
        return True
    if is_dataclass(value):
        tname = type(value).__name__
        if tname.lower().endswith("position"):
            value_field_names = {f.name for f in fields(value)}
            return {"line", "column"}.issubset(value_field_names)
    return False


def _format_inline_value(val: Any) -> str:
    """
    Render a scalar value inline for the tree printer.
    """
    if isinstance(val, Enum):
        return repr(val.value)
    sval = repr(val)
    if isinstance(val, str) and len(val) > 60:
        sval = repr(val[:57] + "...")
    return sval


def _dataclass_to_tree(node: Any, show_pos: bool) -> Tuple[str, List[Tuple[str, List[Tuple[str, list]]]]]:
    """
    Convert a dataclass instance into a generic (label, children) tree.
    """
    if not is_dataclass(node):
        return (repr(node), [])

    tname: str = type(node).__name__
    inline_bits: List[str] = [tname]
    child_slots: List[Tuple[str, Any]] = []

    for f in fields(node):
        val = getattr(node, f.name)

        # Hide position-like fields when show_pos is False
        if not show_pos and _is_position_like(f.name, val):
            continue

        if is_dataclass(val):
            child_slots.append((f.name, val))
        elif isinstance(val, list):
            # Lists are expanded into children; we do not print them inline
            child_slots.append((f.name, val))
        else:
            inline_bits.append(f"{f.name}={_format_inline_value(val)}")

    label = " ".join(inline_bits)

    children: List[Tuple[str, List[Tuple[str, list]]]] = []
    for name, val in child_slots:
        if isinstance(val, list):
            kids = [_dataclass_to_tree(v, show_pos) for v in val]
            children.append((f"{name}[]", kids))
        else:
            klabel, kchildren = _dataclass_to_tree(val, show_pos)
            children.append((name, [(klabel, kchildren)]))
    return (label, children)


def abstract_syntax_tree_to_text(root: Any, show_position: bool = False) -> str:
    """
    Pretty ASCII tree representation of the AST.
    """
    root_label, root_children = _dataclass_to_tree(root, show_position)

    def walk(label: str, kids: List[Tuple[str, List[Tuple[str, list]]]], indent: str = "") -> List[str]:
        lines: List[str] = [f"{indent}{label}"]
        for edge_label, gc in kids:
            lines.append(f"{indent}├─ {edge_label}")
            for i, (cl, ck) in enumerate(gc):
                prefix: str = "│   " if i < len(gc) - 1 else "    "
                lines.append(f"{indent}{prefix}{cl}")
                if ck:
                    lines.extend(walk(cl, ck, indent + prefix)[1:])
        return lines

    return "\n".join(walk(root_label, root_children))


def program_to_summary_text(program: Model, show_position: bool = False) -> str:
    """
    Concise, one-line-per-declaration summary of a model declaration.

    ### Arguments

    - `program`: The root abstract syntax tree node for the model declaration.
    - `show_pos`: If `True`, include source position information for each declaration.

    ### Returns

    A multi-line string summarizing each declaration.
    """
    lines: List[str] = []
    for declaration in program.declarations:
        base = f"{declaration.declaration_type.value} {declaration.name!r}: {declaration.label!r}"
        extras: List[str] = []
        if isinstance(declaration, CategoryDeclaration):
            extras.append(f"members={declaration.dimension_members}")
        elif isinstance(declaration, DimensionDeclaration):
            extras.append(f"members={declaration.dimension_members}")
        if show_position:
            extras.append(f"@{declaration.type_position.line}:{declaration.type_position.column}")
        if extras:
            base += "  (" + ", ".join(extras) + ")"
        if declaration.documentation:
            doc_preview = declaration.documentation
            if len(doc_preview) > 30:
                doc_preview = doc_preview[:27] + "..."
            base += f"  // doc={doc_preview!r}"
        lines.append(base)
    return "\n".join(lines)
