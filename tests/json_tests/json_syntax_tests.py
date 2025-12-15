import json
from pathlib import Path
from symphony import SymphonyFile
from symphony.json_transformer import JSONTransformer


def test_categories_json(categories_symphony_file: SymphonyFile, results_folder: Path):
    with open(results_folder / "categories_parse_tree.json", "w") as f:
        json.dump(
            JSONTransformer(file_path=categories_symphony_file.file_path).transform(
                categories_symphony_file.tree
            ),
            f,
            indent=2,
        )


def test_dimensions_json(dimensions_symphony_file: SymphonyFile, results_folder: Path):
    with open(results_folder / "dimensions_parse_tree.json", "w") as f:
        json.dump(
            JSONTransformer(file_path=dimensions_symphony_file.file_path).transform(
                dimensions_symphony_file.tree
            ),
            f,
            indent=2,
        )


def test_domains_json(domains_symphony_file: SymphonyFile, results_folder: Path):
    with open(results_folder / "domains_parse_tree.json", "w") as f:
        json.dump(
            JSONTransformer(file_path=domains_symphony_file.file_path).transform(
                domains_symphony_file.tree
            ),
            f,
            indent=2,
        )


def test_variables_json(variables_symphony_file: SymphonyFile, results_folder: Path):
    with open(results_folder / "variables_parse_tree.json", "w") as f:
        json.dump(
            JSONTransformer(file_path=variables_symphony_file.file_path).transform(
                variables_symphony_file.tree
            ),
            f,
            indent=2,
        )


def test_equations_json(equations_symphony_file: SymphonyFile, results_folder: Path):
    with open(results_folder / "equations_parse_tree.json", "w") as f:
        json.dump(
            JSONTransformer(file_path=equations_symphony_file.file_path).transform(
                equations_symphony_file.tree
            ),
            f,
            indent=2,
        )
