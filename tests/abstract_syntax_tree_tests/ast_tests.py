import json
import logging
from pathlib import Path

import pytest
from symphony import SymphonyDiagnosticsException
from symphony.abstract_syntax_tree import Modules
from symphony.abstract_syntax_tree_transformer import ASTLoaderResult
from symphony.model_depictions import model_to_summary


def summarise_model(ast_loader_result: ASTLoaderResult) -> str:
    assert ast_loader_result is not None, "Model should not be None"
    result: str = model_to_summary(ast_loader_result.modules, show_position=True)
    logging.info(result)
    return result


def test_categories_abstract_syntax_tree(
    categories_ast_loader_result: ASTLoaderResult, results_folder: Path
):
    with open(results_folder / "categories_objects.txt", "w") as f:
        f.write(summarise_model(categories_ast_loader_result))


def test_categories_with_syntax_errors_abstract_syntax_tree(
    categories_with_syntax_errors_ast_loader_result: ASTLoaderResult, results_folder: Path
):
    assert categories_with_syntax_errors_ast_loader_result.diagnostics.has_errors(), "Diagnostics should contain errors"

def test_dimensions_abstract_syntax_tree(
    dimensions_ast_loader_result: ASTLoaderResult, results_folder: Path
):
    with open(results_folder / "dimensions_objects.txt", "w") as f:
        f.write(summarise_model(dimensions_ast_loader_result))


def test_domains_abstract_syntax_tree(domains_ast_loader_result: ASTLoaderResult, results_folder: Path):
    with open(results_folder / "domains_objects.txt", "w") as f:
        f.write(summarise_model(domains_ast_loader_result))


def test_variables_abstract_syntax_tree(variables_ast_loader_result: ASTLoaderResult, results_folder: Path):
    with open(results_folder / "variables_objects.txt", "w") as f:
        f.write(summarise_model(variables_ast_loader_result))


def test_equations_abstract_syntax_tree(equations_ast_loader_result: ASTLoaderResult, results_folder: Path):
    with open(results_folder / "equations_objects.txt", "w") as f:
        f.write(summarise_model(equations_ast_loader_result))
