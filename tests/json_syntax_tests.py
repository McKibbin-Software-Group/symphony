import json
import logging
from pathlib import Path
from lark import Tree
from symphony.tokenising_transformer import TokenisingTransformer

def test_members_json(members_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "members_parse_tree.json", "w") as f:
        json.dump(TokenisingTransformer().transform(members_parse_tree), f, indent=2)

def test_categories_json(categories_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "categories_parse_tree.json", "w") as f:
        json.dump(TokenisingTransformer().transform(categories_parse_tree), f, indent=2)

def test_dimensions_json(dimensions_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "dimensions_parse_tree.json", "w") as f:
        json.dump(TokenisingTransformer().transform(dimensions_parse_tree), f, indent=2)

def test_domains_json(domains_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "domains_parse_tree.json", "w") as f:
        json.dump(TokenisingTransformer().transform(domains_parse_tree), f, indent=2)

def test_variables_json(variables_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "variables_parse_tree.json", "w") as f:
        json.dump(TokenisingTransformer().transform(variables_parse_tree), f, indent=2)

def test_equations_json(equations_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "equations_parse_tree.json", "w") as f:
        json.dump(TokenisingTransformer().transform(equations_parse_tree), f, indent=2)

def test_modules_json(modules_parse_tree: Tree, results_folder: Path):
    with open(results_folder / "modules_parse_tree.json", "w") as f:
        json.dump(TokenisingTransformer().transform(modules_parse_tree), f, indent=2)