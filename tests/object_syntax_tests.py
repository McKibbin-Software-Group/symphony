import json
import logging
from pathlib import Path

from symphony.abstract_syntax_tree import Model

from symphony.model_depictions import (
    model_to_tree,
    model_to_summary,
)

from symphony.logging import convert_tree_to_jsonable

def test_members_syntax(members_model: Model, results_folder: Path):
    assert members_model is not None
    logging.info(f"Parser results:\n{model_to_summary(members_model, show_position=False)}")
    with open(results_folder / "members_objects.json", "w") as f:
        json.dump(convert_tree_to_jsonable(members_model), f, indent=2)

def test_categories_syntax(categories_model: Model, results_folder: Path):
    assert categories_model is not None
    logging.info(f"Parser results:\n{model_to_summary(categories_model, show_position=False)}")
    with open(results_folder / "categories_objects.json", "w") as f:
        json.dump(convert_tree_to_jsonable(categories_model), f, indent=2)

def test_dimensions_syntax(dimensions_model: Model, results_folder: Path):
    assert dimensions_model is not None
    logging.info(f"Parser results:\n{model_to_summary(dimensions_model, show_position=False)}")
    with open(results_folder / "dimensions_objects.json", "w") as f:
        json.dump(convert_tree_to_jsonable(dimensions_model), f, indent=2)

def test_domains_syntax(domains_model: Model, results_folder: Path):  
    assert domains_model is not None
    logging.info(f"Parser results:\n{model_to_summary(domains_model, show_position=False)}")
    with open(results_folder / "domains_objects.json", "w") as f:
        json.dump(convert_tree_to_jsonable(domains_model), f, indent=2)

def test_variables_syntax(variables_model: Model, results_folder: Path):
    assert variables_model is not None
    logging.info(f"Parser results:\n{model_to_summary(variables_model, show_position=False)}")
    with open(results_folder / "variables_objects.json", "w") as f:
        json.dump(convert_tree_to_jsonable(variables_model), f, indent=2)

def test_equations_syntax(equations_model: Model, results_folder: Path):
    assert equations_model is not None
    logging.info(f"Parser results:\n{model_to_summary(equations_model, show_position=False)}")
    with open(results_folder / "equations_objects.json", "w") as f:
        json.dump(convert_tree_to_jsonable(equations_model), f, indent=2)