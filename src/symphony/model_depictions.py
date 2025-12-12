from __future__ import annotations
from dataclasses import is_dataclass, fields
from typing import Any, List, Tuple
from enum import Enum
from symphony.abstract_syntax_tree import (
    CategoryDeclaration,
    AnyDeclaration,
    DimensionDeclaration,
    Model,
)


def model_to_tree(root: Any, show_position: bool = False) -> str:
    """
    Pretty ASCII tree representation of the AST.
    """
    root_label, root_children = _dataclass_to_tree(root, show_position)

    def walk(
        label: str, kids: List[Tuple[str, List[Tuple[str, list]]]], indent: str = ""
    ) -> List[str]:
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


def model_to_summary(model: Model, show_position: bool = False) -> str:
    """
    Concise, one-line-per-declaration summary of a model declaration.

    ### Arguments

    - `program`: The root abstract syntax tree node for the model declaration.
    - `show_pos`: If `True`, include source position information for each declaration.

    ### Returns

    A multi-line string summarizing each declaration.
    """
    lines: List[str] = []
    for category in model.categories.values():
        base = f"Category {category.name!r}: {category.label!r}"
        extras: List[str] = []
        if show_position:
            extras.append(f"@{category.position.line}:{category.position.column}")
        if extras:
            base += "  (" + ", ".join(extras) + ")"
        if category.documentation:
            doc_preview = category.documentation[0]
            if len(doc_preview) > 30:
                doc_preview = doc_preview[:27] + "..."
            base += f"  // doc={doc_preview!r}"
        lines.append(base)

        for member_name in category.members:
            member = model.members[member_name]
            base = f"\tMember {member.name!r}: {member.label!r}"
            extras: List[str] = []
            if show_position:
                extras.append(f"@{member.position.line}:{member.position.column}")
            if extras:
                base += "  (" + ", ".join(extras) + ")"
            if member.documentation:
                doc_preview = member.documentation[0]
                if len(doc_preview) > 30:
                    doc_preview = doc_preview[:27] + "..."
                base += f"  // doc={doc_preview!r}"
            lines.append(base)
    
    # for declaration in model.declarations:
    #     base = f"{declaration.__class__.__name__} {declaration.name!r}: {declaration.label!r}"
    #     extras: List[str] = []
    #     if isinstance(declaration, CategoryDeclaration):
    #         extras.append(f"members={declaration.members}")
    #     elif isinstance(declaration, DimensionDeclaration):
    #         extras.append(f"members={declaration.members}")
    #     if show_position:
    #         extras.append(
    #             f"@{declaration.position.line}:{declaration.position.column}"
    #         )
    #     if extras:
    #         base += "  (" + ", ".join(extras) + ")"
    #     if declaration.documentation:
    #         doc_preview = declaration.documentation[0]
    #         if len(doc_preview) > 30:
    #             doc_preview = doc_preview[:27] + "..."
    #         base += f"  // doc={doc_preview!r}"
    #     lines.append(base)
    return "\n" + "\n".join(lines)


def _dataclass_to_tree(
    node: Any, show_pos: bool
) -> Tuple[str, List[Tuple[str, List[Tuple[str, list]]]]]:
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


def _is_position_like(field_name: str, value: Any) -> bool:
    """
    Heuristic to determine if a field is position-like
    (i.e., represents source code position information).
    """
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
