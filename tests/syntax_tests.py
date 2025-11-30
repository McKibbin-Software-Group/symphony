import json
import logging
from pathlib import Path

from lark import Tree
from symphony.abstract_syntax_tree import Model, program_to_summary_text
from symphony.logging import convert_tree_to_jsonable
from symphony.json_transformer import JSONTransformer

def test_members_syntax(members_model: Model, results_folder: Path):
    assert members_model is not None
    logging.info(f"Parser results:\n{program_to_summary_text(members_model, show_position=False)}")
    with open(results_folder / "members_objects.json", "w") as f:
        json.dump(convert_tree_to_jsonable(members_model), f, indent=2)

def test_members_json(members_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "members_parse_tree.json", "w") as f:
        json.dump(JSONTransformer().transform(members_parse_tree), f, indent=2)

def test_categories_syntax(categories_model: Model, results_folder: Path):
    assert categories_model is not None
    logging.info(f"Parser results:\n{program_to_summary_text(categories_model, show_position=False)}")
    with open(results_folder / "categories.json", "w") as f:
        json.dump(convert_tree_to_jsonable(categories_model), f, indent=2)

def test_categories_json(categories_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "categories_parse_tree.json", "w") as f:
        json.dump(JSONTransformer().transform(categories_parse_tree), f, indent=2)

def test_dimensions_syntax(dimensions_model: Model, results_folder: Path):
    assert dimensions_model is not None
    logging.info(f"Parser results:\n{program_to_summary_text(dimensions_model, show_position=False)}")
    with open(results_folder / "dimensions.json", "w") as f:
        json.dump(convert_tree_to_jsonable(dimensions_model), f, indent=2)

def test_dimensions_json(dimensions_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "dimensions_parse_tree.json", "w") as f:
        json.dump(JSONTransformer().transform(dimensions_parse_tree), f, indent=2)

def test_domains_syntax(domains_model: Model, results_folder: Path):  
    assert domains_model is not None
    logging.info(f"Parser results:\n{program_to_summary_text(domains_model, show_position=False)}")
    with open(results_folder / "domains.json", "w") as f:
        json.dump(convert_tree_to_jsonable(domains_model), f, indent=2)

def test_domains_json(domains_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "domains_parse_tree.json", "w") as f:
        json.dump(JSONTransformer().transform(domains_parse_tree), f, indent=2)