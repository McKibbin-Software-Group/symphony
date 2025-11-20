# symphony_ast.py
# Abstract Syntax Tree definitions and printers
from __future__ import annotations

from dataclasses import dataclass, is_dataclass, fields
from enum import Enum
from typing import Any, List, Optional, Tuple, Union

# ========= Core AST node types =========


@dataclass(frozen=True)
class SourcePosition:
    """
    1-based line/column location in the source file.
    """
    line: int
    column: int


class DeclType(str, Enum):
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

Documentation = Tuple[str, SourcePosition] # The content and position of a docstring documentation for an entity.


@dataclass(frozen=True)
class Declaration:
    """
    Base class for all top-level declarations.
    """
    decl_type: DeclType
    type_pos: SourcePosition

    name: str
    name_pos: SourcePosition

    label: str
    label_pos: SourcePosition

    doc: Optional[str]
    doc_pos: Optional[SourcePosition]


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
    
    `dimension_members` is the list of names of the members in this dimension
    """
    dimension_members: List[str]


@dataclass(frozen=True)
class CategoryDeclaration(DimensionDeclaration):
    """
    `category` NAME ":" label [name_list] doc?

    `dimension_members` is the list of names of the members in this category (a type of dimension)
    """
    pass

@dataclass(frozen=True)
class DimensionsDeclaration(Declaration):
    """
     "dimensions" NAME ":" label name_list doc?

    `dimensions` lists the name of each included dimension
    """
    dimensions: List[str]


@dataclass(frozen=True)
class DomainDeclaration(Declaration):
    """
    Domain declaration (exact syntax driven by the grammar).
    """
    tuples: List[DomainTuple]


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


DeclNode = Union[
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
class Program:
    """
    Root node: a flat list of declarations.
    """
    decls: List[DeclNode]


# ========= AST text / summary printers =========

def _is_pos_like(field_name: str, value: Any) -> bool:
    if field_name.endswith("_pos"):
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


def _dc_to_tree(node: Any, show_pos: bool) -> Tuple[str, List[Tuple[str, List[Tuple[str, list]]]]]:
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
        if not show_pos and _is_pos_like(f.name, val):
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
            kids = [_dc_to_tree(v, show_pos) for v in val]
            children.append((f"{name}[]", kids))
        else:
            klabel, kchildren = _dc_to_tree(val, show_pos)
            children.append((name, [(klabel, kchildren)]))
    return (label, children)


def ast_to_text(root: Any, show_pos: bool = False) -> str:
    """
    Pretty ASCII tree representation of the AST.
    """
    root_label, root_children = _dc_to_tree(root, show_pos)

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


def program_to_summary_text(program: Program, show_pos: bool = False) -> str:
    """
    Concise, one-line-per-declaration summary of a Program.
    """
    lines: List[str] = []
    for decl in program.decls:
        base = f"{decl.decl_type.value} {decl.name!r}: {decl.label!r}"
        extras: List[str] = []
        if isinstance(decl, CategoryDeclaration):
            extras.append(f"members={decl.dimension_members}")
        elif isinstance(decl, DimensionDeclaration):
            extras.append(f"members={decl.dimension_members}")
        if show_pos:
            extras.append(f"@{decl.type_pos.line}:{decl.type_pos.column}")
        if extras:
            base += "  (" + ", ".join(extras) + ")"
        lines.append(base)
    return "\n".join(lines)
