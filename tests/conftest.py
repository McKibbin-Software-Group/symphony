import logging
from lark import Lark, Tree, UnexpectedInput
import pytest
from pathlib import Path
from importlib import resources
from symphony.abstract_syntax_tree import Model, abstract_syntax_tree_to_text, program_to_summary_text
from symphony.logging import print_parse_error
from symphony.processor import build_parser
from symphony.raw_abstract_syntax_tree_parser import parse_declarations

@pytest.fixture
def data_folder() -> Path:
    return Path(__file__).parent / "data"

@pytest.fixture
def root_folder() -> Path:
    return Path(__file__).parent.parent

@pytest.fixture
def results_folder(root_folder: Path) -> Path:
    result: Path = root_folder / "results"
    result.mkdir(exist_ok=True)
    return result

@pytest.fixture
def models_folder(data_folder: Path) -> Path:
    return data_folder / "models"

@pytest.fixture
def members_file(models_folder: Path) -> Path:
    return models_folder / "members.sym"

@pytest.fixture
def categories_file(models_folder: Path) -> Path:
    return models_folder / "categories.sym"

@pytest.fixture
def dimensions_file(models_folder: Path) -> Path:
    return models_folder / "dimensions.sym"

@pytest.fixture
def domains_file(models_folder: Path) -> Path:
    return models_folder / "domains.sym"

@pytest.fixture
def variables_file(models_folder: Path) -> Path:
    return models_folder / "variables.sym"

@pytest.fixture
def equations_file(models_folder: Path) -> Path:
    return models_folder / "equations.sym"

@pytest.fixture
def symphony_grammar_file(models_folder: Path) -> Path:

    return resources.files("symphony").joinpath("symphony.lark")

@pytest.fixture
def parser(symphony_grammar_file: Path) -> Lark:

    try:
        with resources.as_file(symphony_grammar_file) as grammar_path:
            return build_parser(grammar_path)
    except Exception as exception:
        assert False, f"Failed to build parser from bundled grammar {symphony_grammar_file}: {exception}\n"

def declaration(model_file:Path) -> str:
    try:
        return model_file.read_text(encoding="utf-8")
    except OSError as exception:
        assert False, f"Failed to read input file {model_file}: {exception}\n"

def model(parser: Lark, model_file: Path) -> Model:
    try:
        return parse_declarations(parser, declaration(model_file))
    except UnexpectedInput as err:
        print_parse_error(err, declaration(model_file), model_file)
        assert False, f"Failed to parse model from {model_file}\n"

def parse_tree(parser: Lark, model_file: Path):
    try:
        return parser.parse(declaration(model_file))
    except UnexpectedInput as err:
        assert False, f"Failed to parse model from {model_file}\n"

@pytest.fixture
def members_parse_tree(parser: Lark, members_file: Path) -> Tree:
    return parse_tree(parser, members_file)

@pytest.fixture
def categories_parse_tree(parser: Lark, categories_file: Path) -> Tree:
    return parse_tree(parser, categories_file)

@pytest.fixture
def dimensions_parse_tree(parser: Lark, dimensions_file: Path) -> Tree:
    return parse_tree(parser, dimensions_file)

@pytest.fixture
def domains_parse_tree(parser: Lark, domains_file: Path) -> Tree:
    return parse_tree(parser, domains_file)

@pytest.fixture
def variables_parse_tree(parser: Lark, variables_file: Path) -> Tree:
    return parse_tree(parser, variables_file)

@pytest.fixture
def equations_parse_tree(parser: Lark, equations_file: Path) -> Tree:
    return parse_tree(parser, equations_file)



@pytest.fixture
def members_model(parser: Lark, members_file: Path) -> Model:
    return model(parser, members_file)

@pytest.fixture
def categories_model(parser: Lark, categories_file: Path) -> Model:
    return model(parser, categories_file)

@pytest.fixture
def dimensions_model(parser: Lark, dimensions_file: Path) -> Model:
    return model(parser, dimensions_file)

@pytest.fixture
def domains_model(parser: Lark, domains_file: Path) -> Model:
    return model(parser, domains_file)

@pytest.fixture
def variables_model(parser: Lark, variables_file: Path) -> Model:
    return model(parser, variables_file)

@pytest.fixture
def equations_model(parser: Lark, equations_file: Path) -> Model:
    return model(parser, equations_file)