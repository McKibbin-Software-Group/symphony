import json
import logging
from pathlib import Path

from lark import Tree
from symphony.abstract_syntax_tree import Model, program_to_summary_text
from symphony.logging import convert_tree_to_jsonable
from symphony.json_transformer import JSONTransformer

def test_members_json(members_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "members_parse_tree.json", "w") as f:
        json.dump(JSONTransformer().transform(members_parse_tree), f, indent=2)

def test_categories_json(categories_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "categories_parse_tree.json", "w") as f:
        json.dump(JSONTransformer().transform(categories_parse_tree), f, indent=2)

def test_dimensions_json(dimensions_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "dimensions_parse_tree.json", "w") as f:
        json.dump(JSONTransformer().transform(dimensions_parse_tree), f, indent=2)

def test_domains_json(domains_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "domains_parse_tree.json", "w") as f:
        json.dump(JSONTransformer().transform(domains_parse_tree), f, indent=2)