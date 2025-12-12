from lark import UnexpectedInput
import pytest
from pathlib import Path
from symphony import SymphonyTree, symphony_parser
from symphony.abstract_syntax_tree import Model
from symphony.abstract_syntax_tree_transformer import AbstractSyntaxTreeTransformer
from symphony.logging import print_parse_error
from symphony.abstract_syntax_tree_transformer import parse_declarations
from tests.conftest import symphony_file_contents


def model(model_file: Path) -> Model:
    try:
        symphony_tree: SymphonyTree = symphony_parser().parse(
            symphony_file_contents(model_file)
        )
        return AbstractSyntaxTreeTransformer().transform(symphony_tree.parse_tree)
    except UnexpectedInput as err:
        print_parse_error(err, symphony_file_contents(model_file), model_file)
        assert False, f"Failed to parse model from {model_file}\n"


@pytest.fixture
def categories_model(categories_file: Path) -> Model:
    return model(categories_file)


@pytest.fixture
def dimensions_model(dimensions_file: Path) -> Model:
    return model(dimensions_file)


@pytest.fixture
def domains_model(domains_file: Path) -> Model:
    return model(domains_file)


@pytest.fixture
def variables_model(variables_file: Path) -> Model:
    return model(variables_file)


@pytest.fixture
def equations_model(equations_file: Path) -> Model:
    return model(equations_file)
