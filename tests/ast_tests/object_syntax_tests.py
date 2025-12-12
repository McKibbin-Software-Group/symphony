import json
import logging
from pathlib import Path
from symphony.abstract_syntax_tree import Model
from symphony.model_depictions import model_to_summary
from symphony.logging import convert_tree_to_jsonable
from tests.ast_tests.conftest import dimensions_model

def summarise_model(model: Model) -> str:
    assert model is not None, "Model should not be None"
    result: str = model_to_summary(model, show_position=False)
    logging.info(result)
    return result

def test_categories_abstract_syntax_tree(categories_model: Model, results_folder: Path):
    with open(results_folder / "categories_objects.txt", "w") as f:
        f.write(summarise_model(categories_model))


def test_dimensions_abstract_syntax_tree(dimensions_model: Model, results_folder: Path):
    with open(results_folder / "dimensions_objects.txt", "w") as f:
        f.write(summarise_model(dimensions_model))


def test_domains_abstract_syntax_tree(domains_model: Model, results_folder: Path):
    with open(results_folder / "domains_objects.txt", "w") as f:
        f.write(summarise_model(domains_model))


def test_variables_abstract_syntax_tree(variables_model: Model, results_folder: Path):
    with open(results_folder / "variables_objects.txt", "w") as f:
        f.write(summarise_model(variables_model))


def test_equations_abstract_syntax_tree(equations_model: Model, results_folder: Path):
    with open(results_folder / "equations_objects.txt", "w") as f:
        f.write(summarise_model(equations_model))