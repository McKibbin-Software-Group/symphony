import logging
from pathlib import Path
from typing import List
from symphony.abstract_syntax_tree import CategoryDeclaration, DimensionDeclaration, Modules
from symphony.abstract_syntax_tree_transformer import ASTLoaderResult


def abstract_syntax_tree_summary(modules: Modules, show_position: bool = False) -> str:
    """
    Concise, one-line-per-declaration summary of a model declaration.

    ### Arguments

    - `modules`: The root abstract syntax tree node for the model declaration.
    - `show_position`: If `True`, include source position information for each declaration.

    ### Returns

    A multi-line string summarizing each declaration.
    """
    lines: List[str] = []
    for module in modules.modules:
        for declaration in module.declarations:
            label: str = f"{declaration.label.value}" if hasattr(declaration, "label") else ""
            name: str = f"{declaration.name}" if hasattr(declaration, "name") else ""
            base = f"{declaration.__class__.__name__} {name}: {label!r}"
            extras: List[str] = []
            if show_position:
                extras.append(
                    f"@{declaration.position.line}:{declaration.position.column}"
                )
            if extras:
                base += "  (" + ", ".join(extras) + ")"
            if declaration.documentation:
                doc_preview = declaration.documentation[0]
                if len(doc_preview) > 30:
                    doc_preview = doc_preview[:27] + "..."
                base += f"  // doc={doc_preview!r}"
            lines.append(base)
    return "\n" + "\n".join(lines)


def summarise_abstract_syntax_tree(ast_loader_result: ASTLoaderResult) -> str:
    assert ast_loader_result is not None, "Model should not be None"
    result: str = abstract_syntax_tree_summary(ast_loader_result.modules, show_position=True)
    logging.info(result)
    return result


def test_categories_abstract_syntax_tree(
    categories_ast_loader_result: ASTLoaderResult, results_folder: Path
):
    with open(results_folder / "categories_objects.txt", "w") as f:
        f.write(summarise_abstract_syntax_tree(categories_ast_loader_result))


def test_categories_with_syntax_errors_abstract_syntax_tree(
    categories_with_syntax_errors_ast_loader_result: ASTLoaderResult, results_folder: Path
):
    assert categories_with_syntax_errors_ast_loader_result.diagnostics.has_errors(), "Diagnostics should contain errors"

def test_dimensions_abstract_syntax_tree(
    dimensions_ast_loader_result: ASTLoaderResult, results_folder: Path
):
    with open(results_folder / "dimensions_objects.txt", "w") as f:
        f.write(summarise_abstract_syntax_tree(dimensions_ast_loader_result))


def test_domains_abstract_syntax_tree(domains_ast_loader_result: ASTLoaderResult, results_folder: Path):
    with open(results_folder / "domains_objects.txt", "w") as f:
        f.write(summarise_abstract_syntax_tree(domains_ast_loader_result))


def test_variables_abstract_syntax_tree(variables_ast_loader_result: ASTLoaderResult, results_folder: Path):
    with open(results_folder / "variables_objects.txt", "w") as f:
        f.write(summarise_abstract_syntax_tree(variables_ast_loader_result))


def test_equations_abstract_syntax_tree(equations_ast_loader_result: ASTLoaderResult, results_folder: Path):
    with open(results_folder / "equations_objects.txt", "w") as f:
        f.write(summarise_abstract_syntax_tree(equations_ast_loader_result))
