import json
import logging
from pathlib import Path
from lark import Tree
from symphony import SymphonyTree
from symphony.tokenising_transformer import TokenisingTransformer

def test_categories_json(categories_parse_tree: SymphonyTree, results_folder: Path):
    with open(results_folder / "categories_parse_tree.json", "w") as f:
        json.dump(TokenisingTransformer(file_path=categories_parse_tree.file_path).transform(categories_parse_tree.parse_tree), f, indent=2)

def test_dimensions_json(dimensions_parse_tree: SymphonyTree, results_folder: Path):
    with open(results_folder / "dimensions_parse_tree.json", "w") as f:
        json.dump(TokenisingTransformer(file_path=dimensions_parse_tree.file_path).transform(dimensions_parse_tree.parse_tree), f, indent=2)

def test_domains_json(domains_parse_tree: SymphonyTree, results_folder: Path):
    with open(results_folder / "domains_parse_tree.json", "w") as f:
        json.dump(TokenisingTransformer(file_path=domains_parse_tree.file_path).transform(domains_parse_tree.parse_tree), f, indent=2)

def test_variables_json(variables_parse_tree: SymphonyTree, results_folder: Path):
    with open(results_folder / "variables_parse_tree.json", "w") as f:
        json.dump(TokenisingTransformer(file_path=variables_parse_tree.file_path).transform(variables_parse_tree.parse_tree), f, indent=2)

def test_equations_json(equations_parse_tree: SymphonyTree, results_folder: Path):
    with open(results_folder / "equations_parse_tree.json", "w") as f:
        json.dump(TokenisingTransformer(file_path=equations_parse_tree.file_path).transform(equations_parse_tree.parse_tree), f, indent=2)
